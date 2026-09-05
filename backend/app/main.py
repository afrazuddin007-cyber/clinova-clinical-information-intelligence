import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.database import engine, Base, SessionLocal
from .core.security import get_password_hash
from .models.db_models import User
from .api import health, auth, patients, reports, verification, comparison, conflicts, doctor_intel, demo, audit

logger = logging.getLogger("clinova")

# Create database tables automatically
Base.metadata.create_all(bind=engine)

# Auto-migration check for SQLite schema evolution and indexes
with engine.connect() as conn:
    try:
        from sqlalchemy import text
        conn.execute(text("ALTER TABLE users ADD COLUMN organization_name VARCHAR(255) DEFAULT 'MVSR Medical Center'"))
    except Exception:
        pass
    try:
        from sqlalchemy import text
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_patients_created_by_user_id ON patients (created_by_user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id)"))
        conn.commit()
    except Exception:
        pass

def ensure_default_doctor():
    """Seeds a default demo clinician for zero-friction evaluation."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "doctor@clinova.health").first()
        if not existing:
            demo_doctor = User(
                email="doctor@clinova.health",
                hashed_password=get_password_hash("clinova2026"),
                full_name="Dr. Sarah Chen, MD",
                role="doctor"
            )
            db.add(demo_doctor)
            db.commit()
            logger.info("[Clinova] Default evaluation clinician initialized: doctor@clinova.health")
    finally:
        db.close()

ensure_default_doctor()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Clinova — AI-Powered Clinical Information Intelligence API. 'One patient. One record. Every insight traceable.'",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Global Exception Handler to prevent information leakage
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact system support."}
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for development & Cloud Run
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(health.router, prefix=api_v1_prefix)
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(patients.router, prefix=api_v1_prefix)
app.include_router(reports.router, prefix=api_v1_prefix)
app.include_router(verification.router, prefix=api_v1_prefix)
app.include_router(comparison.router, prefix=api_v1_prefix)
app.include_router(conflicts.router, prefix=api_v1_prefix)
app.include_router(doctor_intel.router, prefix=api_v1_prefix)
app.include_router(demo.router, prefix=api_v1_prefix)
app.include_router(audit.router, prefix=api_v1_prefix)

# Mount Static Frontend Bundle if built (for Cloud Run production)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists() and (static_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health"
    }

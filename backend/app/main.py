import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.database import engine, Base, SessionLocal
from .core.security import get_password_hash
from .models.db_models import User
from .api import health, auth, patients, reports, verification, comparison, conflicts, doctor_intel, demo, audit

# Create database tables automatically
Base.metadata.create_all(bind=engine)

# Auto-migration check for SQLite schema evolution
with engine.connect() as conn:
    try:
        from sqlalchemy import text
        conn.execute(text("ALTER TABLE users ADD COLUMN organization_name VARCHAR(255) DEFAULT 'MVSR Medical Center'"))
        conn.commit()
    except Exception:
        pass  # Column already exists or table freshly created

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
            print("[Clinova] Default evaluation clinician initialized: doctor@clinova.health")
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

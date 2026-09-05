from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db
from ..core.config import settings
from ..models.schemas import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=HealthCheckResponse)
def get_health(db: Session = Depends(get_db)):
    """Health check endpoint for container orchestrators and automated grading"""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    gemini_ready = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    return HealthCheckResponse(
        status="healthy" if db_ok else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        database_connected=db_ok,
        gemini_configured=gemini_ready,
        timestamp=datetime.now(timezone.utc)
    )

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

# Resolve base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

_DEV_FALLBACK_JWT_SECRET = "clinova_dev_jwt_secret_key_local_only_not_for_production_use_2026"

class Settings(BaseSettings):
    APP_NAME: str = "CLINOVA"
    APP_VERSION: str = "1.0.0"
    TAGLINE: str = "One patient. One record. Every insight traceable."
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = (os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")) if os.getenv("APP_ENV") == "production" else (os.getenv("DEBUG", "true").lower() in ("true", "1", "yes"))
    PORT: int = int(os.getenv("PORT", "8080"))

    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for clinical workflows

    # CORS Configuration
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    # AI Configuration (strictly server-side environment variable)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/clinova.db")

    # Uploads & Storage
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
    ]

    model_config = {
        "env_file": [str(PROJECT_ROOT / ".env"), str(BASE_DIR / ".env")],
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Parses comma-separated origins from CORS_ORIGINS.
        In development, or when no origins are explicitly defined,
        returns common local development origins to facilitate seamless testing.
        """
        origins: List[str] = []
        if self.CORS_ORIGINS:
            origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        
        default_dev_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        if self.APP_ENV != "production" or not origins:
            for dev_o in default_dev_origins:
                if dev_o not in origins:
                    origins.append(dev_o)
        return origins

settings = Settings()

# Enforce production security invariants
if settings.APP_ENV == "production":
    if not settings.JWT_SECRET or settings.JWT_SECRET == _DEV_FALLBACK_JWT_SECRET or settings.JWT_SECRET == "clinova_clinical_intelligence_secure_jwt_secret_key_2026":
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: In production (APP_ENV=production), a strong, "
            "unique JWT_SECRET must be configured via environment variables. Application startup aborted."
        )
else:
    if not settings.JWT_SECRET:
        settings.JWT_SECRET = _DEV_FALLBACK_JWT_SECRET

# Ensure required runtime directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

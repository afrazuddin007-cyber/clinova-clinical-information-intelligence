import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Resolve base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

class Settings(BaseSettings):
    APP_NAME: str = "CLINOVA"
    APP_VERSION: str = "1.0.0"
    TAGLINE: str = "One patient. One record. Every insight traceable."
    DEBUG: bool = True
    APP_ENV: str = "development"
    PORT: int = 8080

    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "clinova_clinical_intelligence_secure_jwt_secret_key_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for clinical workflows

    # AI Configuration (strictly server-side environment variable)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/clinova.db"

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

settings = Settings()

# Ensure required runtime directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

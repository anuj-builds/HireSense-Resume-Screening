"""
Central configuration — reads from environment variables with sensible defaults.
Extend this in later phases (e.g. add DATABASE_URL, SECRET_KEY, etc.).
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Project metadata ──────────────────────────────────────────────────────
    PROJECT_NAME: str = "Resume Screening API"
    VERSION: str = "0.1.0"

    # ── API routing ───────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",   # Vite default
        "http://localhost:3000",   # CRA / alternate
        "http://127.0.0.1:5173",
    ]

    # ── File upload ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── Database (Phase 2) ────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./resume_screening.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

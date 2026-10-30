"""
Resume Screening System — FastAPI Backend
Phase 1: Project scaffold + health-check endpoint
Phase 2: Resume upload, extraction, and SQLite persistence
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Startup / shutdown lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and uploads directory on first boot."""
    # Import here to avoid circular imports at module level
    from app.db.database import engine, Base
    import app.db.models  # noqa: F401 — ensure all models are registered

    Base.metadata.create_all(bind=engine)

    # Ensure the uploads directory exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    yield  # ← application runs here

    # (Add any shutdown cleanup here in future phases)


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI-Based Resume Screening and Candidate Shortlisting API",
        version=settings.VERSION,
        docs_url="/docs",       # Swagger UI
        redoc_url="/redoc",     # ReDoc UI
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Allow the React dev server (port 5173) and any localhost origin during dev.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()


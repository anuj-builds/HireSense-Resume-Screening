"""
Top-level API v1 router.
Add new feature routers here as each phase is built.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, resumes, jobs, screening

api_router = APIRouter()

# ── Phase 1 ───────────────────────────────────────────────────────────────────
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# ── Phase 2 ───────────────────────────────────────────────────────────────────
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])

# ── Phase 3 ───────────────────────────────────────────────────────────────────
api_router.include_router(jobs.router,      prefix="/jobs",      tags=["Jobs"])
api_router.include_router(screening.router, prefix="/screening", tags=["Screening"])

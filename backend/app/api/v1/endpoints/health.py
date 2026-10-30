"""
Health-check endpoint.

GET /api/v1/health/         → basic liveness probe
GET /api/v1/health/details  → detailed system info (Python version, uptime, etc.)
"""

import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# Record the time the process started so we can report uptime.
_START_TIME: float = time.monotonic()


# ─── Response schemas ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str


class HealthDetailsResponse(HealthResponse):
    version: str
    python_version: str
    uptime_seconds: float
    environment: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns **200 OK** when the API is running. Use this to verify the server is reachable.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Resume Screening API is up and running 🚀",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/details",
    response_model=HealthDetailsResponse,
    summary="Detailed health info",
    description="Returns runtime details including Python version and uptime.",
)
async def health_details() -> HealthDetailsResponse:
    uptime = time.monotonic() - _START_TIME
    return HealthDetailsResponse(
        status="ok",
        message="Resume Screening API is up and running 🚀",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.VERSION,
        python_version=sys.version,
        uptime_seconds=round(uptime, 2),
        environment="development",
    )

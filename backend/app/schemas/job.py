"""
Pydantic schemas for the Job resource.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Request bodies ───────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """Body for POST /jobs/"""

    title: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Senior Python Engineer"],
        description="Job title (2–255 characters).",
    )
    description: str = Field(
        ...,
        min_length=10,
        examples=["We are looking for a Python engineer with 5+ years experience..."],
        description="Full job description used for TF-IDF similarity matching.",
    )
    required_skills: List[str] = Field(
        default_factory=list,
        examples=[["python", "fastapi", "sql", "docker"]],
        description=(
            "List of required skill keywords (case-insensitive). "
            "Used for explicit skill-match scoring."
        ),
    )

    @field_validator("required_skills", mode="before")
    @classmethod
    def normalise_skills(cls, v):
        if not isinstance(v, list):
            raise ValueError("required_skills must be a list of strings.")
        cleaned = [s.strip().lower() for s in v if isinstance(s, str) and s.strip()]
        return cleaned


# ─── Response schemas ─────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """Returned after creating or fetching a job."""

    id: int
    title: str
    description: str
    required_skills: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Envelope for GET /jobs/ list endpoint."""

    total: int
    jobs: List[JobResponse]


# ─── ORM → Schema helpers ─────────────────────────────────────────────────────

def to_job_response(db_job) -> JobResponse:
    return JobResponse(
        id=db_job.id,
        title=db_job.title,
        description=db_job.description,
        required_skills=db_job.required_skills,   # uses the @property
        created_at=db_job.created_at,
    )

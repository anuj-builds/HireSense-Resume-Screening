"""
Job endpoints.

POST  /api/v1/jobs/        — Create a job posting
GET   /api/v1/jobs/        — List all jobs
GET   /api/v1/jobs/{id}    — Get a single job
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Job
from app.schemas.job import JobCreate, JobListResponse, JobResponse, to_job_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Create ───────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job posting",
    description=(
        "Create a new job posting with a title, description, and optional list "
        "of required skill keywords. The `required_skills` list is used for "
        "explicit skill-match scoring during candidate ranking."
    ),
)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
) -> JobResponse:
    job = Job(title=body.title, description=body.description)
    job.required_skills = body.required_skills      # uses the @property setter
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Created job id=%s title=%r", job.id, job.title)
    return to_job_response(job)


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=JobListResponse,
    summary="List all jobs",
    description="Returns all job postings ordered by most recently created first.",
)
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> JobListResponse:
    total = db.query(Job).count()
    jobs = db.query(Job).order_by(Job.id.desc()).offset(skip).limit(limit).all()
    return JobListResponse(total=total, jobs=[to_job_response(j) for j in jobs])


# ─── Get single ───────────────────────────────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
    description="Returns a single job posting by its ID.",
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> JobResponse:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id={job_id} not found.",
        )
    return to_job_response(job)

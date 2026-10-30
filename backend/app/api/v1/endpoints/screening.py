"""
Screening endpoints: candidate ranking and shortlisting.

GET   /api/v1/screening/{job_id}/rank
      Score and rank ALL stored resumes against the specified job.
      Returns candidates ordered highest-to-lowest overall score.

PATCH /api/v1/screening/{job_id}/shortlist/{resume_id}
      Set a recruiter shortlist status ('pending' | 'shortlisted' | 'rejected')
      and optional note for a specific resume+job pair.

GET   /api/v1/screening/{job_id}/shortlist
      List all shortlist decisions for a job.

Ethical note
------------
Scores use only textual content. No personal characteristics (name, age,
gender, nationality, etc.) influence the result. Scores are decision-support
signals; all hiring decisions remain with human recruiters.
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Job, Resume, Shortlist
from app.schemas.matching import (
    CandidateMatchResult,
    RankedCandidatesResponse,
    ShortlistResponse,
    ShortlistUpdate,
)
from app.services.matcher import rank_resumes

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_job_or_404(job_id: int, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id={job_id} not found.",
        )
    return job


def _get_shortlist_status(job_id: int, resume_id: int, db: Session) -> str:
    """Return the current shortlist status for this (job, resume) pair."""
    sl = (
        db.query(Shortlist)
        .filter(Shortlist.job_id == job_id, Shortlist.resume_id == resume_id)
        .first()
    )
    return sl.status if sl else "pending"


# ─── Rank candidates ──────────────────────────────────────────────────────────

@router.get(
    "/{job_id}/rank",
    response_model=RankedCandidatesResponse,
    summary="Rank candidates for a job",
    description=(
        "Score and rank **all stored resumes** against the specified job. "
        "Scoring uses: (1) required-skill keyword matching and (2) TF-IDF "
        "cosine similarity between the resume and the job description. "
        "Results are returned highest-score first. "
        "Resumes without extracted text receive score 0 but are still listed. "
        "\n\n> ⚠️ **Ethical notice**: scores are decision-support signals only. "
        "No personal characteristics are used in scoring."
    ),
)
def rank_candidates(
    job_id: int,
    db: Session = Depends(get_db),
) -> RankedCandidatesResponse:
    job = _get_job_or_404(job_id, db)

    # Fetch ALL resumes (processed and failed — failed score 0)
    resumes = db.query(Resume).all()

    if not resumes:
        return RankedCandidatesResponse(
            job_id=job_id,
            job_title=job.title,
            total_candidates=0,
            candidates=[],
        )

    ranked = rank_resumes(
        resumes=resumes,
        job_description=job.description,
        required_skills=job.required_skills,
    )

    # Attach current shortlist status for each candidate
    candidates: List[CandidateMatchResult] = []
    for r in ranked:
        sl_status = _get_shortlist_status(job_id, r.resume_id, db)
        candidates.append(
            CandidateMatchResult(
                resume_id=r.resume_id,
                original_filename=r.original_filename,
                overall_score=r.overall_score,
                skill_score=r.skill_score,
                tfidf_score=r.tfidf_score,
                matched_skills=r.matched_skills,
                missing_skills=r.missing_skills,
                shortlist_status=sl_status,
                resume_status=r.resume_status,
            )
        )

    return RankedCandidatesResponse(
        job_id=job_id,
        job_title=job.title,
        total_candidates=len(candidates),
        candidates=candidates,
    )


# ─── Update shortlist status ──────────────────────────────────────────────────

@router.patch(
    "/{job_id}/shortlist/{resume_id}",
    response_model=ShortlistResponse,
    summary="Update shortlist status",
    description=(
        "Set the recruiter's shortlist decision for a specific candidate + job. "
        "Valid statuses: `pending`, `shortlisted`, `rejected`. "
        "Creates the record on first call (upsert semantics)."
    ),
)
def update_shortlist(
    job_id: int,
    resume_id: int,
    body: ShortlistUpdate,
    db: Session = Depends(get_db),
) -> ShortlistResponse:
    # Validate both IDs exist
    _get_job_or_404(job_id, db)
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with id={resume_id} not found.",
        )

    # Upsert
    sl = (
        db.query(Shortlist)
        .filter(Shortlist.job_id == job_id, Shortlist.resume_id == resume_id)
        .first()
    )
    now = datetime.now(timezone.utc)

    if sl is None:
        sl = Shortlist(
            job_id=job_id,
            resume_id=resume_id,
            status=body.status,
            note=body.note,
        )
        db.add(sl)
    else:
        sl.status = body.status
        sl.note = body.note
        sl.updated_at = now

    db.commit()
    db.refresh(sl)

    logger.info(
        "Shortlist updated: job=%s resume=%s status=%r", job_id, resume_id, body.status
    )
    return ShortlistResponse(
        job_id=job_id,
        resume_id=resume_id,
        status=sl.status,
        note=sl.note,
        updated_at=sl.updated_at,
    )


# ─── List shortlist decisions ─────────────────────────────────────────────────

@router.get(
    "/{job_id}/shortlist",
    response_model=List[ShortlistResponse],
    summary="List shortlist decisions for a job",
    description="Returns all recruiter shortlist decisions recorded for the specified job.",
)
def list_shortlists(
    job_id: int,
    db: Session = Depends(get_db),
) -> List[ShortlistResponse]:
    _get_job_or_404(job_id, db)
    entries = (
        db.query(Shortlist)
        .filter(Shortlist.job_id == job_id)
        .order_by(Shortlist.resume_id)
        .all()
    )
    return [
        ShortlistResponse(
            job_id=sl.job_id,
            resume_id=sl.resume_id,
            status=sl.status,
            note=sl.note,
            updated_at=sl.updated_at,
        )
        for sl in entries
    ]

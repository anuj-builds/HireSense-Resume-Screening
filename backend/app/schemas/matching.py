"""
Pydantic schemas for candidate matching, ranking, and shortlisting.

Ethical note
------------
Match scores are computed purely from textual content (extracted resume text
vs. job description and required skills). No demographic attributes (name,
age, gender, nationality, photograph, etc.) are used or stored.
Scores are decision-SUPPORT signals only — they do not make hiring decisions.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ─── Matching / Ranking ───────────────────────────────────────────────────────

class CandidateMatchResult(BaseModel):
    """
    Match result for a single resume against a given job.

    Scoring breakdown
    -----------------
    skill_score      : fraction of required skills found in resume text (0–100)
    tfidf_score      : cosine similarity of resume vs. job description (0–100)
    overall_score    : weighted average (60 % skill + 40 % TF-IDF), rounded (0–100)

    No personal identifiers (name, age, gender, …) are included in scoring.
    """

    resume_id: int
    original_filename: str
    overall_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Weighted match score 0–100. Decision-support only.",
    )
    skill_score: float = Field(..., ge=0, le=100, description="Skill-coverage score 0–100.")
    tfidf_score: float = Field(..., ge=0, le=100, description="TF-IDF cosine similarity 0–100.")
    matched_skills: List[str] = Field(
        default_factory=list,
        description="Required skills found in the resume text.",
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Required skills NOT found in the resume text.",
    )
    shortlist_status: str = Field(
        default="pending",
        description="Recruiter decision: 'pending' | 'shortlisted' | 'rejected'.",
    )
    resume_status: str = Field(
        default="processed",
        description="Resume processing status. Unprocessed resumes score 0.",
    )


class RankedCandidatesResponse(BaseModel):
    """Envelope for GET /screening/{job_id}/rank"""

    job_id: int
    job_title: str
    total_candidates: int
    candidates: List[CandidateMatchResult]


# ─── Shortlisting ─────────────────────────────────────────────────────────────

class ShortlistUpdate(BaseModel):
    """Body for PATCH /screening/{job_id}/shortlist/{resume_id}"""

    status: Literal["pending", "shortlisted", "rejected"] = Field(
        ...,
        description="New shortlist status for this candidate.",
    )
    note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional recruiter note (max 500 chars).",
    )


class ShortlistResponse(BaseModel):
    """Returned after a shortlist status update."""

    job_id: int
    resume_id: int
    status: str
    note: Optional[str]
    updated_at: datetime

"""
ORM models for the Resume Screening system.

Phase 2: Resume model.
Phase 3: Job and Shortlist models added.
"""

import json
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ─── Resume ───────────────────────────────────────────────────────────────────

class Resume(Base):
    """Stores metadata and extracted text for every uploaded resume."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # SHA-256 for duplicate detection
    sha256_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Status: "pending" → "processed" | "failed"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} file={self.original_filename!r} status={self.status!r}>"


# ─── Job ──────────────────────────────────────────────────────────────────────

class Job(Base):
    """
    Stores a recruiter-created job posting.

    required_skills_json stores a JSON-encoded list of lowercase skill strings,
    e.g. '["python", "sql", "fastapi"]'.  Use the helper properties to
    read/write it as a plain Python list.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Stored as a JSON array of lowercase skill strings to stay SQLite-compatible
    required_skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def required_skills(self) -> list[str]:
        """Return required skills as a Python list."""
        try:
            return json.loads(self.required_skills_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @required_skills.setter
    def required_skills(self, skills: list[str]) -> None:
        self.required_skills_json = json.dumps(
            [s.strip().lower() for s in skills if s.strip()]
        )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r}>"


# ─── Shortlist ────────────────────────────────────────────────────────────────

class Shortlist(Base):
    """
    Records a recruiter's shortlisting decision for a (job, resume) pair.

    status values:
        "pending"     — not yet reviewed
        "shortlisted" — recruiter approved this candidate
        "rejected"    — recruiter dismissed this candidate
    """

    __tablename__ = "shortlists"
    __table_args__ = (
        UniqueConstraint("job_id", "resume_id", name="uq_shortlist_job_resume"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Recruiter decision
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Shortlist job={self.job_id} resume={self.resume_id} status={self.status!r}>"

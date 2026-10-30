"""
Pydantic response schemas for the Resume resource.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


_TEXT_PREVIEW_LENGTH = 300  # characters shown in list / upload responses


class ResumeResponse(BaseModel):
    """
    Returned for every resume after upload or look-up.
    The full extracted_text is included on single-item GET.
    The preview is a truncated version for list / upload endpoints.
    """

    id: int
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    mime_type: str
    status: str  # "pending" | "processed" | "failed"
    extracted_text_preview: Optional[str] = Field(
        default=None,
        description=f"First {_TEXT_PREVIEW_LENGTH} characters of extracted text.",
    )
    error_message: Optional[str] = None
    created_at: datetime
    is_duplicate: bool = Field(
        default=False,
        description="True when the uploaded file is byte-for-byte identical to an existing record.",
    )

    model_config = {"from_attributes": True}


class ResumeDetailResponse(ResumeResponse):
    """
    Extended response for GET /resumes/{id} — includes the full extracted text.
    """
    extracted_text: Optional[str] = None

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    """Envelope for GET /resumes/ list endpoint."""
    total: int
    resumes: list[ResumeResponse]


def to_resume_response(db_resume, *, is_duplicate: bool = False) -> ResumeResponse:
    """Map an ORM Resume instance → ResumeResponse."""
    preview: Optional[str] = None
    if db_resume.extracted_text:
        preview = db_resume.extracted_text[:_TEXT_PREVIEW_LENGTH]

    return ResumeResponse(
        id=db_resume.id,
        original_filename=db_resume.original_filename,
        stored_filename=db_resume.stored_filename,
        file_size_bytes=db_resume.file_size_bytes,
        mime_type=db_resume.mime_type,
        status=db_resume.status,
        extracted_text_preview=preview,
        error_message=db_resume.error_message,
        created_at=db_resume.created_at,
        is_duplicate=is_duplicate,
    )


def to_resume_detail(db_resume) -> ResumeDetailResponse:
    """Map an ORM Resume instance → ResumeDetailResponse (full text)."""
    preview: Optional[str] = None
    if db_resume.extracted_text:
        preview = db_resume.extracted_text[:_TEXT_PREVIEW_LENGTH]

    return ResumeDetailResponse(
        id=db_resume.id,
        original_filename=db_resume.original_filename,
        stored_filename=db_resume.stored_filename,
        file_size_bytes=db_resume.file_size_bytes,
        mime_type=db_resume.mime_type,
        status=db_resume.status,
        extracted_text_preview=preview,
        extracted_text=db_resume.extracted_text,
        error_message=db_resume.error_message,
        created_at=db_resume.created_at,
        is_duplicate=False,
    )

"""
Resume endpoints.

POST   /api/v1/resumes/upload      — Upload one or more PDF/DOCX resumes
GET    /api/v1/resumes/            — List all resumes (metadata + text preview)
GET    /api/v1/resumes/{resume_id} — Get a single resume (full text included)
"""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Resume
from app.schemas.resume import (
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeResponse,
    to_resume_detail,
    to_resume_response,
)
from app.services.extractor import ExtractionError, extract_text
from app.services.file_service import (
    compute_sha256,
    save_file,
    validate_extension,
    read_and_validate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=List[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload resumes",
    description=(
        "Upload one or more **PDF** or **DOCX** resume files (max "
        f"{settings.MAX_UPLOAD_SIZE_MB} MB each). "
        "Each file is validated, stored with a unique server-side name, "
        "text is extracted, and metadata is persisted to SQLite. "
        "Uploading a byte-identical duplicate returns the existing record "
        "with `is_duplicate: true` instead of an error."
    ),
)
async def upload_resumes(
    files: List[UploadFile] = File(
        ...,
        description="One or more PDF or DOCX resume files.",
    ),
    db: Session = Depends(get_db),
) -> List[ResumeResponse]:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No files provided.",
        )

    results: List[ResumeResponse] = []

    for upload in files:
        filename = upload.filename or "unknown"
        logger.info("Processing upload: %s", filename)

        # ── 1. Extension check ────────────────────────────────────────────────
        try:
            validate_extension(filename)
        except HTTPException as exc:
            # Surface per-file errors as failed records (don't abort the batch)
            results.append(
                ResumeResponse(
                    id=-1,
                    original_filename=filename,
                    stored_filename="",
                    file_size_bytes=0,
                    mime_type="unknown",
                    status="failed",
                    error_message=exc.detail,
                    created_at=_utcnow(),
                )
            )
            continue

        # ── 2. Read & validate size + magic bytes ─────────────────────────────
        try:
            data = await read_and_validate(upload)
        except HTTPException as exc:
            results.append(
                ResumeResponse(
                    id=-1,
                    original_filename=filename,
                    stored_filename="",
                    file_size_bytes=0,
                    mime_type="unknown",
                    status="failed",
                    error_message=exc.detail,
                    created_at=_utcnow(),
                )
            )
            continue

        # ── 3. Duplicate detection ────────────────────────────────────────────
        sha256 = compute_sha256(data)
        existing: Resume | None = (
            db.query(Resume).filter(Resume.sha256_hash == sha256).first()
        )
        if existing is not None:
            logger.info("Duplicate detected for %s (id=%s)", filename, existing.id)
            results.append(to_resume_response(existing, is_duplicate=True))
            continue

        # ── 4. Save to disk ───────────────────────────────────────────────────
        stored_filename, mime_type = save_file(data, filename)
        stored_path = Path(settings.UPLOAD_DIR) / stored_filename

        # ── 5. Persist initial DB record ──────────────────────────────────────
        resume = Resume(
            original_filename=filename,
            stored_filename=stored_filename,
            file_size_bytes=len(data),
            mime_type=mime_type,
            sha256_hash=sha256,
            status="pending",
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)

        # ── 6. Extract text ───────────────────────────────────────────────────
        try:
            text = extract_text(stored_path, mime_type)
            resume.extracted_text = text
            resume.status = "processed"
            logger.info("Extracted %d chars from %s", len(text), filename)
        except ExtractionError as exc:
            resume.status = "failed"
            resume.error_message = str(exc)[:500]
            logger.warning("Extraction failed for %s: %s", filename, exc)
        except Exception as exc:
            resume.status = "failed"
            resume.error_message = f"Unexpected extraction error: {exc}"
            logger.exception("Unexpected error extracting %s", filename)

        db.commit()
        db.refresh(resume)
        results.append(to_resume_response(resume))

    return results


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=ResumeListResponse,
    summary="List all resumes",
    description="Returns metadata and a text preview for every stored resume.",
)
def list_resumes(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ResumeListResponse:
    total = db.query(Resume).count()
    resumes = db.query(Resume).order_by(Resume.id.desc()).offset(skip).limit(limit).all()
    return ResumeListResponse(
        total=total,
        resumes=[to_resume_response(r) for r in resumes],
    )


# ─── Get single ───────────────────────────────────────────────────────────────

@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    summary="Get resume by ID",
    description="Returns full metadata and complete extracted text for a single resume.",
)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with id={resume_id} not found.",
        )
    return to_resume_detail(resume)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

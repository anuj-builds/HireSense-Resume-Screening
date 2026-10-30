"""
File service: validation, hashing, and disk storage.

Responsibilities:
  - Detect MIME type from magic bytes (not just extension)
  - Enforce allowed types and maximum file size
  - Compute SHA-256 hash for duplicate detection
  - Generate unique server-side filename (UUID-based)
  - Write file bytes to the uploads directory
"""

import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException, status

from app.core.config import settings

# ─── Constants ────────────────────────────────────────────────────────────────

# Allowed MIME types detected from magic bytes
ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

# Magic-byte signatures (first N bytes → MIME type)
_MAGIC: list[tuple[bytes, str]] = [
    (b"%PDF",  "application/pdf"),
    # DOCX is a ZIP archive; its PK magic is followed by a specific path entry
    (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
]

MAX_BYTES: int = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes


# ─── Public API ───────────────────────────────────────────────────────────────

def detect_mime(data: bytes) -> str | None:
    """
    Return the MIME type by inspecting the first bytes of *data*.
    Returns None if the signature is not recognised.

    Note: Both PDF and DOCX/ZIP share b"PK\x03\x04" for modern Office formats.
    We distinguish them by checking for the [Content_Types].xml marker that
    every valid DOCX ZIP must contain.  Plain ZIP archives without that marker
    are rejected.
    """
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                # Ensure it really is an Office Open XML file, not just any ZIP
                if b"[Content_Types].xml" in data[:4096] or b"word/" in data[:4096]:
                    return mime
                # It's a plain ZIP — reject
                return None
            return mime
    return None


def validate_extension(filename: str) -> None:
    """Raise 422 if the filename extension is not pdf or docx."""
    suffix = Path(filename).suffix.lower()
    allowed_exts = {".pdf", ".docx"}
    if suffix not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{suffix}'. Only PDF and DOCX are accepted.",
        )


async def read_and_validate(upload: UploadFile) -> bytes:
    """
    Read the full file into memory, enforcing MAX_BYTES.
    Raises HTTP 413 if the file exceeds the limit.
    Raises HTTP 422 if MIME magic bytes don't match a supported type.
    """
    # Read up to MAX_BYTES + 1 so we can detect oversized files
    chunk = await upload.read(MAX_BYTES + 1)

    if len(chunk) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File '{upload.filename}' exceeds the maximum allowed size of "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )

    if len(chunk) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File '{upload.filename}' is empty.",
        )

    detected = detect_mime(chunk)
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"File '{upload.filename}' has an unsupported format. "
                "Magic-byte check failed — only PDF and DOCX are accepted."
            ),
        )

    return chunk


def compute_sha256(data: bytes) -> str:
    """Return hex-encoded SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def build_upload_dir() -> Path:
    """Return the uploads directory Path, creating it if necessary."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_file(data: bytes, original_filename: str) -> tuple[str, str]:
    """
    Save *data* to the uploads directory with a UUID-based filename.

    Returns:
        (stored_filename, mime_type)
    """
    mime = detect_mime(data)  # already validated — will not be None
    ext = ALLOWED_MIME_TYPES[mime]
    stored_filename = f"{uuid.uuid4().hex}{ext}"

    dest = build_upload_dir() / stored_filename
    dest.write_bytes(data)

    return stored_filename, mime

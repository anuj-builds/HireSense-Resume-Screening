"""
Text extraction service for PDF and DOCX files.

Raises ExtractionError for:
  - Corrupt or unreadable files
  - Files that parse successfully but contain zero extractable text
    (e.g. scanned image-only PDFs without OCR layer)
"""

from pathlib import Path


class ExtractionError(Exception):
    """Raised when a file cannot be parsed or yields no text."""


# ─── PDF ──────────────────────────────────────────────────────────────────────

def extract_pdf(file_path: Path) -> str:
    """
    Extract plain text from a PDF using PyMuPDF (fitz).

    Args:
        file_path: Absolute path to the stored PDF file.

    Returns:
        Stripped text string.

    Raises:
        ExtractionError: If the file is corrupt, password-protected,
                         or contains no extractable text layer.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ExtractionError("PyMuPDF (fitz) is not installed.") from exc

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        raise ExtractionError(f"Cannot open PDF: {exc}") from exc

    if doc.is_encrypted:
        doc.close()
        raise ExtractionError("PDF is password-protected and cannot be read.")

    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text("text"))  # type: ignore[arg-type]
    doc.close()

    full_text = "\n".join(pages_text).strip()
    if not full_text:
        raise ExtractionError(
            "PDF parsed successfully but contains no extractable text "
            "(may be a scanned image without an OCR layer)."
        )

    return full_text


# ─── DOCX ─────────────────────────────────────────────────────────────────────

def extract_docx(file_path: Path) -> str:
    """
    Extract plain text from a DOCX file using python-docx.

    Args:
        file_path: Absolute path to the stored DOCX file.

    Returns:
        Stripped text string (paragraphs joined by newlines).

    Raises:
        ExtractionError: If the file is corrupt or contains no text.
    """
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
    except ImportError as exc:
        raise ExtractionError("python-docx is not installed.") from exc

    try:
        doc = Document(str(file_path))
    except PackageNotFoundError as exc:
        raise ExtractionError(f"Cannot open DOCX (corrupt or not a valid DOCX): {exc}") from exc
    except Exception as exc:
        raise ExtractionError(f"Cannot open DOCX: {exc}") from exc

    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs).strip()

    if not full_text:
        raise ExtractionError(
            "DOCX parsed successfully but contains no extractable text."
        )

    return full_text


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def extract_text(file_path: Path, mime_type: str) -> str:
    """
    Dispatch to the correct extractor based on MIME type.

    Args:
        file_path: Path to the stored file on disk.
        mime_type: MIME type string (e.g. 'application/pdf').

    Returns:
        Extracted text.

    Raises:
        ExtractionError: On any extraction failure.
        ValueError: If the MIME type is not supported.
    """
    if mime_type == "application/pdf":
        return extract_pdf(file_path)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_docx(file_path)
    else:
        raise ValueError(f"No extractor available for MIME type: {mime_type!r}")

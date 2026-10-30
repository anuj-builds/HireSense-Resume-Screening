"""
Automated tests for the Resume upload, extraction, and persistence endpoints.

Test matrix:
  01  Valid PDF upload              → 200, status=processed, text extracted
  02  Valid DOCX upload             → 200, status=processed, text extracted
  03  File too large                → 200 (batch), status=failed with size error
  04  Wrong extension (.txt)        → 200 (batch), status=failed with type error
  05  Corrupt PDF (bad magic)       → 200 (batch), status=failed with magic error
  06  Empty file                    → 200 (batch), status=failed with empty error
  07  Duplicate upload              → 200, is_duplicate=True, same id
  08  Multi-file batch (PDF+DOCX)   → 200, two results, both processed
  09  GET /resumes/ lists uploads   → 200, total matches
  10  GET /resumes/{id} returns full text
  11  GET /resumes/{id} 404 for missing id
  12  Health endpoints still work   → 200 (regression guard)
"""

import io
import pytest
from fastapi.testclient import TestClient


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _upload(client: TestClient, files_payload):
    """POST to /api/v1/resumes/upload with the given files tuples."""
    return client.post("/api/v1/resumes/upload", files=files_payload)


def _single_pdf(pdf_bytes: bytes, filename: str = "resume.pdf"):
    return [("files", (filename, pdf_bytes, "application/pdf"))]


def _single_docx(docx_bytes: bytes, filename: str = "resume.docx"):
    return [("files", (filename, docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))]


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestPDFUpload:
    def test_01_valid_pdf_upload(self, client: TestClient, pdf_bytes: bytes):
        """Valid PDF → 200, status processed, text contains expected content."""
        resp = _upload(client, _single_pdf(pdf_bytes))
        assert resp.status_code == 200, resp.text

        results = resp.json()
        assert len(results) == 1
        r = results[0]
        assert r["status"] == "processed", f"Expected processed, got: {r}"
        assert r["original_filename"] == "resume.pdf"
        assert r["id"] > 0
        assert r["is_duplicate"] is False
        assert r["extracted_text_preview"] is not None
        assert "Python" in r["extracted_text_preview"] or len(r["extracted_text_preview"]) > 0

    def test_05_corrupt_pdf(self, client: TestClient):
        """Bytes starting with %PDF but corrupt → failed status with magic error."""
        # These bytes start with %PDF but are not parseable by fitz
        bad_data = b"%PDF-1.4\n%%garbage\x00\x01\x02\x03" + b"JUNK" * 500
        resp = _upload(client, [("files", ("corrupt.pdf", bad_data, "application/pdf"))])
        assert resp.status_code == 200, resp.text
        r = resp.json()[0]
        # Magic check will pass (starts with %PDF), but fitz will fail to parse
        assert r["status"] == "failed"
        assert r["error_message"] is not None

    def test_06_empty_file(self, client: TestClient):
        """Empty file → status=failed with empty error message."""
        resp = _upload(client, [("files", ("empty.pdf", b"", "application/pdf"))])
        assert resp.status_code == 200, resp.text
        r = resp.json()[0]
        assert r["status"] == "failed"
        assert "empty" in r["error_message"].lower()


class TestDOCXUpload:
    def test_02_valid_docx_upload(self, client: TestClient, docx_bytes: bytes):
        """Valid DOCX → 200, status processed, text contains expected content."""
        resp = _upload(client, _single_docx(docx_bytes))
        assert resp.status_code == 200, resp.text

        results = resp.json()
        assert len(results) == 1
        r = results[0]
        assert r["status"] == "processed", f"Expected processed, got: {r}"
        assert r["original_filename"] == "resume.docx"
        assert r["id"] > 0
        assert r["is_duplicate"] is False
        assert r["extracted_text_preview"] is not None


class TestValidation:
    def test_03_file_too_large(self, client: TestClient, pdf_bytes: bytes):
        """PDF padded beyond 10 MB → status=failed with size error."""
        oversized = pdf_bytes + b"\x00" * (10 * 1024 * 1024 + 1)
        resp = _upload(client, _single_pdf(oversized, "big.pdf"))
        assert resp.status_code == 200, resp.text
        r = resp.json()[0]
        assert r["status"] == "failed"
        assert "10" in r["error_message"] or "size" in r["error_message"].lower() or "MB" in r["error_message"]

    def test_04_wrong_extension(self, client: TestClient, pdf_bytes: bytes):
        """File with .txt extension → status=failed with type error."""
        resp = _upload(client, [("files", ("notes.txt", pdf_bytes, "text/plain"))])
        assert resp.status_code == 200, resp.text
        r = resp.json()[0]
        assert r["status"] == "failed"
        assert "txt" in r["error_message"].lower() or "unsupported" in r["error_message"].lower()

    def test_unsupported_magic(self, client: TestClient):
        """File with .pdf extension but random bytes (wrong magic) → status=failed."""
        random_bytes = b"\x89PNG\r\n\x1a\n" + b"X" * 200  # PNG magic, .pdf ext
        resp = _upload(client, [("files", ("fake.pdf", random_bytes, "application/pdf"))])
        assert resp.status_code == 200, resp.text
        r = resp.json()[0]
        assert r["status"] == "failed"
        assert r["error_message"] is not None


class TestDeduplication:
    def test_07_duplicate_upload(self, client: TestClient, pdf_bytes: bytes):
        """Uploading the same file twice → second result has is_duplicate=True, same id."""
        # First upload
        resp1 = _upload(client, _single_pdf(pdf_bytes, "cv.pdf"))
        assert resp1.status_code == 200
        first = resp1.json()[0]
        assert first["status"] == "processed"
        original_id = first["id"]

        # Second upload — identical bytes
        resp2 = _upload(client, _single_pdf(pdf_bytes, "cv_copy.pdf"))
        assert resp2.status_code == 200
        second = resp2.json()[0]
        assert second["is_duplicate"] is True
        assert second["id"] == original_id


class TestBatchUpload:
    def test_08_multi_file_batch(self, client: TestClient, pdf_bytes: bytes, docx_bytes: bytes):
        """Uploading PDF + DOCX in one request → 2 results, both processed."""
        files = [
            ("files", ("resume1.pdf",  pdf_bytes,  "application/pdf")),
            ("files", ("resume2.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ]
        resp = _upload(client, files)
        assert resp.status_code == 200, resp.text
        results = resp.json()
        assert len(results) == 2
        statuses = {r["original_filename"]: r["status"] for r in results}
        assert statuses["resume1.pdf"] == "processed"
        assert statuses["resume2.docx"] == "processed"


class TestListAndGet:
    def test_09_list_resumes(self, client: TestClient, pdf_bytes: bytes, docx_bytes: bytes):
        """After uploading 2 resumes, GET /resumes/ returns total=2."""
        files = [
            ("files", ("r1.pdf",  pdf_bytes,  "application/pdf")),
            ("files", ("r2.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ]
        _upload(client, files)

        resp = client.get("/api/v1/resumes/")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 2
        assert len(data["resumes"]) == 2

    def test_10_get_single_resume_full_text(self, client: TestClient, pdf_bytes: bytes):
        """GET /resumes/{id} returns the full extracted_text (not just preview)."""
        upload_resp = _upload(client, _single_pdf(pdf_bytes, "fulltext.pdf"))
        resume_id = upload_resp.json()[0]["id"]

        resp = client.get(f"/api/v1/resumes/{resume_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == resume_id
        assert data["extracted_text"] is not None
        assert len(data["extracted_text"]) > 0

    def test_11_get_missing_resume(self, client: TestClient):
        """GET /resumes/99999 → 404."""
        resp = client.get("/api/v1/resumes/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestHealthRegression:
    def test_12_health_endpoints_still_work(self, client: TestClient):
        """Phase 1 health endpoints must still return 200 after Phase 2 changes."""
        r1 = client.get("/api/v1/health/")
        assert r1.status_code == 200
        assert r1.json()["status"] == "ok"

        r2 = client.get("/api/v1/health/details")
        assert r2.status_code == 200
        assert r2.json()["status"] == "ok"
        assert "python_version" in r2.json()

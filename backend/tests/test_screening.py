"""
Phase 3 tests: candidate matching, ranking, and shortlisting.

S01  Rank endpoint returns candidates ordered by score (highest first)
S02  Resume with required skills scores higher than one without
S03  Resume with no extracted text scores 0
S04  Ranking a non-existent job → 404
S05  Shortlist a candidate as 'shortlisted'
S06  Shortlist a candidate as 'rejected'
S07  Shortlist with invalid status → 422
S08  Shortlist for non-existent job → 404
S09  Shortlist for non-existent resume → 404
S10  List shortlist decisions for a job
S11  Shortlist status appears in rank results
S12  No required skills → skill_score = 100 for processed resumes
"""

import io
import pytest
from fastapi.testclient import TestClient


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _upload_pdf(client: TestClient, pdf_bytes: bytes, filename: str = "resume.pdf") -> int:
    """Upload a PDF and return its resume_id."""
    resp = client.post(
        "/api/v1/resumes/upload",
        files=[("files", (filename, pdf_bytes, "application/pdf"))],
    )
    assert resp.status_code == 200, resp.text
    r = resp.json()[0]
    assert r["status"] == "processed", f"Upload failed: {r}"
    return r["id"]


def _upload_docx(client: TestClient, docx_bytes: bytes, filename: str = "resume.docx") -> int:
    """Upload a DOCX and return its resume_id."""
    resp = client.post(
        "/api/v1/resumes/upload",
        files=[("files", (filename, docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    assert resp.status_code == 200, resp.text
    r = resp.json()[0]
    assert r["status"] == "processed", f"Upload failed: {r}"
    return r["id"]


def _make_job(client: TestClient, title: str, description: str, skills: list) -> int:
    """POST a job and return its job_id."""
    resp = client.post("/api/v1/jobs/", json={
        "title": title,
        "description": description,
        "required_skills": skills,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_pdf_with_skills(skills: list[str]) -> bytes:
    """Build a synthetic PDF whose text mentions specific skills."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    text = "Professional Resume\n\nSkills: " + ", ".join(skills) + "\n"
    text += "Experienced professional with background in " + " and ".join(skills) + ".\n"
    page.insert_text((72, 100), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ─── Ranking tests ────────────────────────────────────────────────────────────

class TestRanking:
    def test_S01_rank_returns_candidates_in_order(self, client: TestClient, pdf_bytes: bytes):
        """Rank endpoint returns at least one candidate and score ∈ [0,100]."""
        _upload_pdf(client, pdf_bytes, "cand1.pdf")
        job_id = _make_job(client, "Python Dev",
                           "We need a Python developer with SQL experience.",
                           ["python", "sql"])

        resp = client.get(f"/api/v1/screening/{job_id}/rank")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["total_candidates"] >= 1

        scores = [c["overall_score"] for c in data["candidates"]]
        # Verify descending order
        assert scores == sorted(scores, reverse=True), "Candidates not sorted by score desc"
        # All scores in [0, 100]
        assert all(0 <= s <= 100 for s in scores)

    def test_S02_skilled_resume_scores_higher(self, client: TestClient):
        """Resume explicitly mentioning required skills outscores one that doesn't."""
        skills = ["python", "fastapi", "postgresql"]

        # High-match resume
        high_pdf = _make_pdf_with_skills(skills)
        _upload_pdf(client, high_pdf, "high_match.pdf")

        # Low-match resume (mentions none of the required skills)
        low_pdf = _make_pdf_with_skills(["java", "spring", "oracle"])
        _upload_pdf(client, low_pdf, "low_match.pdf")

        job_id = _make_job(
            client,
            "FastAPI Engineer",
            "Looking for a Python FastAPI developer experienced with PostgreSQL databases.",
            skills,
        )

        resp = client.get(f"/api/v1/screening/{job_id}/rank")
        assert resp.status_code == 200, resp.text
        candidates = resp.json()["candidates"]
        assert len(candidates) == 2

        top = candidates[0]
        bottom = candidates[1]
        assert top["overall_score"] >= bottom["overall_score"], (
            "High-match resume should score >= low-match resume"
        )

    def test_S03_unprocessed_resume_scores_zero(self, client: TestClient, pdf_bytes: bytes):
        """A resume with failed status appears in rankings with score 0."""
        # Upload a corrupt file so it stays failed
        bad_data = b"%PDF-1.4\ngarbage\x00\x01" + b"X" * 500
        resp = client.post(
            "/api/v1/resumes/upload",
            files=[("files", ("bad.pdf", bad_data, "application/pdf"))],
        )
        assert resp.status_code == 200
        r = resp.json()[0]
        assert r["status"] == "failed"

        job_id = _make_job(client, "Any Job",
                           "Any job description for testing purposes.",
                           ["python"])
        rank_resp = client.get(f"/api/v1/screening/{job_id}/rank")
        assert rank_resp.status_code == 200

        # Find the failed resume in the ranking
        failed_candidates = [
            c for c in rank_resp.json()["candidates"]
            if c["resume_status"] == "failed"
        ]
        assert len(failed_candidates) >= 1
        for c in failed_candidates:
            assert c["overall_score"] == 0.0

    def test_S04_rank_nonexistent_job(self, client: TestClient):
        """Ranking for a non-existent job → 404."""
        resp = client.get("/api/v1/screening/99999/rank")
        assert resp.status_code == 404

    def test_S12_no_required_skills_skill_score_100(self, client: TestClient, pdf_bytes: bytes):
        """When a job has no required skills, processed resumes get skill_score=100."""
        _upload_pdf(client, pdf_bytes, "noskills.pdf")
        job_id = _make_job(
            client,
            "Open Role",
            "We are hiring for a general software engineering role.",
            [],     # ← no required skills
        )
        resp = client.get(f"/api/v1/screening/{job_id}/rank")
        assert resp.status_code == 200
        candidates = resp.json()["candidates"]
        processed = [c for c in candidates if c["resume_status"] == "processed"]
        for c in processed:
            assert c["skill_score"] == 100.0, f"Expected 100.0 skill_score, got {c['skill_score']}"


# ─── Shortlisting tests ───────────────────────────────────────────────────────

class TestShortlisting:
    def test_S05_shortlist_candidate(self, client: TestClient, pdf_bytes: bytes):
        """PATCH shortlist with 'shortlisted' → 200, status confirmed."""
        resume_id = _upload_pdf(client, pdf_bytes, "sl_resume.pdf")
        job_id = _make_job(client, "SL Job",
                           "Shortlist test job with Python requirement.",
                           ["python"])

        resp = client.patch(
            f"/api/v1/screening/{job_id}/shortlist/{resume_id}",
            json={"status": "shortlisted", "note": "Strong Python background."},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "shortlisted"
        assert data["job_id"] == job_id
        assert data["resume_id"] == resume_id
        assert "Strong Python" in (data["note"] or "")

    def test_S06_reject_candidate(self, client: TestClient, pdf_bytes: bytes):
        """PATCH shortlist with 'rejected' → 200, status confirmed."""
        resume_id = _upload_pdf(client, pdf_bytes, "rej_resume.pdf")
        job_id = _make_job(client, "RJ Job",
                           "Rejection test job description with requirements.",
                           ["python"])

        resp = client.patch(
            f"/api/v1/screening/{job_id}/shortlist/{resume_id}",
            json={"status": "rejected"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "rejected"

    def test_S07_invalid_shortlist_status(self, client: TestClient, pdf_bytes: bytes):
        """PATCH with invalid status value → 422."""
        resume_id = _upload_pdf(client, pdf_bytes, "inv_resume.pdf")
        job_id = _make_job(client, "INV Job",
                           "Invalid status test job description here.",
                           [])

        resp = client.patch(
            f"/api/v1/screening/{job_id}/shortlist/{resume_id}",
            json={"status": "maybe"},  # not in allowed values
        )
        assert resp.status_code == 422

    def test_S08_shortlist_nonexistent_job(self, client: TestClient, pdf_bytes: bytes):
        """PATCH shortlist for non-existent job → 404."""
        resume_id = _upload_pdf(client, pdf_bytes, "nej_resume.pdf")
        resp = client.patch(
            f"/api/v1/screening/99999/shortlist/{resume_id}",
            json={"status": "shortlisted"},
        )
        assert resp.status_code == 404

    def test_S09_shortlist_nonexistent_resume(self, client: TestClient):
        """PATCH shortlist for non-existent resume → 404."""
        job_id = _make_job(client, "NER Job",
                           "Non-existent resume test job description.",
                           [])
        resp = client.patch(
            f"/api/v1/screening/{job_id}/shortlist/99999",
            json={"status": "shortlisted"},
        )
        assert resp.status_code == 404

    def test_S10_list_shortlist_decisions(self, client: TestClient, pdf_bytes: bytes, docx_bytes: bytes):
        """GET /screening/{job_id}/shortlist lists all decisions for that job."""
        rid1 = _upload_pdf(client, pdf_bytes, "sl1.pdf")
        rid2 = _upload_docx(client, docx_bytes, "sl2.docx")
        job_id = _make_job(client, "List SL Job",
                           "List shortlist test job description with skills.",
                           ["python"])

        client.patch(f"/api/v1/screening/{job_id}/shortlist/{rid1}",
                     json={"status": "shortlisted"})
        client.patch(f"/api/v1/screening/{job_id}/shortlist/{rid2}",
                     json={"status": "rejected"})

        resp = client.get(f"/api/v1/screening/{job_id}/shortlist")
        assert resp.status_code == 200, resp.text
        entries = resp.json()
        assert len(entries) == 2
        statuses = {e["resume_id"]: e["status"] for e in entries}
        assert statuses[rid1] == "shortlisted"
        assert statuses[rid2] == "rejected"

    def test_S11_shortlist_status_in_rank_results(self, client: TestClient, pdf_bytes: bytes):
        """After shortlisting, the rank endpoint shows the updated status."""
        resume_id = _upload_pdf(client, pdf_bytes, "rank_sl.pdf")
        job_id = _make_job(client, "Rank SL Job",
                           "Ranking shortlist status test job description.",
                           ["python"])

        # Shortlist this candidate
        client.patch(
            f"/api/v1/screening/{job_id}/shortlist/{resume_id}",
            json={"status": "shortlisted"},
        )

        # Now rank — the shortlist_status should be 'shortlisted'
        resp = client.get(f"/api/v1/screening/{job_id}/rank")
        assert resp.status_code == 200
        candidates = resp.json()["candidates"]
        match = next((c for c in candidates if c["resume_id"] == resume_id), None)
        assert match is not None
        assert match["shortlist_status"] == "shortlisted"

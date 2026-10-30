"""
Phase 3 tests: Job CRUD endpoints.

J01  POST /jobs/ creates a job and returns it
J02  GET  /jobs/ lists all jobs
J03  GET  /jobs/{id} returns a specific job
J04  GET  /jobs/999 returns 404
J05  Skills are normalised to lowercase on create
J06  Description too short → 422
J07  Title too short → 422
"""

import pytest
from fastapi.testclient import TestClient


class TestJobCRUD:
    def test_J01_create_job(self, client: TestClient):
        """POST /jobs/ → 201, job returned with correct fields."""
        payload = {
            "title": "Senior Python Engineer",
            "description": "We need a Python engineer with experience in FastAPI and SQL databases.",
            "required_skills": ["Python", "FastAPI", "SQL"],
        }
        resp = client.post("/api/v1/jobs/", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["id"] > 0
        assert data["title"] == "Senior Python Engineer"
        # Skills are normalised to lowercase
        assert "python" in data["required_skills"]
        assert "fastapi" in data["required_skills"]
        assert "sql" in data["required_skills"]

    def test_J02_list_jobs(self, client: TestClient):
        """GET /jobs/ returns all created jobs."""
        client.post("/api/v1/jobs/", json={
            "title": "Data Analyst",
            "description": "Looking for a data analyst with Python and SQL skills.",
            "required_skills": ["python", "sql"],
        })
        client.post("/api/v1/jobs/", json={
            "title": "ML Engineer",
            "description": "Machine learning engineer needed with TensorFlow and Python skills.",
            "required_skills": ["python", "tensorflow"],
        })

        resp = client.get("/api/v1/jobs/")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 2
        assert len(data["jobs"]) == 2

    def test_J03_get_job_by_id(self, client: TestClient):
        """GET /jobs/{id} returns the correct job."""
        created = client.post("/api/v1/jobs/", json={
            "title": "Backend Dev",
            "description": "Backend developer role requiring Python and Docker experience.",
            "required_skills": ["python", "docker"],
        }).json()
        job_id = created["id"]

        resp = client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == job_id
        assert data["title"] == "Backend Dev"

    def test_J04_get_missing_job(self, client: TestClient):
        """GET /jobs/99999 → 404."""
        resp = client.get("/api/v1/jobs/99999")
        assert resp.status_code == 404

    def test_J05_skills_normalised_to_lowercase(self, client: TestClient):
        """Skills with mixed case are stored lowercase."""
        resp = client.post("/api/v1/jobs/", json={
            "title": "Full-stack Dev",
            "description": "Full stack developer with React and Python knowledge needed.",
            "required_skills": ["REACT", "Python", "TypeScript"],
        })
        assert resp.status_code == 201
        skills = resp.json()["required_skills"]
        assert all(s == s.lower() for s in skills)

    def test_J06_description_too_short(self, client: TestClient):
        """Description < 10 chars → 422."""
        resp = client.post("/api/v1/jobs/", json={
            "title": "Dev Job",
            "description": "Short",
            "required_skills": [],
        })
        assert resp.status_code == 422

    def test_J07_title_too_short(self, client: TestClient):
        """Title < 2 chars → 422."""
        resp = client.post("/api/v1/jobs/", json={
            "title": "X",
            "description": "Some valid description here",
            "required_skills": [],
        })
        assert resp.status_code == 422

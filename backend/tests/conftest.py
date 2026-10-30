"""
pytest fixtures for the Resume Screening API test suite.

Database isolation strategy
---------------------------
SQLite's :memory: databases are per-connection by default. Using StaticPool
ensures that every SQLAlchemy operation (create_all, sessions, etc.) uses
the SAME underlying connection and thus the SAME in-memory schema.

This fixture:
  1. Creates a StaticPool in-memory engine and calls create_all() on it.
  2. Overrides the FastAPI get_db dependency to yield a session from that engine.
  3. Restores everything after each test.
"""

import io
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

import app.db.database as db_module       # module we monkey-patch
from app.db.database import get_db
import app.db.models                       # noqa: F401 — register ALL models on Base
from app.db.database import Base
from main import app


# ─── In-memory test database ──────────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Fresh in-memory SQLite DB per test using StaticPool so that all
    SQLAlchemy operations (schema creation AND queries) share the same
    connection and see the same tables.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,            # ← all ops share one connection
    )

    # Ensure all models (Resume, Job, Shortlist…) are registered on Base
    import app.db.models  # noqa: F401

    # Create schema on the shared in-memory connection
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = TestingSessionLocal()

    # Patch module-level names so any code that reads them gets the test engine
    original_engine       = db_module.engine
    original_session_cls  = db_module.SessionLocal

    db_module.engine       = test_engine
    db_module.SessionLocal = TestingSessionLocal

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        db_module.engine       = original_engine
        db_module.SessionLocal = original_session_cls


# ─── TestClient with DB override ─────────────────────────────────────────────

@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """TestClient whose get_db dependency yields the shared in-memory session."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # cleanup handled by test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


# ─── Synthetic document fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def pdf_bytes() -> bytes:
    """Structurally valid PDF with real text content (PyMuPDF)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 100),
        (
            "John Doe\n"
            "Software Engineer\n"
            "Skills: Python, FastAPI, Machine Learning, SQL\n"
            "Experience: 5 years at Acme Corp\n"
            "Education: B.Sc. Computer Science, State University\n"
        ),
        fontsize=12,
    )
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


@pytest.fixture(scope="session")
def docx_bytes() -> bytes:
    """Structurally valid DOCX with real text content (python-docx)."""
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_heading("Jane Smith", level=1)
    doc.add_paragraph("Data Scientist | jane@example.com")
    doc.add_paragraph("Skills: Python, TensorFlow, Pandas, SQL, Spark")
    doc.add_paragraph("Experience: 3 years at DataCo, 2 years at ML Labs")
    doc.add_paragraph("Education: M.Sc. Data Science, Tech University")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

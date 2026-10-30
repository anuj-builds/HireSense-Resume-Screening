"""
Database engine, session factory, and FastAPI dependency.

Usage:
    from app.db.database import get_db, Base, engine

    # In endpoint:
    db: Session = Depends(get_db)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# ─── Engine ───────────────────────────────────────────────────────────────────
# connect_args is required for SQLite to allow multi-threaded use.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set True to log all SQL statements during debugging
)

# ─── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── FastAPI dependency ───────────────────────────────────────────────────────
def get_db():
    """
    Yield a database session and guarantee it is closed after the request,
    even if an exception is raised.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

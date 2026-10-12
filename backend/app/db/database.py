"""
GhostWatt — app/db/database.py
SQLAlchemy engine with SQLite WAL mode, session factory, and session helpers.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

connect_args = {}
if settings.db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.db_url, connect_args=connect_args)


# Enable WAL mode and foreign keys for SQLite (concurrency & data integrity)
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def create_all_tables():
    """Create all tables. Called on startup and by seed script."""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Drop all tables. Used by seed script for idempotent re-seeding."""
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager session helper for standalone scripts, background tasks,
    or CLI tools. Commits on exit, rollbacks on exception.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Alias for convenience
session_scope = get_session

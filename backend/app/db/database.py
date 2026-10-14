"""
GhostWatt — app/db/database.py
SQLAlchemy engine with SQLite WAL mode, session factory, and session helpers.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

DB_URL = settings.resolved_db_url
connect_args = {}
if DB_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30  # wait for the write lock instead of failing with "database is locked"

engine = create_engine(DB_URL, connect_args=connect_args)


# Enable WAL mode and foreign keys for SQLite (concurrency & data integrity)
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _table_columns(conn, table: str) -> set:
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}


def create_all_tables():
    """
    Create all tables and apply the small, idempotent SQLite migrations the app relies on.
    Called on startup and by the seed script. Safe to run on every start.
    """
    Base.metadata.create_all(bind=engine)
    if not DB_URL.startswith("sqlite"):
        return

    with engine.begin() as conn:
        # --- additive column migrations ------------------------------------------------------
        wl_cols = _table_columns(conn, "water_locations")
        if "baseline_night_lph" not in wl_cols:
            conn.exec_driver_sql("ALTER TABLE water_locations ADD COLUMN baseline_night_lph REAL DEFAULT 50.0")
        if "meter_type" not in wl_cols:
            conn.exec_driver_sql("ALTER TABLE water_locations ADD COLUMN meter_type TEXT DEFAULT 'pulse'")

        user_cols = _table_columns(conn, "users")
        if "phone" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
        if "full_name" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN full_name VARCHAR(120)")
        conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_unique ON users(phone) WHERE phone IS NOT NULL")

        # Demo accounts get a phone number + display name (only where still empty).
        for email, phone, name in (
            ("admin@ghostwatt.demo", "9876500000", "Demo Admin"),
            ("student@ghostwatt.demo", "9876543210", "Demo Student"),
            ("student2@ghostwatt.demo", "9876543211", "Demo Student 2"),
        ):
            conn.exec_driver_sql(
                "UPDATE users SET phone = COALESCE(phone, :p), full_name = COALESCE(full_name, :n) WHERE email = :e",
                {"p": phone, "n": name, "e": email},
            )

        # --- data-integrity migration: one reading per (room, timestamp) ---------------------
        # Re-running a simulation over an already-populated period used to insert duplicate rows,
        # which double-counted kWh / litres in every total. Keep the newest row, then enforce it.
        conn.exec_driver_sql(
            "DELETE FROM meter_readings WHERE id NOT IN (SELECT MAX(id) FROM meter_readings GROUP BY room_id, timestamp)"
        )
        conn.exec_driver_sql(
            "DELETE FROM water_readings WHERE id NOT IN (SELECT MAX(id) FROM water_readings GROUP BY location_id, timestamp)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_meter_room_ts ON meter_readings(room_id, timestamp)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_water_loc_ts ON water_readings(location_id, timestamp)"
        )


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

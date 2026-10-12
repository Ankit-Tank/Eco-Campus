"""
Tests for GhostWatt DB Models, Constraints, and Seed Data Generator.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.db.database import get_session, Base, engine
from app.db import models
from app.core.security import verify_password
from app.services.data_generator import generate_all


def test_models_and_tables_exist():
    """Verify all 14 required tables exist in metadata."""
    expected_tables = {
        "users",
        "rooms",
        "equipment",
        "timetable",
        "meter_readings",
        "actions",
        "savings_records",
        "water_locations",
        "water_readings",
        "water_alerts",
        "complaints",
        "complaint_history",
        "settings",
        "sim_state",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_database_seeding_and_counts():
    """Verify seeding runs idempotently and populates all tables."""
    with get_session() as db:
        summary = generate_all(db, seed=42, reset=True)

    counts = summary["counts"]
    assert counts["rooms"] == 12
    assert counts["equipment"] == 46
    assert counts["users"] == 3
    assert counts["water_locations"] == 6
    assert counts["meter_readings"] == 16128
    assert counts["water_readings"] == 2016
    assert counts["water_alerts"] == 1
    assert counts["sim_state"] == 1


def test_user_authentication_hashes():
    """Verify seeded user credentials verify against stored hashes."""
    with get_session() as db:
        admin = db.query(models.User).filter_by(email="admin@ghostwatt.demo").first()
        student = db.query(models.User).filter_by(email="student@ghostwatt.demo").first()

        assert admin is not None
        assert admin.role == "admin"
        assert verify_password("admin123", admin.password_hash) is True
        assert verify_password("wrongpass", admin.password_hash) is False

        assert student is not None
        assert student.role == "student"
        assert verify_password("student123", student.password_hash) is True


def test_savings_records_unique_constraint():
    """Verify UNIQUE constraint on (action_id, interval_start)."""
    with get_session() as db:
        action = db.query(models.Action).first()
        assert action is not None

        dt = datetime(2026, 10, 10, 12, 0, 0)
        rec1 = models.SavingsRecord(
            action_id=action.id,
            interval_start=dt,
            pre_avg_kw=2.0,
            post_avg_kw=0.5,
            reduction_kw=1.5,
            credited_kwh=0.375,
            monetary_saving_inr=3.19,
            emissions_kg=0.266,
            verification_status="verified",
            is_simulated=True,
        )
        db.add(rec1)
        db.commit()

        rec2 = models.SavingsRecord(
            action_id=action.id,
            interval_start=dt,  # Duplicate action_id + interval_start
            pre_avg_kw=1.8,
            post_avg_kw=0.4,
            reduction_kw=1.4,
            credited_kwh=0.35,
            monetary_saving_inr=2.97,
            emissions_kg=0.248,
            verification_status="verified",
            is_simulated=True,
        )
        db.add(rec2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_water_alert_status_and_notes():
    """Verify water_alerts status and inspection_notes fields."""
    with get_session() as db:
        alert = db.query(models.WaterAlert).first()
        assert alert is not None
        assert alert.status in ["SUSPECTED", "CONFIRMED", "FALSE_ALARM"]
        assert "Suspected" in alert.inspection_notes or len(alert.inspection_notes) > 0


def test_sim_state_single_row():
    """Verify sim_state contains virtual_now, speed, and running."""
    with get_session() as db:
        state = db.query(models.SimState).filter_by(id=1).first()
        assert state is not None
        assert isinstance(state.virtual_now, datetime)
        assert state.speed == 1.0
        assert state.running is False

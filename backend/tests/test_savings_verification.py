"""
GhostWatt — tests/test_savings_verification.py
Comprehensive test suite for Verified Savings Meter and Corrective Actions.

SPEC §8 & Prompt Requirements:
1. Normal saving: AC switched off -> verified reduction credited with kWh, Rs, and CO2.
2. No reduction: appliance was already off or demand didn't drop -> 0 credited, NOT_VERIFIED.
3. Drop caused by a class ending: must NOT be credited -> 0 credited, NOT_VERIFIED.
4. Duplicate prevention: UNIQUE(action_id, interval_start) + in-code check prevent double counting.
5. Student attempting the action: returns HTTP 403 Forbidden.
6. API endpoints:
   - POST /actions/switch-off (admin only)
   - GET /savings/summary (claimed vs verified kWh, Rs, CO2, label "Simulated Verified Savings")
   - GET /savings/records
   - GET /actions
"""
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.db import models
from app.db.database import get_session
from app.main import app
from app.services.savings_verification import (
    calculate_savings_reduction,
    get_settings_rates,
    verify_action,
    verify_all_pending_actions,
)
from app.services import simulator


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def student_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "student@ghostwatt.demo", "password": "student123"},
    )
    assert resp.status_code == 200, f"Student login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "admin@ghostwatt.demo", "password": "admin123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Normal Saving Test
# ===========================================================================
def test_normal_saving():
    """
    Normal saving: Room has ghost load before action (e.g. 3.8 kW vs 0.1 kW expected).
    Admin switches off the appliance. Demand drops to 0.1 kW.
    Reduction is credited, status is VERIFIED, monetary and CO2 savings computed.
    """
    with get_session() as db:
        room = db.query(models.Room).filter(models.Room.room_code == "A-102").first()
        admin = db.query(models.User).filter(models.User.role == "admin").first()
        eq = db.query(models.Equipment).filter(
            models.Equipment.room_id == room.id,
            models.Equipment.kind == "ac",
        ).first()

        action_ts = datetime(2026, 10, 15, 22, 0, 0)  # night time, no class scheduled
        post_ts = action_ts + timedelta(minutes=15)

        # Create meter readings for pre and post intervals
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=action_ts,
            actual_demand_kw=3.75,
            interval_kwh=round(3.75 * 0.25, 4),
            source="simulated",
            is_simulated=True,
        ))
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=post_ts,
            actual_demand_kw=0.15,
            interval_kwh=round(0.15 * 0.25, 4),
            source="simulated",
            is_simulated=True,
        ))

        # Record action in PENDING state
        action = models.Action(
            room_id=room.id,
            user_id=admin.id,
            action_type="switch_off",
            equipment="AC",
            timestamp=action_ts,
            notes="Switched off overnight AC in A-102",
            verification_status="PENDING",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        # Run verification after post window closes
        rec = verify_action(action, db, window_minutes=15, current_ts=post_ts)

        assert rec is not None
        assert rec.action_id == action.id
        assert rec.verification_status == "VERIFIED"
        assert rec.pre_avg_kw == pytest.approx(3.75, rel=1e-2)
        assert rec.post_avg_kw == pytest.approx(0.15, rel=1e-2)
        # Reduction: min(3.75 - 0.15 = 3.60, 3.75 - 0.08 = 3.67) = 3.60 kW
        assert rec.reduction_kw == pytest.approx(3.60, rel=1e-2)
        assert rec.credited_kwh == pytest.approx(0.90, rel=1e-2)
        assert rec.monetary_saving_inr > 0.0
        assert rec.emissions_kg > 0.0
        assert action.verification_status == "VERIFIED"


# ===========================================================================
# 2. No Reduction Test
# ===========================================================================
def test_no_reduction():
    """
    No reduction: Appliance was already off or actual demand did not decrease.
    Reduction must be 0, credited_kwh must be 0, and status must be NOT_VERIFIED.
    Never credit when there is no reduction.
    """
    with get_session() as db:
        room = db.query(models.Room).filter(models.Room.room_code == "A-101").first()
        admin = db.query(models.User).filter(models.User.role == "admin").first()

        action_ts = datetime(2026, 10, 16, 23, 0, 0)
        post_ts = action_ts + timedelta(minutes=15)

        # Demand remained flat at baseline
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=action_ts,
            actual_demand_kw=0.10,
            interval_kwh=0.025,
            source="simulated",
            is_simulated=True,
        ))
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=post_ts,
            actual_demand_kw=0.10,
            interval_kwh=0.025,
            source="simulated",
            is_simulated=True,
        ))

        action = models.Action(
            room_id=room.id,
            user_id=admin.id,
            action_type="switch_off",
            equipment="AC",
            timestamp=action_ts,
            notes="Attempted switch-off but AC was not running",
            verification_status="PENDING",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        rec = verify_action(action, db, window_minutes=15, current_ts=post_ts)

        assert rec is not None
        assert rec.verification_status == "NOT_VERIFIED"
        assert rec.reduction_kw == 0.0
        assert rec.credited_kwh == 0.0
        assert rec.monetary_saving_inr == 0.0
        assert rec.emissions_kg == 0.0
        assert action.verification_status == "NOT_VERIFIED"


# ===========================================================================
# 3. Drop Caused by a Class Ending Test (Must NOT be Credited)
# ===========================================================================
def test_drop_caused_by_class_ending_not_credited():
    """
    Class ending guard:
    Class was scheduled during pre-action interval (e.g. 10:00-11:00 on Monday).
    Class ended at 11:00. The post-action interval (11:15) saw power drop naturally.
    The system must detect that pre had a class in session and post did not,
    and MUST NOT credit this drop!
    """
    with get_session() as db:
        room = db.query(models.Room).filter(models.Room.room_code == "A-101").first()
        admin = db.query(models.User).filter(models.User.role == "admin").first()

        # Find or create a timetable entry for room A-101
        # Let's use Monday (day_of_week=0) from 10:00 to 11:00
        tt = db.query(models.TimetableEntry).filter(
            models.TimetableEntry.room_id == room.id,
            models.TimetableEntry.day_of_week == 0,
            models.TimetableEntry.start_time == "10:00",
            models.TimetableEntry.end_time == "11:00",
        ).first()
        if not tt:
            tt = models.TimetableEntry(
                room_id=room.id,
                day_of_week=0,
                start_time="10:00",
                end_time="11:00",
                activity="Physics Lecture",
                expected_students=35,
                is_active=True,
            )
            db.add(tt)
            db.commit()

        # Action taken at 10:45 (Monday) during class
        # Monday date: 2026-10-19 is a Monday
        action_ts = datetime(2026, 10, 19, 10, 45, 0)
        post_ts = datetime(2026, 10, 19, 11, 0, 0)  # Class ends at 11:00

        # Readings: high during class, low after class ends
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=action_ts,
            actual_demand_kw=3.20,
            interval_kwh=0.80,
            source="simulated",
            is_simulated=True,
        ))
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=post_ts,
            actual_demand_kw=0.10,
            interval_kwh=0.025,
            source="simulated",
            is_simulated=True,
        ))

        action = models.Action(
            room_id=room.id,
            user_id=admin.id,
            action_type="switch_off",
            equipment="LIGHT",
            timestamp=action_ts,
            notes="Action right as class was ending",
            verification_status="PENDING",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        rec = verify_action(action, db, window_minutes=15, current_ts=post_ts)

        assert rec is not None
        # Drop caused by class ending must NOT be credited!
        assert rec.verification_status == "NOT_VERIFIED"
        assert rec.reduction_kw == 0.0
        assert rec.credited_kwh == 0.0
        assert rec.monetary_saving_inr == 0.0
        assert rec.emissions_kg == 0.0
        assert action.verification_status == "NOT_VERIFIED"


# ===========================================================================
# 4. Duplicate Prevention Test
# ===========================================================================
def test_duplicate_prevention():
    """
    Duplicate prevention:
    1. Verify action once -> creates SavingsRecord.
    2. Re-invoking verify_action() on the same action & interval returns the
       existing record without creating duplicate rows.
    3. Direct duplicate insertion raises IntegrityError due to UNIQUE(action_id, interval_start).
    """
    with get_session() as db:
        room = db.query(models.Room).filter(models.Room.room_code == "A-102").first()
        admin = db.query(models.User).filter(models.User.role == "admin").first()

        action_ts = datetime(2026, 10, 20, 21, 0, 0)
        post_ts = action_ts + timedelta(minutes=15)

        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=action_ts,
            actual_demand_kw=3.5,
            interval_kwh=0.875,
            source="simulated",
            is_simulated=True,
        ))
        db.add(models.MeterReading(
            room_id=room.id,
            timestamp=post_ts,
            actual_demand_kw=0.1,
            interval_kwh=0.025,
            source="simulated",
            is_simulated=True,
        ))

        action = models.Action(
            room_id=room.id,
            user_id=admin.id,
            action_type="switch_off",
            equipment="AC",
            timestamp=action_ts,
            notes="Test duplicate guard",
            verification_status="PENDING",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        # First verification run
        rec1 = verify_action(action, db, window_minutes=15, current_ts=post_ts)
        assert rec1 is not None

        count_before = (
            db.query(models.SavingsRecord)
            .filter(models.SavingsRecord.action_id == action.id)
            .count()
        )
        assert count_before == 1

        # Second verification run — must not create a duplicate
        rec2 = verify_action(action, db, window_minutes=15, current_ts=post_ts)
        assert rec2.id == rec1.id

        count_after = (
            db.query(models.SavingsRecord)
            .filter(models.SavingsRecord.action_id == action.id)
            .count()
        )
        assert count_after == 1

        # Attempt raw duplicate insertion in database -> IntegrityError
        dup_raw = models.SavingsRecord(
            action_id=action.id,
            interval_start=action_ts,
            pre_avg_kw=3.5,
            post_avg_kw=0.1,
            reduction_kw=3.4,
            credited_kwh=0.85,
            monetary_saving_inr=7.22,
            emissions_kg=0.603,
            verification_status="VERIFIED",
            is_simulated=True,
        )
        db.add(dup_raw)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ===========================================================================
# 5. Student Attempting Action Returns HTTP 403 Forbidden
# ===========================================================================
def test_student_attempting_action_returns_403(client, student_headers):
    """A student account attempting POST /actions/switch-off must receive 403 Forbidden."""
    resp = client.post(
        "/actions/switch-off",
        json={"room_id": 1, "equipment_id": 1, "notes": "Student trying switch-off"},
        headers=student_headers,
    )
    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower() or "admin" in resp.json()["detail"].lower()


# ===========================================================================
# 6. Admin Switch-off Flow and Automated Simulator Verification
# ===========================================================================
def test_admin_switch_off_and_automated_verification(client, admin_headers):
    """
    Complete end-to-end flow:
    1. Admin calls POST /actions/switch-off -> 201 Created with status PENDING.
    2. Simulated appliance is set to OFF.
    3. Simulator tick advances virtual_now and runs verify_all_pending_actions().
    4. Action transitions from PENDING to verified/not_verified.
    """
    with get_session() as db:
        room = db.query(models.Room).filter(models.Room.room_code == "A-102").first()
        eq = db.query(models.Equipment).filter(
            models.Equipment.room_id == room.id,
            models.Equipment.kind == "ac",
        ).first()
        room_id = room.id
        eq_id = eq.id

    # 1. Admin triggers switch-off
    resp = client.post(
        "/actions/switch-off",
        json={
            "room_id": room_id,
            "equipment_id": eq_id,
            "notes": "Admin switching off AC via dashboard",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Switch-off failed: {resp.text}"
    body = resp.json()
    assert body["verification_status"] == "PENDING"
    assert body["claimed_reduction_kw"] > 0
    assert body["claimed_kwh_per_interval"] > 0
    assert body["data_source"] == "simulated"
    action_id = body["id"]

    # Verify appliance state set to OFF
    with get_session() as db:
        updated_eq = db.query(models.Equipment).filter(models.Equipment.id == eq_id).first()
        assert updated_eq.state == "OFF"

    # 2. Advance simulator clock by one 15-minute tick
    with get_session() as db:
        tick_summary = simulator.tick(db, delta_minutes=15)
        assert tick_summary["readings_count"] > 0

    # 3. Check that the action was evaluated by the tick
    with get_session() as db:
        act = db.query(models.Action).filter(models.Action.id == action_id).first()
        assert act.verification_status in ("VERIFIED", "PARTIAL", "NOT_VERIFIED")


# ===========================================================================
# 7. Savings Summary, Records, and Actions Endpoints
# ===========================================================================
def test_savings_and_actions_endpoints(client, admin_headers, student_headers):
    """
    Validate GET /savings/summary, GET /savings/records, and GET /actions:
    - Proper data_source: "simulated"
    - Summary label: "Simulated Verified Savings"
    - Both student and admin can read these analytical endpoints.
    """
    # GET /savings/summary
    summary_resp = client.get("/savings/summary", headers=student_headers)
    assert summary_resp.status_code == 200
    s_data = summary_resp.json()
    assert s_data["label"] == "Simulated Verified Savings"
    assert s_data["data_source"] == "simulated"
    assert "claimed_kwh" in s_data
    assert "verified_kwh" in s_data
    assert "monetary_saving_inr" in s_data
    assert "emissions_co2_kg" in s_data
    assert "total_actions" in s_data
    assert "verified_actions" in s_data
    assert "pending_actions" in s_data

    # GET /savings/records
    records_resp = client.get("/savings/records", headers=admin_headers)
    assert records_resp.status_code == 200
    r_data = records_resp.json()
    assert r_data["data_source"] == "simulated"
    assert isinstance(r_data["records"], list)
    assert r_data["count"] == len(r_data["records"])
    assert "total_credited_kwh" in r_data
    assert "total_monetary_saving_inr" in r_data

    # GET /actions
    actions_resp = client.get("/actions", headers=student_headers)
    assert actions_resp.status_code == 200
    a_data = actions_resp.json()
    assert a_data["data_source"] == "simulated"
    assert isinstance(a_data["actions"], list)
    assert a_data["count"] == len(a_data["actions"])
    if a_data["actions"]:
        first_act = a_data["actions"][0]
        assert "room_code" in first_act
        assert "equipment_kind" in first_act
        assert "user_email" in first_act
        assert "verification_status" in first_act

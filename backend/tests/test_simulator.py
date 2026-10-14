"""
Eco-Campus — tests/test_simulator.py
Unit and integration tests for virtual clock, simulation ticking, equipment model,
speed control, live snapshot performance, and RBAC enforcement.
"""
from datetime import datetime, timedelta
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_session
from app.db import models
from app.services.expected_demand import expected_kw
from app.services.ghost_load import calculate_ghost_load_kw
from app.services.simulator import (
    calculate_sleep_duration,
    clear_appliance_states,
    get_or_create_sim_state,
    reset_sim,
    set_appliance,
    set_sim_running,
    set_sim_speed,
    tick,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def student_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "student@ghostwatt.demo", "password": "student123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "admin@ghostwatt.demo", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. SIMULATION ENGINE: N TICKS CONSISTENCY AND GHOST LOAD MATCHING
# ===========================================================================

def test_tick_advances_clock_and_generates_consistent_readings():
    """
    Test that running N ticks advances virtual_now by N * 15 minutes,
    creates readings at consistent 15-minute timestamps for all rooms,
    and ghost load calculations match the core formula max(0, actual - expected).
    """
    N = 8  # 8 intervals = 2 hours
    anchor_time = datetime(2026, 11, 1, 8, 0, 0)

    with get_session() as db:
        # Pre-clean test timestamp range for isolation
        db.query(models.MeterReading).filter(models.MeterReading.timestamp >= anchor_time).delete()
        db.commit()

        reset_sim(db, to_date=anchor_time)
        clear_appliance_states()

        rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
        equipment = db.query(models.Equipment).all()
        eq_by_room = {}
        for eq in equipment:
            eq_by_room.setdefault(eq.room_id, []).append(eq)
        timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
        tt_by_room = {}
        for t in timetables:
            tt_by_room.setdefault(t.room_id, []).append(t)

        start_reading_count = db.query(models.MeterReading).count()

        # Step N times
        ticked_timestamps = []
        for i in range(N):
            tick_summary = tick(db, delta_minutes=15)
            assert tick_summary["rooms_ticked"] == len(rooms)
            state = get_or_create_sim_state(db)
            ticked_timestamps.append(state.virtual_now)

        # 1. Virtual clock advanced by exactly N * 15 minutes
        final_state = get_or_create_sim_state(db)
        expected_final_time = anchor_time + timedelta(minutes=N * 15)
        assert final_state.virtual_now == expected_final_time

        # 2. Consistent 15-minute intervals between consecutive ticks
        for i in range(len(ticked_timestamps) - 1):
            delta = ticked_timestamps[i + 1] - ticked_timestamps[i]
            assert delta == timedelta(minutes=15)

        # 3. Exactly N new readings per room
        end_reading_count = db.query(models.MeterReading).count()
        assert end_reading_count - start_reading_count == N * len(rooms)

        # 4. For each room, verify timestamps and that ghost load matches the engine
        for room in rooms:
            room_readings = (
                db.query(models.MeterReading)
                .filter(
                    models.MeterReading.room_id == room.id,
                    models.MeterReading.timestamp > anchor_time,
                    models.MeterReading.timestamp <= expected_final_time,
                )
                .order_by(models.MeterReading.timestamp.asc())
                .all()
            )
            assert len(room_readings) == N

            r_eq = eq_by_room.get(room.id, [])
            r_tt = tt_by_room.get(room.id, [])

            for j, mr in enumerate(room_readings):
                # Verify consistent spacing
                expected_ts = anchor_time + timedelta(minutes=(j + 1) * 15)
                assert mr.timestamp == expected_ts

                # Verify actual demand >= idle baseline
                assert mr.actual_demand_kw >= room.idle_baseline_kw - 0.05
                assert round(mr.actual_demand_kw * 0.25, 4) == round(mr.interval_kwh, 4)

                # Verify ghost load matches the engine formula
                exp_kw, _ = expected_kw(room, r_eq, r_tt, mr.timestamp)
                calculated_ghost = calculate_ghost_load_kw(mr.actual_demand_kw, exp_kw)
                expected_ghost = max(0.0, mr.actual_demand_kw - exp_kw)
                assert abs(calculated_ghost - expected_ghost) < 1e-4


def test_interactive_appliance_toggle_increases_actual_demand():
    """Toggling an appliance ON increases subsequent actual demand in tick()."""
    target_time = datetime(2026, 11, 2, 23, 0, 0)  # Night time, room empty

    with get_session() as db:
        # Pre-clean test timestamp range
        db.query(models.MeterReading).filter(models.MeterReading.timestamp >= target_time).delete()
        db.commit()

        reset_sim(db, to_date=target_time)
        clear_appliance_states()

        room = db.query(models.Room).filter(models.Room.room_code == "A-101").first()
        ac_eq = db.query(models.Equipment).filter(models.Equipment.room_id == room.id, models.Equipment.kind == "ac").first()

        # Tick with AC default OFF
        set_appliance("A-101", "ac", False)
        tick(db, delta_minutes=15)
        st_off = get_or_create_sim_state(db)
        r_off = (
            db.query(models.MeterReading)
            .filter(models.MeterReading.room_id == room.id, models.MeterReading.timestamp == st_off.virtual_now)
            .first()
        )

        # Force AC ON and tick
        set_appliance("A-101", "ac", True)
        tick(db, delta_minutes=15)
        st_on = get_or_create_sim_state(db)
        r_on = (
            db.query(models.MeterReading)
            .filter(models.MeterReading.room_id == room.id, models.MeterReading.timestamp == st_on.virtual_now)
            .first()
        )

        expected_extra_kw = ac_eq.rated_kw * ac_eq.count
        diff = r_on.actual_demand_kw - r_off.actual_demand_kw
        assert diff >= expected_extra_kw - 0.1  # Allowing subtle sensor noise
        clear_appliance_states()


def test_hourly_water_readings_generated_on_hour_boundary():
    """Water readings are generated whenever virtual clock hits an hour boundary (minute == 0)."""
    # Start at 09:45; next tick is 10:00 (hour boundary)
    start_time = datetime(2026, 10, 15, 9, 45, 0)

    with get_session() as db:
        reset_sim(db, to_date=start_time)
        w_count_pre = db.query(models.WaterReading).count()
        loc_count = db.query(models.WaterLocation).count()

        summary = tick(db, delta_minutes=15)
        assert summary["water_readings_count"] == loc_count

        w_count_post = db.query(models.WaterReading).count()
        assert w_count_post - w_count_pre == loc_count


def test_speed_to_sleep_duration_scaling():
    """Speed scaling behaves as an inverse time-delay multiplier."""
    d_1x = calculate_sleep_duration(1.0, base_seconds=2.0)
    d_2x = calculate_sleep_duration(2.0, base_seconds=2.0)
    d_10x = calculate_sleep_duration(10.0, base_seconds=2.0)

    assert d_1x == 2.0
    assert d_2x == 1.0
    assert d_10x == 0.2


# ===========================================================================
# 2. SIMULATION CONTROL ROUTES & PERMISSIONS
# ===========================================================================

def test_sim_state_and_control_admin_routes(client, admin_headers):
    """Admin can start, pause, change speed, step tick, and reset the simulation."""
    # 1. GET /sim/state
    resp = client.get("/sim/state", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "virtual_now" in data
    assert "speed" in data
    assert "running" in data
    assert data["data_source"] == "simulated"

    # 2. POST /sim/start
    start_resp = client.post("/sim/start", headers=admin_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["running"] is True

    # 3. POST /sim/pause
    pause_resp = client.post("/sim/pause", headers=admin_headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["running"] is False

    # 4. POST /sim/speed with positive value
    speed_resp = client.post("/sim/speed", json={"speed": 4.5}, headers=admin_headers)
    assert speed_resp.status_code == 200
    assert speed_resp.json()["speed"] == 4.5

    # 5. POST /sim/speed non-positive rejection
    bad_speed = client.post("/sim/speed", json={"speed": -2.0}, headers=admin_headers)
    assert bad_speed.status_code in (400, 422)

    # 6. POST /sim/tick manually
    tick_resp = client.post("/sim/tick", headers=admin_headers)
    assert tick_resp.status_code == 200

    # 7. POST /sim/reset
    reset_resp = client.post("/sim/reset", json={"to_date": "2026-10-12T00:00:00"}, headers=admin_headers)
    assert reset_resp.status_code == 200
    assert reset_resp.json()["virtual_now"].startswith("2026-10-12T00:00:00")
    assert reset_resp.json()["running"] is False


def test_sim_routes_rbac_enforcement(client, student_headers):
    """Student receives 403 Forbidden on all simulation administrative routes."""
    sim_endpoints = [
        ("POST", "/sim/start", None),
        ("POST", "/sim/pause", None),
        ("POST", "/sim/speed", {"speed": 2.0}),
        ("POST", "/sim/reset", None),
        ("GET", "/sim/state", None),
        ("POST", "/sim/tick", None),
    ]
    for method, path, payload in sim_endpoints:
        # Check without token -> 401
        r_unauth = client.request(method, path, json=payload)
        assert r_unauth.status_code == 401

        # Check with student token -> 403
        r_stu = client.request(method, path, json=payload, headers=student_headers)
        assert r_stu.status_code == 403


# ===========================================================================
# 3. LIVE SNAPSHOT ENDPOINT (ACCURACY & PERFORMANCE < 100MS)
# ===========================================================================

def test_live_snapshot_authenticated_user_access_and_fields(client, student_headers):
    """Students can access GET /live/snapshot and receive complete consolidated state."""
    # Ensure simulation clock is seeded
    with get_session() as db:
        tick(db, delta_minutes=15)

    resp = client.get("/live/snapshot", headers=student_headers)
    assert resp.status_code == 200
    snap = resp.json()

    # Core required fields
    assert "virtual_now" in snap
    assert "total_actual_kw" in snap
    assert "total_expected_kw" in snap
    assert "total_ghost_kw" in snap
    assert "cost_per_hour" in snap
    assert "co2_per_hour" in snap
    assert "fan_equivalent" in snap
    assert "rooms" in snap
    assert "active_alerts" in snap
    assert snap["accelerated_time"] is True
    assert snap["data_source"] == "simulated"

    # Rooms breakdown
    assert len(snap["rooms"]) == 12
    for rm in snap["rooms"]:
        assert "room_code" in rm
        assert "actual_kw" in rm
        assert "expected_kw" in rm
        assert "ghost_kw" in rm
        assert "status" in rm
        assert "reason_code" in rm
        assert "reason_explanation" in rm
        assert rm["ghost_kw"] >= 0.0


def test_live_snapshot_sub_100ms_performance(client, student_headers):
    """
    Verify snapshot response latency is fast (< 100 ms target).
    Tests across multiple repeated warm calls.
    """
    # Warm up cache / connection
    client.get("/live/snapshot", headers=student_headers)

    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        resp = client.get("/live/snapshot", headers=student_headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert resp.status_code == 200
        times.append(elapsed_ms)

    avg_time_ms = sum(times) / len(times)
    # Target under 100 ms
    assert avg_time_ms < 100.0, f"Average snapshot latency too high: {avg_time_ms:.1f}ms > 100ms"

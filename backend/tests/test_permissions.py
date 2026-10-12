"""
GhostWatt — tests/test_permissions.py
Role-based access control (RBAC), authentication enforcement, and input validation tests.

Specifications verified:
- Unauthenticated requests (no token / invalid token) return HTTP 401 Unauthorized.
- Student accounts receive HTTP 403 Forbidden on EVERY administrator route.
- Student accounts can successfully access all analytical read endpoints (HTTP 200 OK).
- Administrator accounts can successfully perform mutations and writes across all modules.
- Strict input validation is enforced (non-positive settings, backward timetable times, invalid appliances).
- Every response includes `data_source: "simulated"` for frontend labeling.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def student_headers(client):
    """Obtain authorization headers for the seeded student account."""
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "student@ghostwatt.demo", "password": "student123"},
    )
    assert resp.status_code == 200, f"Student login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_headers(client):
    """Obtain authorization headers for the seeded admin account."""
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "admin@ghostwatt.demo", "password": "admin123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. NO TOKEN / INVALID TOKEN -> HTTP 401
# ===========================================================================

PROTECTED_ENDPOINTS = [
    ("GET", "/auth/me", None),
    ("GET", "/dashboard/summary", None),
    ("GET", "/electricity/series", None),
    ("GET", "/ghost/current", None),
    ("GET", "/ghost/ranking", None),
    ("GET", "/ghost/switch-off-list", None),
    ("GET", "/ghost/room/1/explain", None),
    ("GET", "/rooms", None),
    ("GET", "/rooms/1", None),
    ("POST", "/rooms", {"room_code": "TEST-1", "block": "A", "name": "Test", "room_type": "classroom", "capacity": 30, "idle_baseline_kw": 0.1}),
    ("PUT", "/rooms/1", {"name": "Updated"}),
    ("DELETE", "/rooms/1", None),
    ("GET", "/rooms/1/equipment", None),
    ("POST", "/rooms/1/equipment", {"kind": "fan", "rated_kw": 0.075, "count": 2, "state": "OFF"}),
    ("PUT", "/rooms/equipment/1", {"count": 4}),
    ("DELETE", "/rooms/equipment/1", None),
    ("GET", "/timetable", None),
    ("GET", "/timetable/1", None),
    ("POST", "/timetable", {"room_id": 1, "day_of_week": 0, "start_time": "09:00", "end_time": "10:00"}),
    ("PUT", "/timetable/1", {"activity": "Updated Lecture"}),
    ("DELETE", "/timetable/1", None),
    ("GET", "/settings", None),
    ("PUT", "/settings", {"settings": {"electricity_price_per_kwh": "9.50"}}),
    ("GET", "/water/series", None),
    ("GET", "/water/alerts", None),
    ("PATCH", "/water/alerts/1", {"status": "CONFIRMED"}),
]


@pytest.mark.parametrize("method,path,payload", PROTECTED_ENDPOINTS)
def test_no_token_returns_401(client, method, path, payload):
    """Every protected endpoint without an Authorization header must yield 401 Unauthorized."""
    resp = client.request(method, path, json=payload)
    assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"
    data = resp.json()
    assert "detail" in data


def test_invalid_token_returns_401(client):
    """Malformed or expired tokens must yield 401 Unauthorized."""
    headers = {"Authorization": "Bearer invalid_garbage_token_12345"}
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 401
    assert "detail" in resp.json()


# ===========================================================================
# 2. STUDENT USER GETS 403 ON EVERY ADMIN ROUTE
# ===========================================================================

ADMIN_MUTATION_ENDPOINTS = [
    # Room Admin Routes
    ("POST", "/rooms", {"room_code": "STU-01", "block": "A", "name": "Student Created", "room_type": "classroom", "capacity": 40, "idle_baseline_kw": 0.15}),
    ("PUT", "/rooms/1", {"name": "Hacked Name"}),
    ("DELETE", "/rooms/1", None),
    # Equipment Admin Routes
    ("POST", "/rooms/1/equipment", {"kind": "light", "rated_kw": 0.04, "count": 10, "state": "OFF"}),
    ("PUT", "/rooms/equipment/1", {"count": 20}),
    ("DELETE", "/rooms/equipment/1", None),
    # Timetable Admin Routes
    ("POST", "/timetable", {"room_id": 1, "day_of_week": 1, "start_time": "11:00", "end_time": "12:00", "activity": "Student Scheduled"}),
    ("PUT", "/timetable/1", {"activity": "Student Overwrite"}),
    ("DELETE", "/timetable/1", None),
    # Settings Admin Route
    ("PUT", "/settings", {"settings": {"electricity_price_per_kwh": "100.0"}}),
    # Water Alert Admin Route
    ("PATCH", "/water/alerts/1", {"status": "FALSE_ALARM", "inspection_notes": "Student triage"}),
]


@pytest.mark.parametrize("method,path,payload", ADMIN_MUTATION_ENDPOINTS)
def test_student_gets_403_on_admin_routes(client, student_headers, method, path, payload):
    """A user with the student role must receive 403 Forbidden on all administrative actions."""
    resp = client.request(method, path, json=payload, headers=student_headers)
    assert resp.status_code == 403, (
        f"Student unexpectedly allowed or received wrong status on {method} {path}: "
        f"{resp.status_code} ({resp.text})"
    )
    detail = resp.json().get("detail", "")
    assert "Admin" in detail or "forbidden" in detail.lower()


# ===========================================================================
# 3. STUDENT HAS ACCESS TO ALL READ / ANALYTICAL ROUTES
# ===========================================================================

def test_student_can_read_all_analytics(client, student_headers):
    """Students can read dashboard, series, rankings, triage, and explainability endpoints."""
    # Auth Profile
    me = client.get("/auth/me", headers=student_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "student"

    # Dashboard Summary
    dash = client.get("/dashboard/summary", headers=student_headers)
    assert dash.status_code == 200
    assert dash.json()["data_source"] == "simulated"
    assert "ghost_kwh" in dash.json()

    # Electricity Series
    elec = client.get("/electricity/series?block=A", headers=student_headers)
    assert elec.status_code == 200
    assert elec.json()["data_source"] == "simulated"
    assert isinstance(elec.json()["series"], list)

    # Ghost Load Endpoints (both /ghost and /ghost-load aliases)
    for prefix in ("/ghost", "/ghost-load"):
        curr = client.get(f"{prefix}/current", headers=student_headers)
        assert curr.status_code == 200
        assert curr.json()["data_source"] == "simulated"

        rank = client.get(f"{prefix}/ranking", headers=student_headers)
        assert rank.status_code == 200
        assert rank.json()["data_source"] == "simulated"

        switch_off = client.get(f"{prefix}/switch-off-list", headers=student_headers)
        assert switch_off.status_code == 200
        assert switch_off.json()["data_source"] == "simulated"

        explain = client.get(f"{prefix}/room/A-101/explain", headers=student_headers)
        assert explain.status_code == 200
        assert explain.json()["data_source"] == "simulated"

    # Rooms & Timetable Queries
    rooms = client.get("/rooms", headers=student_headers)
    assert rooms.status_code == 200
    assert rooms.json()["data_source"] == "simulated"

    tt = client.get("/timetable", headers=student_headers)
    assert tt.status_code == 200
    assert tt.json()["data_source"] == "simulated"

    settings_get = client.get("/settings", headers=student_headers)
    assert settings_get.status_code == 200
    assert settings_get.json()["data_source"] == "simulated"

    water_series = client.get("/water/series", headers=student_headers)
    assert water_series.status_code == 200
    assert water_series.json()["data_source"] == "simulated"

    water_alerts = client.get("/water/alerts", headers=student_headers)
    assert water_alerts.status_code == 200
    assert water_alerts.json()["data_source"] == "simulated"


# ===========================================================================
# 4. ADMIN CAN PERFORM WRITES AND PASS VALIDATION
# ===========================================================================

def test_admin_crud_and_validation(client, admin_headers):
    """Admin can create, update, and manage entities with strict schema validation."""
    # 1. Admin Create Room
    new_room_code = "ADM-999"
    # Clean up any leftover test room from a previous interrupted run
    all_rooms = client.get("/rooms", headers=admin_headers).json().get("items", [])
    for rm in all_rooms:
        if rm["room_code"] == new_room_code:
            client.delete(f"/rooms/{rm['id']}", headers=admin_headers)

    room_payload = {
        "room_code": new_room_code,
        "block": "C",
        "name": "Admin Test Lab",
        "room_type": "lab",
        "capacity": 25,
        "idle_baseline_kw": 0.25,
    }
    r_create = client.post("/rooms", json=room_payload, headers=admin_headers)
    assert r_create.status_code == 201
    created_room = r_create.json()
    room_id = created_room["id"]
    assert created_room["room_code"] == new_room_code
    assert created_room["data_source"] == "simulated"

    # 2. Admin Duplicate Room Code check
    r_dup = client.post("/rooms", json=room_payload, headers=admin_headers)
    assert r_dup.status_code == 400

    # 3. Admin Update Room
    r_up = client.put(f"/rooms/{room_id}", json={"name": "Renamed Admin Lab"}, headers=admin_headers)
    assert r_up.status_code == 200
    assert r_up.json()["name"] == "Renamed Admin Lab"

    # 4. Admin Add Equipment to Room
    eq_payload = {
        "kind": "lab_equipment",
        "rated_kw": 1.5,
        "count": 4,
        "state": "OFF",
        "expected_in_class": 1.0,
    }
    eq_resp = client.post(f"/rooms/{room_id}/equipment", json=eq_payload, headers=admin_headers)
    assert eq_resp.status_code == 201
    eq_data = eq_resp.json()
    eq_id = eq_data["id"]
    assert eq_data["kind"] == "lab_equipment"
    assert eq_data["data_source"] == "simulated"

    # 5. Invalid Equipment Kind Check
    eq_bad = client.post(
        f"/rooms/{room_id}/equipment",
        json={"kind": "plasma_cannon", "rated_kw": 5.0, "count": 1, "state": "OFF"},
        headers=admin_headers,
    )
    assert eq_bad.status_code == 400

    # 6. Admin Update Equipment
    eq_update = client.put(f"/rooms/equipment/{eq_id}", json={"count": 6}, headers=admin_headers)
    assert eq_update.status_code == 200
    assert eq_update.json()["count"] == 6

    # 7. Admin Create Timetable Entry
    tt_payload = {
        "room_id": room_id,
        "day_of_week": 2,
        "start_time": "10:00",
        "end_time": "12:00",
        "activity": "Advanced Robotics Practical",
        "expected_students": 20,
    }
    tt_resp = client.post("/timetable", json=tt_payload, headers=admin_headers)
    assert tt_resp.status_code == 201
    tt_data = tt_resp.json()
    tt_id = tt_data["id"]
    assert tt_data["activity"] == "Advanced Robotics Practical"
    assert tt_data["data_source"] == "simulated"

    # 8. Timetable Validation: end_time <= start_time
    tt_bad = client.post(
        "/timetable",
        json={
            "room_id": room_id,
            "day_of_week": 2,
            "start_time": "15:00",
            "end_time": "14:00",  # Backward time
            "activity": "Paradox Session",
        },
        headers=admin_headers,
    )
    assert tt_bad.status_code in (400, 422)

    # 9. Admin Update Settings with strictly positive values
    settings_payload = {
        "settings": {
            "electricity_price_per_kwh": "9.25",
            "emissions_factor_kg_per_kwh": "0.75",
        }
    }
    s_resp = client.put("/settings", json=settings_payload, headers=admin_headers)
    assert s_resp.status_code == 200
    assert s_resp.json()["settings"]["electricity_price_per_kwh"] == "9.25"
    assert s_resp.json()["data_source"] == "simulated"

    # 10. Settings Validation: non-positive value rejection
    s_bad = client.put(
        "/settings",
        json={"settings": {"electricity_price_per_kwh": "-5.0"}},
        headers=admin_headers,
    )
    assert s_bad.status_code in (400, 422)
    assert "positive" in str(s_bad.json()).lower()

    # 11. Admin Triage Water Alert
    water_alerts = client.get("/water/alerts", headers=admin_headers).json()["alerts"]
    if water_alerts:
        first_alert_id = water_alerts[0]["id"]
        patch_resp = client.patch(
            f"/water/alerts/{first_alert_id}",
            json={"status": "CONFIRMED", "inspection_notes": "Plumber repaired leaking flange in Restroom C"},
            headers=admin_headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "CONFIRMED"
        assert patch_resp.json()["inspection_notes"] == "Plumber repaired leaking flange in Restroom C"
        assert patch_resp.json()["data_source"] == "simulated"

    # Cleanup created entities
    client.delete(f"/timetable/{tt_id}", headers=admin_headers)
    client.delete(f"/rooms/equipment/{eq_id}", headers=admin_headers)
    client.delete(f"/rooms/{room_id}", headers=admin_headers)

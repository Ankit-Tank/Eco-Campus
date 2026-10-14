"""
Eco-Campus — tests/test_final_backend.py
Comprehensive test suite validating:
1. POST /sim/scenario/demo (Admin reset to evening, A-102 AC ghost load injection, alert firing, switch-off, and rapid verification).
2. Equivalents (ceiling fans and water buckets with assumption text) across all responses.
3. Campus block leaderboard (GET /leaderboard/blocks) with sustainability scores and grades.
4. Student peer report (POST /reports/appliance-left-on) generating admin signals and notifications.
5. Consistent pagination and error handling across endpoints.
"""
import pytest
from app.db.database import get_session
from app.db import models
from app.services.simulator import tick


# ===========================================================================
# 1. DEMO SCENARIO: A-102 AC GHOST EVENT & SAVINGS VERIFICATION WORKFLOW
# ===========================================================================

def test_demo_scenario_admin_only(client, student_headers):
    """Students cannot trigger the demo scenario reset (403 Forbidden)."""
    resp = client.post("/sim/scenario/demo", headers=student_headers)
    assert resp.status_code == 403


def test_demo_scenario_injection_and_verification_flow(client, admin_headers):
    """
    POST /sim/scenario/demo resets the sim clock to evening (21:30),
    forces an AC-left-on ghost event in room A-102, fires the alert,
    allows an admin to register a switch-off action, and completes
    verification on simulator advance.
    """
    # 1. Trigger demo scenario
    resp = client.post("/sim/scenario/demo", headers=admin_headers)
    assert resp.status_code == 200
    demo_data = resp.json()

    assert demo_data["status"] == "demo_scenario_active"
    assert demo_data["room_code"] == "A-102"
    assert "21:30" in demo_data["virtual_now"]
    assert demo_data["speed"] == 60.0
    assert demo_data["ghost_kw"] > 1.0
    assert demo_data["alert_status"] == "TRIGGERED"

    # 2. Verify Room A-102 state in live snapshot
    snap_resp = client.get("/live/snapshot", headers=admin_headers)
    assert snap_resp.status_code == 200
    snap = snap_resp.json()
    a102_room = next((r for r in snap["rooms"] if r["room_code"] == "A-102"), None)
    assert a102_room is not None
    assert a102_room["status"] in ("High Usage", "Possible Idle Load")
    assert a102_room["ghost_kw"] > 1.0

    # 3. Locate the AC equipment in A-102
    room_detail = client.get(f"/rooms/{demo_data['room_id']}", headers=admin_headers).json()
    ac_eq = next((eq for eq in room_detail["equipment"] if eq["kind"] == "ac"), None)
    assert ac_eq is not None

    # 4. Action: Switch off the AC
    action_payload = {
        "room_id": demo_data["room_id"],
        "equipment_id": ac_eq["id"],
        "notes": "Patrol guard switched off forgotten AC unit in A-102.",
    }
    act_resp = client.post("/actions/switch-off", json=action_payload, headers=admin_headers)
    assert act_resp.status_code == 201
    action_data = act_resp.json()
    assert action_data["verification_status"] == "PENDING"
    assert action_data["claimed_reduction_kw"] > 0.0
    action_id = action_data["id"]

    # 5. Advance simulator by 2 ticks (30 simulated minutes = 0.5s at 60x speed)
    with get_session() as db:
        tick(db, delta_minutes=15)
        tick(db, delta_minutes=15)

    # 6. Verify that action status changed to VERIFIED or PARTIAL and savings were recorded
    act_check = client.get(f"/actions/{action_id}", headers=admin_headers)
    assert act_check.status_code == 200
    updated_act = act_check.json()
    assert updated_act["verification_status"] in ("VERIFIED", "PARTIAL")

    # 7. Check savings records list
    sav_resp = client.get(f"/savings/records?action_id={action_id}", headers=admin_headers)
    assert sav_resp.status_code == 200
    records = sav_resp.json()["records"]
    assert len(records) >= 1
    assert records[0]["credited_kwh"] > 0.0
    assert records[0]["monetary_saving_inr"] > 0.0


# ===========================================================================
# 2. EQUIVALENTS AND ASSUMPTION STRINGS ACROSS RESPONSES
# ===========================================================================

def test_equivalents_and_assumptions_dashboard_summary(client, student_headers):
    """GET /dashboard/summary contains fan, bucket equivalents, and explanatory assumptions."""
    resp = client.get("/dashboard/summary", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "fan_equivalents" in data
    assert "bucket_equivalents" in data
    assert "fan_assumption" in data
    assert "bucket_assumption" in data
    assert data["fan_assumption"] is not None
    assert "75W" in data["fan_assumption"] or "fan" in data["fan_assumption"].lower()
    assert "15L" in data["bucket_assumption"] or "bucket" in data["bucket_assumption"].lower()
    assert "assumptions" in data
    assert "tariff" in data["assumptions"]
    assert "emissions" in data["assumptions"]


def test_equivalents_and_assumptions_live_snapshot(client, student_headers):
    """GET /live/snapshot includes fan equivalent and assumption metadata."""
    resp = client.get("/live/snapshot", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "fan_equivalent" in data
    assert "fan_assumption" in data
    assert data["fan_assumption"] is not None
    assert "assumptions" in data
    assert "fan" in data["assumptions"]


def test_equivalents_and_assumptions_ghost_current_and_ranking(client, student_headers):
    """GET /ghost/current and /ghost/ranking include fan equivalents and assumptions."""
    cur_resp = client.get("/ghost/current", headers=student_headers)
    assert cur_resp.status_code == 200
    cur_data = cur_resp.json()
    assert "fan_equivalents" in cur_data
    assert "fan_assumption" in cur_data
    assert "assumptions" in cur_data

    rank_resp = client.get("/ghost/ranking", headers=student_headers)
    assert rank_resp.status_code == 200
    rank_data = rank_resp.json()
    assert "fan_equivalents" in rank_data
    assert "fan_assumption" in rank_data
    assert "assumptions" in rank_data


def test_equivalents_and_assumptions_water_series_and_alerts(client, student_headers):
    """GET /water/series and /water/alerts include bucket equivalents and assumptions."""
    ws_resp = client.get("/water/series", headers=student_headers)
    assert ws_resp.status_code == 200
    ws_data = ws_resp.json()
    assert "bucket_equivalents" in ws_data
    assert "bucket_assumption" in ws_data
    assert "assumptions" in ws_data

    wa_resp = client.get("/water/alerts", headers=student_headers)
    assert wa_resp.status_code == 200
    wa_data = wa_resp.json()
    for alert in wa_data["alerts"]:
        assert "bucket_equivalents" in alert
        assert "bucket_assumption" in alert
        assert "assumptions" in alert


# ===========================================================================
# 3. CAMPUS BLOCK LEADERBOARD: GET /leaderboard/blocks
# ===========================================================================

def test_leaderboard_requires_authentication(client):
    """Unauthenticated call to /leaderboard/blocks returns 401."""
    resp = client.get("/leaderboard/blocks")
    assert resp.status_code == 401


def test_leaderboard_blocks_structure_and_scoring(client, student_headers):
    """GET /leaderboard/blocks returns ranked campus blocks with sustainability scores and grades."""
    resp = client.get("/leaderboard/blocks?period=all", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "blocks" in data
    assert len(data["blocks"]) >= 3  # Blocks A, B, C
    assert "best_block" in data
    assert "worst_block" in data
    assert "assumptions" in data
    assert data["data_source"] == "simulated"

    ranks = [b["rank"] for b in data["blocks"]]
    assert ranks == sorted(ranks)  # Ordered by rank (1, 2, 3...)

    for item in data["blocks"]:
        assert "block" in item
        assert "name" in item
        assert item["actual_kwh"] >= 0.0
        assert item["expected_kwh"] >= 0.0
        assert item["ghost_kwh"] >= 0.0
        assert 0.0 <= item["sustainability_score"] <= 100.0
        assert item["grade"] in ("A+", "A", "B", "C", "D")
        assert "fan_equivalents" in item
        assert item["fan_assumption"] is not None


# ===========================================================================
# 4. STUDENT APPLIANCE-LEFT-ON REPORT SIGNAL: POST /reports/appliance-left-on
# ===========================================================================

def test_student_appliance_left_on_report(client, student_headers, admin_headers):
    """Students can submit peer-observation reports for left-on appliances."""
    payload = {
        "room_id": 2,  # A-102
        "appliance_kind": "ac",
        "notes": "Spotted AC running at full blast while looking through classroom window after hours.",
    }
    resp = client.post("/reports/appliance-left-on", json=payload, headers=student_headers)
    assert resp.status_code == 201
    rep = resp.json()

    assert rep["complaint_code"].startswith("AL-")
    assert rep["category"] == "appliance_left_on"
    assert rep["status"] == "signal_recorded"
    assert rep["room_code"] == "A-102"
    assert rep["block"] == "A"
    assert rep["data_source"] == "simulated"

    # Verify that admin sees this signal in complaints list
    complaints_resp = client.get("/complaints?category=appliance_left_on", headers=admin_headers)
    assert complaints_resp.status_code == 200
    items = complaints_resp.json()["complaints"]
    matching = [c for c in items if c["complaint_code"] == rep["complaint_code"]]
    assert len(matching) == 1

    # Verify admin received notification
    notifs_resp = client.get("/complaints/notifications/admin", headers=admin_headers)
    assert notifs_resp.status_code == 200
    notifs = notifs_resp.json()["notifications"]
    assert any(n["reference_id"] == rep["complaint_code"] for n in notifs)


# ===========================================================================
# 5. PAGINATION AND CONSISTENT JSON VALIDATION / ERROR RESPONSES
# ===========================================================================

def test_pagination_on_endpoints(client, admin_headers):
    """Verify limit, offset, and total_count on paginated endpoints."""
    # 1. Electricity Series pagination
    elec_resp = client.get("/electricity/series?limit=5&offset=2", headers=admin_headers)
    assert elec_resp.status_code == 200
    elec_data = elec_resp.json()
    assert elec_data["limit"] == 5
    assert elec_data["offset"] == 2
    assert elec_data["count"] <= 5
    assert "total_count" in elec_data

    # 2. Complaints pagination
    comp_resp = client.get("/complaints?limit=2&offset=0", headers=admin_headers)
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["limit"] == 2
    assert comp_data["offset"] == 0
    assert len(comp_data["complaints"]) <= 2
    assert "total_count" in comp_data

    # 3. Actions pagination
    act_resp = client.get("/actions?limit=3&offset=0", headers=admin_headers)
    assert act_resp.status_code == 200
    act_data = act_resp.json()
    assert act_data["limit"] == 3
    assert act_data["offset"] == 0
    assert len(act_data["actions"]) <= 3
    assert "total_count" in act_data

    # 4. Savings Records pagination
    sav_resp = client.get("/savings/records?limit=3&offset=0", headers=admin_headers)
    assert sav_resp.status_code == 200
    sav_data = sav_resp.json()
    assert sav_data["limit"] == 3
    assert sav_data["offset"] == 0
    assert len(sav_data["records"]) <= 3
    assert "total_count" in sav_data


def test_consistent_json_errors_and_validation(client, admin_headers):
    """Endpoints return structured JSON error payloads with 'detail' on client and server errors."""
    # 404 Room not found
    r_404 = client.get("/rooms/99999", headers=admin_headers)
    assert r_404.status_code == 404
    assert "detail" in r_404.json()

    # 400 Bad Request on invalid action equipment
    bad_action = client.post(
        "/actions/switch-off",
        json={"room_id": 1, "equipment_id": 99999, "notes": "invalid"},
        headers=admin_headers,
    )
    assert bad_action.status_code in (400, 404)
    assert "detail" in bad_action.json()

    # 422 Unprocessable Entity on schema validation failure
    invalid_schema = client.post(
        "/timetable",
        json={"room_id": "not_an_int", "day_of_week": 99},
        headers=admin_headers,
    )
    assert invalid_schema.status_code == 422
    assert "detail" in invalid_schema.json()

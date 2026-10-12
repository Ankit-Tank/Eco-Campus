"""
GhostWatt — tests/test_complaints_and_reports.py
Test suite for student water complaints, lifecycle transitions, admin triage,
executive sustainability reports, CSV export, and role-based privacy restrictions.

SPEC §10, §12 & Prompt Requirements:
1. Student submits complaint (multipart, photo upload, validation, unique ID like WC-0001).
2. Student cannot read another student's complaint (403 Forbidden and filtered list).
3. Lifecycle transitions (submitted -> acknowledged -> assigned -> in_progress -> resolved -> reopened).
4. Invalid lifecycle transitions are rejected with 400 Bad Request.
5. Simple admin notification record created for new complaints.
6. Executive reports summary with top 3 rooms (explanations & recommendations), verified savings,
   water totals, tagged figures (simulated, calculated, verified), and student privacy restriction.
7. CSV export with data tags on every row.
8. Water alert status update (SUSPECTED -> CONFIRMED or FALSE_ALARM with inspection notes).
"""
import io
import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db import models
from app.db.database import get_session
from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "admin@ghostwatt.demo", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def student1_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username_or_email": "student@ghostwatt.demo", "password": "student123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def student2_headers(client):
    # Ensure second student account exists in test db
    with get_session() as db:
        user2 = db.query(models.User).filter(models.User.email == "student2@ghostwatt.demo").first()
        if not user2:
            user2 = models.User(
                username="student2",
                email="student2@ghostwatt.demo",
                password_hash=hash_password("student123"),
                role="student",
                is_active=True,
            )
            db.add(user2)
            db.commit()

    resp = client.post(
        "/auth/login",
        json={"username_or_email": "student2@ghostwatt.demo", "password": "student123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Complaint Submission & Validation
# ===========================================================================
def test_submit_complaint_and_validation(client, student1_headers):
    """Student submits a complaint with photo upload, validation, and notification creation."""
    # 1. File format validation rejection (.txt not allowed)
    fake_txt = io.BytesIO(b"Not an image")
    resp_bad = client.post(
        "/complaints",
        data={
            "building": "Block C",
            "location_detail": "1st Floor Restroom",
            "category": "leaking_tap",
            "description": "Continuous drip from faucet",
        },
        files={"photo": ("malicious.txt", fake_txt, "text/plain")},
        headers=student1_headers,
    )
    assert resp_bad.status_code == 400
    assert "Invalid file type" in resp_bad.json()["detail"]

    # 2. Valid image upload submission (.png)
    fake_img = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    resp_good = client.post(
        "/complaints",
        data={
            "building": "Block C",
            "location_detail": "1st Floor Restroom",
            "category": "leaking_tap",
            "description": "Faucet dripping heavily onto vanity",
        },
        files={"photo": ("leak.png", fake_img, "image/png")},
        headers=student1_headers,
    )
    assert resp_good.status_code == 201, f"Submission failed: {resp_good.text}"
    data = resp_good.json()
    assert data["complaint_code"].startswith("WC-")
    assert data["status"] == "submitted"
    assert data["building"] == "Block C"
    assert data["attachment_path"] is not None
    assert len(data["history"]) >= 1
    assert data["history"][0]["new_status"] == "submitted"
    assert data["data_source"] == "simulated"


# ===========================================================================
# 2. Privacy: Student Cannot Read Another Student's Complaint
# ===========================================================================
def test_student_cannot_read_another_students_complaint(client, student1_headers, student2_headers):
    """
    A student cannot read another student's complaint:
    - Direct GET /complaints/{id} returns HTTP 403 Forbidden.
    - List GET /complaints filters out other students' complaints.
    """
    # Student 1 creates a private complaint
    resp = client.post(
        "/complaints",
        data={
            "building": "Block A",
            "location_detail": "Ground Floor Water Cooler",
            "category": "low_pressure",
            "description": "Drinking water fountain barely trickles",
        },
        headers=student1_headers,
    )
    assert resp.status_code == 201
    s1_complaint_id = resp.json()["id"]

    # Student 2 attempts to read Student 1's complaint directly -> 403
    resp_forbidden = client.get(
        f"/complaints/{s1_complaint_id}",
        headers=student2_headers,
    )
    assert resp_forbidden.status_code == 403
    assert "Forbidden" in resp_forbidden.json()["detail"]

    # Student 2 lists complaints -> Student 1's complaint must NOT be present
    s2_list_resp = client.get("/complaints", headers=student2_headers)
    assert s2_list_resp.status_code == 200
    s2_complaint_ids = [c["id"] for c in s2_list_resp.json()["complaints"]]
    assert s1_complaint_id not in s2_complaint_ids


# ===========================================================================
# 3. Lifecycle Transitions (Valid)
# ===========================================================================
def test_complaint_lifecycle_valid_transitions(client, admin_headers, student1_headers):
    """
    Admin triages a complaint through valid lifecycle transitions:
    submitted -> acknowledged -> assigned -> in_progress -> resolved -> reopened.
    Every transition is logged in complaint_history.
    """
    # 1. Student submits complaint
    resp = client.post(
        "/complaints",
        data={
            "building": "Block B",
            "location_detail": "Physics Lab sink",
            "category": "broken_pipe",
            "description": "Pipe joint leaking under sink",
        },
        headers=student1_headers,
    )
    cid = resp.json()["id"]

    # 2. Admin acknowledges
    r_ack = client.patch(
        f"/complaints/{cid}",
        json={"status": "acknowledged", "notes": "Facilities supervisor reviewed"},
        headers=admin_headers,
    )
    assert r_ack.status_code == 200
    assert r_ack.json()["status"] == "acknowledged"

    # 3. Admin assigns to staff (admin user id 1)
    r_assign = client.patch(
        f"/complaints/{cid}",
        json={"status": "assigned", "assigned_to": 1, "notes": "Assigned to head plumber"},
        headers=admin_headers,
    )
    assert r_assign.status_code == 200
    assert r_assign.json()["status"] == "assigned"
    assert r_assign.json()["assigned_to"] == 1

    # 4. In Progress
    r_prog = client.patch(
        f"/complaints/{cid}",
        json={"status": "in_progress", "notes": "Plumbing crew on site replacing gasket"},
        headers=admin_headers,
    )
    assert r_prog.status_code == 200
    assert r_prog.json()["status"] == "in_progress"

    # 5. Resolved
    r_res = client.patch(
        f"/complaints/{cid}",
        json={
            "status": "resolved",
            "resolution_notes": "Replaced PVC compression coupling. Pressure tested OK.",
            "notes": "Work completed and inspected",
        },
        headers=admin_headers,
    )
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "resolved"
    assert "compression coupling" in r_res.json()["resolution_notes"]

    # 6. Reopened
    r_reopen = client.patch(
        f"/complaints/{cid}",
        json={"status": "reopened", "notes": "Student reported persistent seepage next morning"},
        headers=admin_headers,
    )
    assert r_reopen.status_code == 200
    assert r_reopen.json()["status"] == "reopened"

    # Verify history contains all transitions
    hist = r_reopen.json()["history"]
    statuses_logged = [h["new_status"] for h in hist]
    assert "submitted" in statuses_logged
    assert "acknowledged" in statuses_logged
    assert "assigned" in statuses_logged
    assert "in_progress" in statuses_logged
    assert "resolved" in statuses_logged
    assert "reopened" in statuses_logged


# ===========================================================================
# 4. Lifecycle Transitions (Invalid)
# ===========================================================================
def test_complaint_lifecycle_invalid_transition_fails(client, admin_headers, student1_headers):
    """Jumping from resolved to acknowledged directly without reopening must fail (400)."""
    resp = client.post(
        "/complaints",
        data={
            "building": "Block C",
            "location_detail": "Ground Floor",
            "category": "overflowing_tank",
            "description": "Overhead tank overflow float valve stuck",
        },
        headers=student1_headers,
    )
    cid = resp.json()["id"]

    # Directly resolve
    client.patch(f"/complaints/{cid}", json={"status": "resolved"}, headers=admin_headers)

    # Attempt illegal transition: resolved -> acknowledged
    bad_transition = client.patch(
        f"/complaints/{cid}",
        json={"status": "acknowledged"},
        headers=admin_headers,
    )
    assert bad_transition.status_code == 400
    assert "Invalid lifecycle transition" in bad_transition.json()["detail"]


# ===========================================================================
# 5. Admin Notifications
# ===========================================================================
def test_admin_notifications_logging(client, admin_headers):
    """Admin notification log records complaint events."""
    resp = client.get("/complaints/notifications/admin", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "notifications" in data
    assert data["count"] >= 1
    assert data["data_source"] == "simulated"


# ===========================================================================
# 6. Executive Reports Summary (Tags & Role Restrictions)
# ===========================================================================
def test_reports_summary_tagged_and_restricted(client, admin_headers, student1_headers):
    """
    Validate GET /reports/summary:
    - Figures tagged as simulated, calculated, or verified.
    - Top 3 rooms have explanations and recommended actions.
    - Students receive restricted version (no staff breakdowns).
    - Admins receive full campus breakdown.
    """
    # 1. Admin report view
    admin_rep = client.get("/reports/summary", headers=admin_headers)
    assert admin_rep.status_code == 200
    a_data = admin_rep.json()
    assert a_data["is_restricted"] is False
    assert a_data["actual_kwh"] > 0
    assert a_data["expected_kwh"] > 0
    assert a_data["ghost_kwh"] >= 0
    assert a_data["data_tags"]["actual_kwh"] == "simulated"
    assert a_data["data_tags"]["ghost_kwh"] == "calculated"
    assert a_data["data_tags"]["verified_savings"] == "verified"

    # Top 3 rooms
    assert len(a_data["top_ghost_rooms"]) <= 3
    for r in a_data["top_ghost_rooms"]:
        assert r["explanation"] != ""
        assert r["recommended_action"] != ""
        assert r["tag"] == "calculated"

    # Verified savings
    vs = a_data["verified_savings"]
    assert vs["tag"] == "verified"

    # Complaints (admin gets breakdown)
    c_admin = a_data["complaints"]
    assert c_admin["is_restricted"] is False
    assert c_admin["category_breakdown"] is not None

    # 2. Student report view (restricted)
    stud_rep = client.get("/reports/summary", headers=student1_headers)
    assert stud_rep.status_code == 200
    s_data = stud_rep.json()
    assert s_data["is_restricted"] is True
    c_stud = s_data["complaints"]
    assert c_stud["is_restricted"] is True
    assert c_stud["category_breakdown"] is None
    assert c_stud["own_complaints"] is not None


# ===========================================================================
# 7. CSV Export
# ===========================================================================
def test_reports_export_csv(client, admin_headers):
    """Downloadable CSV report contains data tags and structured sections."""
    resp = client.get("/reports/export.csv", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]

    csv_text = resp.text
    assert "Section,Metric,Value,Unit,Data Tag,Details / Notes" in csv_text
    assert "Executive Summary" in csv_text
    assert "Electricity" in csv_text
    assert "simulated" in csv_text
    assert "calculated" in csv_text
    assert "verified" in csv_text


# ===========================================================================
# 8. Water Alert Triaging (Admin PATCH)
# ===========================================================================
def test_water_alert_status_patch(client, admin_headers):
    """Admin updates water alert status from SUSPECTED to CONFIRMED with inspection notes."""
    # Find existing water alert
    alerts_resp = client.get("/water/alerts", headers=admin_headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()["alerts"]
    assert len(alerts) >= 1
    target_alert_id = alerts[0]["id"]

    # PATCH to CONFIRMED
    patch_resp = client.patch(
        f"/water/alerts/{target_alert_id}",
        json={
            "status": "CONFIRMED",
            "inspection_notes": "Facilities verified fractured pipe elbow under Block C main washroom riser.",
        },
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "CONFIRMED"
    assert "fractured pipe" in updated["inspection_notes"]
    assert updated["resolved_at"] is not None

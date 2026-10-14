"""
Eco-Campus - tests/test_audit_fixes.py
Regression tests for the security / integrity / integration fixes made during the full audit.
Each test documents a bug that existed before.
"""
import io
from datetime import datetime

import pytest

from app.core.phone import normalize_phone
from app.db import models
from app.db.database import SessionLocal
from app.services import otp_store
from app.services.rate_limit import SlidingWindowLimiter

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
ADMIN_PHONE = "9876500000"


def _login(client, who, pw):
    r = client.post("/auth/login", json={"username_or_email": who, "password": pw})
    return r


def _otp_login(client, phone):
    sent = client.post("/auth/student/otp/send", json={"phone": phone})
    assert sent.status_code == 200, sent.text
    r = client.post("/auth/student/otp/verify", json={"phone": phone, "otp": sent.json()["dev_otp"]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


@pytest.fixture(scope="module", autouse=True)
def _restore_sim_state():
    with SessionLocal() as db:
        st = db.query(models.SimState).filter(models.SimState.id == 1).first()
        saved = (st.virtual_now, st.speed, st.running)
    yield
    with SessionLocal() as db:
        st = db.query(models.SimState).filter(models.SimState.id == 1).first()
        st.virtual_now, st.speed, st.running = saved
        db.commit()


# ---------------------------------------------------------------- unit helpers
def test_normalize_phone_variants():
    assert normalize_phone("+919876543210") == "9876543210"
    assert normalize_phone("919876543210") == "9876543210"
    assert normalize_phone("09876543210") == "9876543210"
    assert normalize_phone("98765 43210") == "9876543210"
    for bad in ("12345", "5876543210", "", None, "abcdefghij"):
        with pytest.raises(ValueError):
            normalize_phone(bad)


def test_otp_store_rules():
    otp_store.reset_all()
    code, _ = otp_store.issue("t", "9000000001", demo_mode=True, now=1000.0)
    assert code == otp_store.DEMO_OTP
    with pytest.raises(otp_store.OtpError) as cooldown:
        otp_store.issue("t", "9000000001", demo_mode=True, now=1005.0)
    assert cooldown.value.code == "OTP_COOLDOWN"
    for _ in range(otp_store.MAX_ATTEMPTS):
        with pytest.raises(otp_store.OtpError):
            otp_store.verify("t", "9000000001", "000000", now=1010.0)
    with pytest.raises(otp_store.OtpError) as locked:
        otp_store.verify("t", "9000000001", otp_store.DEMO_OTP, now=1011.0)
    assert locked.value.code == "OTP_LOCKED"
    otp_store.issue("t", "9000000002", demo_mode=False, now=2000.0)
    with pytest.raises(otp_store.OtpError) as expired:
        otp_store.verify("t", "9000000002", "123456", now=2000.0 + otp_store.OTP_TTL_SECONDS + 1)
    assert expired.value.code in ("OTP_EXPIRED", "OTP_INVALID")


def test_rate_limiter_window():
    lim = SlidingWindowLimiter(max_events=2, window_seconds=10)
    assert lim.retry_after("k", now=0) == 0
    lim.record("k", now=0)
    lim.record("k", now=1)
    assert lim.retry_after("k", now=2) > 0
    assert lim.retry_after("k", now=20) == 0


# ---------------------------------------------------------------- authentication
def test_mock_tokens_are_rejected(client):
    for tok in ("mock-admin-token", "mock-student-token"):
        assert client.get("/sim/state", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_no_hardcoded_master_passwords(client):
    assert _login(client, "admin@ghostwatt.demo", "demo").status_code == 401
    assert _login(client, "admin@ecocampus.demo", "admin123").status_code == 401
    assert _login(client, "student@ghostwatt.demo", "admin123").status_code == 401
    assert client.post("/auth/admin/login", json={"email": "admin@ghostwatt.demo", "password": "demo"}).status_code == 401


def test_login_rate_limit(client):
    codes = [_login(client, "admin@ghostwatt.demo", "wrong-password").status_code for _ in range(9)]
    assert codes[:8] == [401] * 8
    assert codes[8] == 429
    # Even the right password is refused while locked out, then works for other accounts
    assert _login(client, "admin@ghostwatt.demo", "admin123").status_code == 429
    assert _login(client, "student@ghostwatt.demo", "student123").status_code == 200


def test_admin_login_requires_admin_role(client):
    r = client.post("/auth/admin/login", json={"email": "student@ghostwatt.demo", "password": "student123"})
    assert r.status_code == 403


def test_student_otp_creates_separate_accounts(client):
    h1, u1 = _otp_login(client, "+919111111111")
    h2, u2 = _otp_login(client, "9222222222")
    assert u1["id"] != u2["id"] and u1["role"] == u2["role"] == "student"
    # same number logs into the same account
    otp_store.reset_all()
    _, u1_again = _otp_login(client, "9111111111")
    assert u1_again["id"] == u1["id"]


def test_student_complaints_isolated_between_phone_accounts(client):
    h1, _ = _otp_login(client, "9333333331")
    h2, _ = _otp_login(client, "9333333332")
    c = client.post("/complaints", headers=h1, data={"category": "leaking_tap", "description": "tap dripping", "location": "Block A - Washroom"})
    assert c.status_code == 201
    cid = c.json()["id"]
    assert client.get("/complaints/mine", headers=h2).json()["count"] == 0
    assert client.get(f"/complaints/{cid}", headers=h2).status_code == 403
    assert client.get(f"/complaints/{cid}", headers=h1).status_code == 200


def test_student_otp_rejects_wrong_invalid_and_admin_numbers(client):
    assert client.post("/auth/student/otp/send", json={"phone": "123"}).status_code == 422
    client.post("/auth/student/otp/send", json={"phone": "9444444444"})
    assert client.post("/auth/student/otp/verify", json={"phone": "9444444444", "otp": "000000"}).status_code == 400
    # cooldown on rapid resend
    assert client.post("/auth/student/otp/send", json={"phone": "9444444444"}).status_code == 429
    # an admin's phone cannot be used for the student flow
    sent = client.post("/auth/student/otp/send", json={"phone": ADMIN_PHONE}).json()
    r = client.post("/auth/student/otp/verify", json={"phone": ADMIN_PHONE, "otp": sent["dev_otp"]})
    assert r.status_code == 403


def _reset_password(client, new_password):
    sent = client.post("/auth/admin/forgot-password/send-otp", json={"phone": ADMIN_PHONE})
    assert sent.status_code == 200
    ver = client.post("/auth/admin/forgot-password/verify-otp", json={"phone": ADMIN_PHONE, "otp": sent.json()["dev_otp"]})
    assert ver.status_code == 200, ver.text
    token = ver.json()["reset_token"]
    return token, client.post("/auth/admin/forgot-password/reset", json={"reset_token": token, "new_password": new_password})


def test_admin_password_reset_is_bound_and_single_use(client):
    # Unauthenticated attacker with the public demo OTP but WITHOUT the admin's phone is refused
    assert client.post("/auth/admin/forgot-password/verify-otp", json={"phone": "9555555555", "otp": "123456"}).status_code == 400
    assert client.post("/auth/admin/forgot-password/verify-otp", json={"phone": ADMIN_PHONE, "otp": "123456"}).status_code == 400  # no OTP requested yet

    token, done = _reset_password(client, "NewPass#2026")
    assert done.status_code == 200
    # a reset token is not a login session
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    # single use
    again = client.post("/auth/admin/forgot-password/reset", json={"reset_token": token, "new_password": "Another#2026"})
    assert again.status_code == 400
    # the new password works, the old one does not
    assert _login(client, "admin@ghostwatt.demo", "NewPass#2026").status_code == 200
    assert _login(client, "admin@ghostwatt.demo", "admin123").status_code == 401
    # restore the demo password for the rest of the suite
    otp_store.reset_all()
    _, restored = _reset_password(client, "admin123")
    assert restored.status_code == 200
    assert _login(client, "admin@ghostwatt.demo", "admin123").status_code == 200


def test_reset_rejects_short_password_and_garbage_token(client):
    assert client.post("/auth/admin/forgot-password/reset", json={"reset_token": "garbage", "new_password": "longenough1"}).status_code == 400
    assert client.post("/auth/admin/forgot-password/reset", json={"reset_token": "x", "new_password": "short"}).status_code == 422


# ---------------------------------------------------------------- complaints
@pytest.mark.parametrize(
    "category",
    ["leaking_tap", "broken_pipe", "overflowing_tank", "low_pressure", "water_wastage",
     "lights_left_on", "ac_running", "electrical_damage", "other"],
)
def test_every_category_offered_by_the_student_form_is_accepted(client, student_headers, category):
    r = client.post("/complaints", headers=student_headers,
                    data={"category": category, "title": "Issue", "description": "details here", "location": "Block B - Lab 2"})
    assert r.status_code == 201, r.text
    assert r.json()["category"] == ("general_wastage" if category == "water_wastage" else category)


def test_complaint_requires_location_and_text(client, student_headers):
    assert client.post("/complaints", headers=student_headers, data={"category": "leaking_tap", "description": "abc"}).status_code == 422
    assert client.post("/complaints", headers=student_headers, data={"category": "leaking_tap", "location": "Block A"}).status_code == 422
    assert client.post("/complaints", headers=student_headers, data={"category": "bogus", "description": "abc", "location": "x"}).status_code == 400


def test_photo_upload_is_sanitised(client, student_headers):
    r = client.post("/complaints", headers=student_headers,
                    data={"category": "leaking_tap", "description": "photo test", "location": "Block A"},
                    files={"photo": ("../../evil.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 201, r.text
    url = r.json()["image_url"]
    assert url.startswith("/uploads/complaints/") and ".." not in url and "evil" not in url
    assert client.get(url).status_code == 200
    # disguised non-image is refused, as is a bad extension
    fake = client.post("/complaints", headers=student_headers,
                       data={"category": "leaking_tap", "description": "photo test", "location": "Block A"},
                       files={"photo": ("x.png", io.BytesIO(b"<script>alert(1)</script>"), "image/png")})
    assert fake.status_code == 400
    exe = client.post("/complaints", headers=student_headers,
                      data={"category": "leaking_tap", "description": "photo test", "location": "Block A"},
                      files={"photo": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")})
    assert exe.status_code == 400


def test_assign_only_to_admin_staff_and_assignee_list(client, admin_headers, student_headers):
    cid = client.post("/complaints", headers=student_headers,
                      data={"category": "broken_pipe", "description": "pipe burst", "location": "Block C"}).json()["id"]
    student_id = client.get("/auth/me", headers=student_headers).json()["id"]
    assert client.patch(f"/complaints/{cid}", headers=admin_headers, json={"assigned_to": student_id}).status_code == 400
    people = client.get("/complaints/assignees", headers=admin_headers).json()["assignees"]
    assert people and all("id" in p and "email" in p for p in people)
    ok = client.patch(f"/complaints/{cid}", headers=admin_headers, json={"assigned_to": people[0]["id"], "status": "assigned"})
    assert ok.status_code == 200 and ok.json()["assigned_to"] == people[0]["id"]
    assert client.get("/complaints/assignees", headers=student_headers).status_code == 403


def test_reopen_flow_and_permissions(client, admin_headers, student_headers):
    cid = client.post("/complaints", headers=student_headers,
                      data={"category": "leaking_tap", "description": "again", "location": "Block A"}).json()["id"]
    assert client.post(f"/complaints/{cid}/reopen", headers=student_headers, json={}).status_code == 400  # not resolved yet
    assert client.patch(f"/complaints/{cid}", headers=admin_headers, json={"status": "resolved", "resolution_notes": "fixed"}).status_code == 200
    other, _ = _otp_login(client, "9666666666")
    assert client.post(f"/complaints/{cid}/reopen", headers=other, json={}).status_code == 403
    r = client.post(f"/complaints/{cid}/reopen", headers=student_headers, json={"reason": "Leaking again"})
    assert r.status_code == 200 and r.json()["status"] == "reopened"
    assert r.json()["history"][-1]["note"] == "Leaking again"


def test_admin_notifications_can_be_marked_read(client, admin_headers, student_headers):
    client.post("/complaints", headers=student_headers,
                data={"category": "leaking_tap", "description": "notif", "location": "Block A"})
    notes = client.get("/complaints/admin/notifications", headers=admin_headers).json()
    assert notes["unread_count"] > 0
    first = notes["notifications"][0]["id"]
    assert client.patch(f"/complaints/admin/notifications/{first}/read", headers=admin_headers).status_code == 200
    assert client.patch(f"/complaints/admin/notifications/{first}/read", headers=student_headers).status_code == 403
    assert client.post("/complaints/admin/notifications/read-all", headers=admin_headers).status_code == 200
    assert client.get("/complaints/admin/notifications", headers=admin_headers).json()["unread_count"] == 0
    assert client.patch("/complaints/admin/notifications/999999/read", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------- settings / validation
@pytest.mark.parametrize("key,val", [
    ("bucket_litres", "nan"), ("electricity_price_per_kwh", "inf"), ("emissions_factor_kg_per_kwh", "-1"),
    ("fan_watt_equivalent", "0"), ("electricity_price_per_kwh", "1e9"), ("bucket_litres", "abc"),
])
def test_settings_reject_non_finite_or_out_of_range(client, admin_headers, key, val):
    assert client.put("/settings", headers=admin_headers, json={"settings": {key: val}}).status_code == 422


def test_settings_accept_valid_values(client, admin_headers):
    cur = client.get("/settings", headers=admin_headers).json()["settings"]
    r = client.put("/settings", headers=admin_headers, json={"settings": {"bucket_litres": cur["bucket_litres"]}})
    assert r.status_code == 200


@pytest.mark.parametrize("url", [
    "/dashboard/summary?from=notadate", "/electricity/series?from=garbage", "/water/series?to=zzz",
    "/reports/summary?from=zzz", "/reports/export.csv?to=zzz", "/ghost/ranking?from=bad",
    "/ghost/room/1/explain?ts=bad", "/dashboard/summary?from=2026-10-10&to=2026-10-01",
    "/reports/summary?from=2026-10-10&to=2026-10-01", "/leaderboard/blocks?period=garbage",
    "/ghost/ranking?period=garbage",
])
def test_invalid_dates_and_periods_are_422(client, admin_headers, url):
    assert client.get(url, headers=admin_headers).status_code == 422


def test_water_bucket_equivalent_uses_setting(client, admin_headers):
    cur = client.get("/settings", headers=admin_headers).json()["settings"]
    client.put("/settings", headers=admin_headers, json={"settings": {"bucket_litres": "30"}})
    try:
        data = client.get("/water/series?limit=5", headers=admin_headers).json()
        assert "30" in str(data.get("bucket_assumption") or data)
    finally:
        client.put("/settings", headers=admin_headers, json={"settings": {"bucket_litres": cur["bucket_litres"]}})


# ---------------------------------------------------------------- simulator + savings
def _ac_equipment(client, admin_headers):
    rooms = client.get("/rooms", headers=admin_headers).json()["items"]
    room = next(r for r in rooms if r["room_code"] == "A-102")
    ac = next(e for e in room["equipment"] if e["kind"] == "ac")
    return room, ac


def test_sim_appliance_endpoint(client, admin_headers, student_headers):
    room, ac = _ac_equipment(client, admin_headers)
    assert client.post("/sim/appliance", headers=student_headers, json={"equipment_id": ac["id"], "state": "OFF"}).status_code == 403
    assert client.post("/sim/appliance", headers=admin_headers, json={"equipment_id": ac["id"], "state": "MAYBE"}).status_code == 422
    assert client.post("/sim/appliance", headers=admin_headers, json={"equipment_id": 999999, "state": "OFF"}).status_code == 404
    r = client.post("/sim/appliance", headers=admin_headers, json={"equipment_id": ac["id"], "state": "off"})
    assert r.status_code == 200 and r.json()["state"] == "OFF" and r.json()["room_code"] == "A-102"
    r = client.post("/sim/appliance", headers=admin_headers, json={"equipment_id": ac["id"], "state": "ON"})
    assert r.json()["state"] == "ON"


def test_sim_reset_accepts_timestamp_alias_and_validates(client, admin_headers):
    r = client.post("/sim/reset", headers=admin_headers, json={"timestamp": "2026-10-05T08:00:00"})
    assert r.status_code == 200 and r.json()["virtual_now"].startswith("2026-10-05T08:00")
    assert client.post("/sim/reset", headers=admin_headers, json={"timestamp": "nonsense"}).status_code == 422
    assert client.post("/sim/reset", headers=admin_headers, json={"to_date": "2026-10-05T09:00:00"}).json()["virtual_now"].startswith("2026-10-05T09:00")


def test_tick_never_creates_duplicate_readings_and_accepts_delta(client, admin_headers):
    client.post("/sim/reset", headers=admin_headers, json={"to_date": "2026-10-06T10:00:00"})
    before = client.get("/sim/state", headers=admin_headers).json()["virtual_now"]
    client.post("/sim/tick", headers=admin_headers, json={"delta_minutes": 30})
    after = client.get("/sim/state", headers=admin_headers).json()["virtual_now"]
    assert datetime.fromisoformat(after) - datetime.fromisoformat(before) == __import__("datetime").timedelta(minutes=30)
    # replay the same period twice
    client.post("/sim/reset", headers=admin_headers, json={"to_date": "2026-10-06T10:00:00"})
    client.post("/sim/tick", headers=admin_headers, json={"delta_minutes": 30})
    with SessionLocal() as db:
        dup = db.execute(__import__("sqlalchemy").text(
            "SELECT COUNT(*) FROM (SELECT room_id, timestamp FROM meter_readings GROUP BY 1,2 HAVING COUNT(*)>1)")).scalar()
        wdup = db.execute(__import__("sqlalchemy").text(
            "SELECT COUNT(*) FROM (SELECT location_id, timestamp FROM water_readings GROUP BY 1,2 HAVING COUNT(*)>1)")).scalar()
    assert dup == 0 and wdup == 0


def test_database_has_no_duplicate_readings_and_unique_indexes():
    with SessionLocal() as db:
        text = __import__("sqlalchemy").text
        assert db.execute(text("SELECT COUNT(*) FROM (SELECT 1 FROM meter_readings GROUP BY room_id, timestamp HAVING COUNT(*)>1)")).scalar() == 0
        idx = {r[1] for r in db.execute(text("PRAGMA index_list(meter_readings)")).fetchall()}
        assert "ux_meter_room_ts" in idx


def test_switching_off_twice_is_rejected(client, admin_headers):
    room, ac = _ac_equipment(client, admin_headers)
    body = {"room_id": room["id"], "equipment_id": ac["id"], "notes": "first"}
    assert client.post("/actions/switch-off", headers=admin_headers, json=body).status_code == 201
    second = client.post("/actions/switch-off", headers=admin_headers, json={**body, "notes": "again"})
    assert second.status_code == 409


# ---------------------------------------------------------------- dashboards are real, not fabricated
def test_admin_overview_is_calculated_from_data(client, admin_headers):
    client.post("/sim/reset", headers=admin_headers, json={"to_date": "2026-10-12T00:00:00"})
    ov = client.get("/dashboard/admin-overview?from=2026-10-01&to=2026-10-07", headers=admin_headers).json()
    assert len(ov["series"]) >= 7
    assert abs(ov["kpis"]["consumption_mwh"] * 1000 - ov["total_kwh"]) < 1.0
    assert abs(sum(b["share_pct"] for b in ov["blocks"]) - 100.0) < 0.5
    assert abs(sum(b["kwh"] for b in ov["blocks"]) - ov["total_kwh"]) < 1.0
    # zones are derived from the rooms table
    with SessionLocal() as db:
        blocks = {r.block.upper() for r in db.query(models.Room).filter(models.Room.is_active == True).all()}  # noqa: E712
    assert {z["key"] for z in ov["zones"]} == {f"academic_{b.lower()}" for b in blocks}
    one = client.get(f"/dashboard/admin-overview?zone={ov['zones'][0]['key']}", headers=admin_headers).json()
    assert len(one["blocks"]) == 1
    assert client.get("/dashboard/admin-overview?zone=nope", headers=admin_headers).status_code == 422


def test_admin_overview_for_a_period_with_no_data_is_zero_not_fabricated(client, admin_headers):
    client.post("/sim/reset", headers=admin_headers, json={"to_date": "2020-01-10T00:00:00"})
    ov = client.get("/dashboard/admin-overview", headers=admin_headers).json()
    assert ov["total_kwh"] == 0 and ov["kpis"]["consumption_mwh"] == 0
    assert all(p["actual_kw"] == 0 for p in ov["series"])
    assert ov["optimization_events"] == []


def test_new_student_home_is_all_zeros(client):
    h, user = _otp_login(client, "9777777777")
    home = client.get("/dashboard/student-home", headers=h).json()
    assert home["stats"] == {"reports_filed": 0, "accepted": 0, "in_progress": 0, "estimated_saving_kwh": 0.0}
    assert home["recent"] == [] and home["impact"] == {"electricity_kwh": 0.0, "water_litres": 0.0, "co2_kg": 0.0}
    assert home["name"] == user["name"]


def test_student_home_counts_and_image_urls(client):
    h, _ = _otp_login(client, "9888888888")
    client.post("/complaints", headers=h, data={"category": "leaking_tap", "description": "pic", "location": "Block A"},
                files={"photo": ("a.png", io.BytesIO(PNG), "image/png")})
    home = client.get("/dashboard/student-home", headers=h).json()
    assert home["stats"]["reports_filed"] == 1 and home["stats"]["accepted"] == 0
    url = home["recent"][0]["image_url"]
    assert url.startswith("/uploads/complaints/") and url.count("/uploads/") == 1
    assert client.get(url).status_code == 200


def test_public_impact_matches_database(client):
    data = client.get("/dashboard/public-impact").json()
    cards = {c["key"]: c for c in data["cards"]}
    with SessionLocal() as db:
        total = sum(s.credited_kwh for s in db.query(models.SavingsRecord).all())
    assert abs(cards["electricity"]["value"] - round(total, 1)) < 0.11
    assert "waste" not in cards  # nothing in the system measures waste diverted
    assert all(c["change_pct"] is None for c in data["cards"])


def test_leaderboard_period_changes_window(client, student_headers):
    day = client.get("/leaderboard/blocks?period=today", headers=student_headers).json()
    month = client.get("/leaderboard/blocks?period=30d", headers=student_headers).json()
    assert month["total_ghost_kwh"] >= day["total_ghost_kwh"]
    assert client.get("/ghost/ranking?period=week", headers=student_headers).status_code == 200


def test_cors_and_security_headers(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert r.headers.get("x-content-type-options") == "nosniff"
    evil = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


# ---------------------------------------------------------------- rooms / timetable validation
@pytest.mark.parametrize("start,end", [("25:99", "26:00"), ("09:60", "10:00"), ("10:00", "24:00"), ("12:00", "10:00"), ("9:00", "10:00")])
def test_timetable_rejects_invalid_clock_times(client, admin_headers, start, end):
    r = client.post("/timetable", headers=admin_headers,
                    json={"room_id": 1, "day_of_week": 1, "start_time": start, "end_time": end, "activity": "x", "expected_students": 5})
    assert r.status_code == 422


def test_timetable_update_rejects_invalid_clock_time(client, admin_headers):
    created = client.post("/timetable", headers=admin_headers,
                          json={"room_id": 1, "day_of_week": 6, "start_time": "21:00", "end_time": "22:00", "activity": "late", "expected_students": 5})
    assert created.status_code == 201
    eid = created.json()["id"]
    assert client.put(f"/timetable/{eid}", headers=admin_headers, json={"start_time": "99:99"}).status_code == 422
    assert client.delete(f"/timetable/{eid}", headers=admin_headers).status_code == 204


def test_room_with_history_cannot_be_deleted_but_empty_room_can(client, admin_headers):
    assert client.delete("/rooms/1", headers=admin_headers).status_code == 409
    new = client.post("/rooms", headers=admin_headers,
                      json={"room_code": "Z-901", "block": "z", "name": "Temp Room", "room_type": "classroom", "capacity": 10, "idle_baseline_kw": 0.1})
    assert new.status_code == 201 and new.json()["block"] == "Z"
    assert client.delete(f"/rooms/{new.json()['id']}", headers=admin_headers).status_code == 204


def test_new_block_appears_in_leaderboard_without_error(client, admin_headers, student_headers):
    new = client.post("/rooms", headers=admin_headers,
                      json={"room_code": "D-101", "block": "D", "name": "New Block Room", "room_type": "classroom", "capacity": 20, "idle_baseline_kw": 0.1})
    assert new.status_code == 201
    assert client.get("/leaderboard/blocks", headers=student_headers).status_code == 200
    assert client.get("/live/snapshot", headers=student_headers).status_code == 200
    assert client.get("/ghost/current", headers=student_headers).status_code == 200
    assert client.delete(f"/rooms/{new.json()['id']}", headers=admin_headers).status_code == 204


# ---------------------------------------------------------------- water thresholds are configurable
def test_night_flow_detection_honours_threshold_and_default_baseline():
    from datetime import datetime as dt
    from app.services.water_analysis import analyze_night_flow

    rows = [{"location_id": 1, "timestamp": dt(2026, 10, 1, h), "flow_rate_lph": 70.0, "interval_litres": 70.0, "expected_baseline_lph": None}
            for h in (1, 2, 3)]
    # 70 L/h against a 100 L/h threshold and a 40 L/h fallback baseline (x2 = 80): not anomalous
    assert analyze_night_flow(rows, threshold_lph=100.0, default_baseline_lph=40.0) == []
    # lowering the threshold to 50 L/h flags it, using the fallback baseline for the excess
    alerts = analyze_night_flow(rows, threshold_lph=50.0, default_baseline_lph=40.0)
    assert len(alerts) == 1 and alerts[0]["baseline_lph"] == 40.0 and alerts[0]["excess_litres"] == 90.0


def test_date_only_to_includes_the_whole_last_day(client, admin_headers):
    one_day = client.get("/electricity/series?from=2026-10-05&to=2026-10-05&limit=5000", headers=admin_headers).json()
    stamps = [r["timestamp"] for r in one_day["series"]]
    assert stamps, "readings for a date-only range must not be empty"
    assert any(s.startswith("2026-10-05T23") for s in stamps), "the last quarter-hours of the day must be included"
    assert all(s.startswith("2026-10-05") for s in stamps)


def test_title_and_description_are_both_kept(client, student_headers):
    r = client.post("/complaints", headers=student_headers,
                    data={"category": "leaking_tap", "title": "Tap dripping", "description": "Water drips all night near the sink", "location": "Block A - Washroom"})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Tap dripping"
    assert "Water drips all night near the sink" in body["description"]
    home = client.get("/dashboard/student-home", headers=student_headers).json()
    assert any(item["title"] == "Tap dripping" for item in home["recent"])

"""
Eco-Campus — tests/test_assistant.py
Comprehensive test suite for the AI Sustainability Assistant (POST /assistant/ask).

SPEC §11 & User Requirements:
1. Six example questions from the spec:
   - top_ghost_rooms ("Which rooms have the highest ghost load?")
   - explain_room_alert ("Why is room A-101 alerting?")
   - verified_savings ("How much energy have we saved through verified actions?")
   - block_wastage ("Which block wastes the most electricity?")
   - open_complaints ("What are the open water complaints?")
   - recommended_actions ("What recommended actions should we take to reduce energy waste?")
2. Fallback with the API key removed (returns source: "fallback" and template answer).
3. Fallback with an invalid API key.
4. Student asking for another student's complaint is refused.
5. Unsupported question returns friendly listing of supported questions.
6. Number guard tests: strictly validates that numbers in answer originate in tool output.
7. Unauthenticated request returns 401 Unauthorized.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.db import models
from app.db.database import get_session
from app.main import app
from app.services.groq_assistant import extract_numbers_from_obj, validate_number_guard


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
    # Ensure a second student exists
    with get_session() as db:
        u2 = db.query(models.User).filter(models.User.email == "student2@ghostwatt.demo").first()
        if not u2:
            u2 = models.User(
                email="student2@ghostwatt.demo",
                password_hash=hash_password("student123"),
                full_name="Second Student",
                role="student",
                is_active=True,
            )
            db.add(u2)
            db.commit()

    resp = client.post(
        "/auth/login",
        json={"username_or_email": "student2@ghostwatt.demo", "password": "student123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Unauthenticated Request
# ---------------------------------------------------------------------------
def test_assistant_requires_auth(client):
    resp = client.post("/assistant/ask", json={"question": "Which rooms have the highest ghost load?"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Six Example Questions from the Spec
# ---------------------------------------------------------------------------
def test_assistant_question_1_top_ghost_rooms(client, admin_headers):
    """Q1: Which rooms have the highest ghost load?"""
    resp = client.post(
        "/assistant/ask",
        json={"question": "Which rooms have the highest ghost load?"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert data["source"] in ("groq", "fallback")
    assert data["data_source"] == "simulated"
    assert "data_used" in data
    assert "top_rooms" in data["data_used"]


def test_assistant_question_2_explain_room_alert(client, admin_headers):
    """Q2: Why is room A-101 alerting?"""
    resp = client.post(
        "/assistant/ask",
        json={"question": "Why is room A-101 alerting?"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert data["source"] in ("groq", "fallback")
    assert "data_used" in data
    assert data["data_used"].get("room_code") == "A-101"
    assert "status" in data["data_used"]


def test_assistant_question_3_verified_savings(client, admin_headers):
    """Q3: How much energy have we saved through verified actions?"""
    resp = client.post(
        "/assistant/ask",
        json={"question": "How much energy have we saved through verified actions?"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert data["source"] in ("groq", "fallback")
    assert "data_used" in data
    assert "verified_kwh" in data["data_used"]
    assert "monetary_saving_inr" in data["data_used"]


def test_assistant_question_4_block_wastage(client, admin_headers):
    """Q4: Which block wastes the most electricity?"""
    resp = client.post(
        "/assistant/ask",
        json={"question": "Which block wastes the most electricity?"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert data["source"] in ("groq", "fallback")
    assert "data_used" in data
    assert "highest_waste_block" in data["data_used"]
    assert "blocks" in data["data_used"]


def test_assistant_question_5_open_complaints(client, admin_headers):
    """Q5: What are the open water complaints?"""
    resp = client.post(
        "/assistant/ask",
        json={"question": "What are the open water complaints?"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["source"] in ("groq", "fallback")
    assert "data_used" in data
    assert "complaints" in data["data_used"]
    assert "count" in data["data_used"]


def test_assistant_question_6_recommended_actions(client, admin_headers):
    """Q6: What recommended actions should we take to reduce energy waste?"""
    resp = client.post(
        "/assistant/ask",
        json={"question": "What recommended actions should we take to reduce energy waste?"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert data["source"] in ("groq", "fallback")
    assert "data_used" in data
    assert "recommendations" in data["data_used"]


# ---------------------------------------------------------------------------
# 3. Fallback when API Key is Removed
# ---------------------------------------------------------------------------
def test_assistant_fallback_when_key_removed(client, student1_headers, monkeypatch):
    """When GROQ_API_KEY is unset, assistant uses deterministic template fallback."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(settings, "groq_api_key", "")

    resp = client.post(
        "/assistant/ask",
        json={"question": "Which rooms have the highest ghost load?"},
        headers=student1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "fallback"
    assert "top_rooms" in data["data_used"]
    assert "Top rooms with the highest ghost load" in data["answer"]


def test_assistant_fallback_with_invalid_key(client, student1_headers, monkeypatch):
    """When GROQ_API_KEY is invalid, assistant catches error and returns fallback."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_invalid_test_key_12345")
    monkeypatch.setattr(settings, "groq_api_key", "gsk_invalid_test_key_12345")

    resp = client.post(
        "/assistant/ask",
        json={"question": "Which block wastes the most electricity?"},
        headers=student1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "fallback"
    assert "highest_waste_block" in data["data_used"]
    assert "Highest electricity wastage is in" in data["answer"]


# ---------------------------------------------------------------------------
# 4. Student Refusal When Querying Another Student's Complaint
# ---------------------------------------------------------------------------
def test_student_cannot_query_another_students_complaint(client, student1_headers):
    """Student requesting another student's complaint receives explicit refusal."""
    resp = client.post(
        "/assistant/ask",
        json={"question": "What complaints were filed by student2@ghostwatt.demo?"},
        headers=student1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Refusal should be in answer
    assert "Access denied" in data["answer"] or "refusal" in str(data["data_used"])
    assert data["data_used"].get("refusal") == "Access denied: Students are only permitted to view their own complaints."


def test_student_cannot_query_other_students_complaints_generic(client, student1_headers):
    """Student asking generally for other students' complaints is refused."""
    resp = client.post(
        "/assistant/ask",
        json={"question": "Can I see complaints filed by other students?"},
        headers=student1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Access denied" in data["answer"] or "refusal" in str(data["data_used"])


# ---------------------------------------------------------------------------
# 5. Unsupported Question Fallback
# ---------------------------------------------------------------------------
def test_assistant_unsupported_question_listing(client, student1_headers, monkeypatch):
    """Unrelated questions trigger a friendly message listing supported questions."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(settings, "groq_api_key", "")

    resp = client.post(
        "/assistant/ask",
        json={"question": "What is the capital of Australia?"},
        headers=student1_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "fallback"
    assert "I can answer questions regarding campus electricity waste" in data["answer"]
    assert "Which rooms have the highest ghost load?" in data["answer"]


# ---------------------------------------------------------------------------
# 6. Number Guard Unit Verification
# ---------------------------------------------------------------------------
def test_number_guard_accepts_valid_numbers():
    tool_data = {
        "period": "7d",
        "top_rooms": [
            {"rank": 1, "room_code": "A-101", "name": "Classroom 101", "ghost_kwh": 45.2, "cost_inr": 384.2},
            {"rank": 2, "room_code": "B-201", "name": "Lab 1", "ghost_kwh": 30.1, "cost_inr": 255.85},
        ],
        "total_ghost_kwh": 128.5,
    }

    # All numbers (1, 101, 45.2, 384.2) exist in tool_data
    valid_text = "Classroom A-101 is ranked 1 with 45.2 kWh of ghost load costing 384.2 INR."
    assert validate_number_guard(valid_text, tool_data) is True


def test_number_guard_rejects_hallucinated_numbers():
    tool_data = {
        "room_code": "A-101",
        "actual_kw": 4.5,
        "expected_kw": 0.8,
        "ghost_kw": 3.7,
    }

    # Hallucinated 99.9 does NOT exist in tool_data
    hallucinated_text = "Room A-101 is using 99.9 kW excess power above normal."
    assert validate_number_guard(hallucinated_text, tool_data) is False


def test_extract_numbers_from_nested_structures():
    sample = {
        "room": "C-301",
        "metrics": [12.5, 34],
        "nested": {"savings": "₹1,250.75", "code": "WC-0005"},
    }
    nums = extract_numbers_from_obj(sample)
    assert 301.0 in nums
    assert 12.5 in nums
    assert 34.0 in nums
    assert 1250.75 in nums
    assert 5.0 in nums

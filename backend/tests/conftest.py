"""
GhostWatt — tests/conftest.py
Shared pytest fixtures for the test suite.
"""
import importlib

try:
    pytest = importlib.import_module("pytest")
except Exception:
    class _DummyPytest:  # type: ignore
        @staticmethod
        def fixture(*args, **kwargs):
            return lambda fn: fn
    pytest = _DummyPytest()
from fastapi.testclient import TestClient
from app.main import app


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

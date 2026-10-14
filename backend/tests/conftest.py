"""
GhostWatt - tests/conftest.py
Shared pytest fixtures.

The suite runs against a THROWAWAY COPY of backend/ghostwatt.db (or a freshly seeded database when
that file does not exist), so tests can create complaints / actions / settings without touching the
real demo database. The environment is configured BEFORE the app is imported.
"""
import importlib
import os
import shutil
import tempfile
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_TMP = Path(tempfile.mkdtemp(prefix="ghostwatt_tests_"))
_TEST_DB = _TMP / "test.db"
_SOURCE_DB = _BACKEND / "ghostwatt.db"

os.environ["DB_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["JWT_SECRET"] = "test-only-secret-not-for-production-0123456789"
os.environ["DEMO_MODE"] = "true"
os.environ["GROQ_API_KEY"] = ""  # tests must never call the real Groq API

_seed_needed = not _SOURCE_DB.exists()
if not _seed_needed:
    shutil.copy(_SOURCE_DB, _TEST_DB)

try:
    pytest = importlib.import_module("pytest")
except Exception:  # pragma: no cover
    class _DummyPytest:  # type: ignore
        @staticmethod
        def fixture(*args, **kwargs):
            return lambda fn: fn
    pytest = _DummyPytest()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

from app.db.database import SessionLocal, create_all_tables  # noqa: E402

# TestClient(app) without a `with` block does not run the app lifespan, so apply the
# schema creation / migrations explicitly (this is what the lifespan does at startup).
create_all_tables()
if _seed_needed:
    from app.services.data_generator import generate_all  # noqa: E402

    with SessionLocal() as _db:
        generate_all(_db, seed=42, reset=True)


@pytest.fixture(autouse=True)
def _reset_limiters():
    """Rate limiters / OTP state are process-wide; keep tests independent of each other."""
    from app.routes import auth as auth_routes
    from app.services import otp_store

    from app.services.simulator import clear_appliance_states

    auth_routes.login_limiter.reset_all()
    auth_routes.otp_verify_limiter.reset_all()
    otp_store.reset_all()
    clear_appliance_states()  # interactive appliance overrides are process-wide state
    yield


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

"""
GhostWatt - services/otp_store.py
Small in-memory one-time-password store (pure Python, no FastAPI imports).

- Codes expire after OTP_TTL_SECONDS and allow MAX_ATTEMPTS wrong guesses.
- A new code cannot be requested before RESEND_AFTER_SECONDS have passed.
- In demo mode the code is the fixed demo value so the hackathon flow works without SMS.
  Outside demo mode the code is random; no SMS provider is wired in yet, so it is only
  written to the server log (see README: "Future integrations").
"""
import logging
import secrets
import threading
import time
from typing import Dict, Optional, Tuple

DEMO_OTP = "123456"
OTP_TTL_SECONDS = 300
RESEND_AFTER_SECONDS = 30
MAX_ATTEMPTS = 5

_log = logging.getLogger("ghostwatt.otp")
_lock = threading.Lock()
_codes: Dict[str, Dict[str, float]] = {}


class OtpError(Exception):
    """Raised for cooldown / expired / too-many-attempts problems. .code is a short machine code."""

    def __init__(self, code: str, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry_after = retry_after


def _key(purpose: str, phone: str) -> str:
    return f"{purpose}:{phone}"


def issue(purpose: str, phone: str, demo_mode: bool, now: Optional[float] = None) -> Tuple[str, int]:
    """Create (or refuse to re-create too quickly) an OTP. Returns (code, resend_after_seconds)."""
    now = time.time() if now is None else now
    k = _key(purpose, phone)
    with _lock:
        existing = _codes.get(k)
        if existing and now - existing["issued_at"] < RESEND_AFTER_SECONDS:
            wait = int(RESEND_AFTER_SECONDS - (now - existing["issued_at"])) + 1
            raise OtpError("OTP_COOLDOWN", f"Please wait {wait}s before requesting another code.", wait)
        code = DEMO_OTP if demo_mode else f"{secrets.randbelow(10**6):06d}"
        _codes[k] = {"code": code, "issued_at": now, "attempts": 0}
    if not demo_mode:
        _log.warning("OTP for %s (%s): %s  [no SMS provider configured]", phone[-4:].rjust(10, "*"), purpose, code)
    return code, RESEND_AFTER_SECONDS


def verify(purpose: str, phone: str, code: str, now: Optional[float] = None) -> None:
    """Consume the OTP on success. Raises OtpError on every failure."""
    now = time.time() if now is None else now
    k = _key(purpose, phone)
    with _lock:
        entry = _codes.get(k)
        if entry is None:
            raise OtpError("OTP_INVALID", "Invalid or expired code. Request a new one.")
        if now - entry["issued_at"] > OTP_TTL_SECONDS:
            _codes.pop(k, None)
            raise OtpError("OTP_EXPIRED", "This code has expired. Request a new one.")
        if entry["attempts"] >= MAX_ATTEMPTS:
            _codes.pop(k, None)
            raise OtpError("OTP_LOCKED", "Too many wrong attempts. Request a new code.")
        if not secrets.compare_digest(str(code).strip(), str(entry["code"])):
            entry["attempts"] += 1
            raise OtpError("OTP_INVALID", "Invalid code. Please check and try again.")
        _codes.pop(k, None)


def reset_all() -> None:
    """Test helper."""
    with _lock:
        _codes.clear()

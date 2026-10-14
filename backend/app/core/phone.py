"""Eco-Campus - core/phone.py: Indian mobile number normalisation (pure functions)."""
import re
from typing import Optional

_PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_phone(raw: Optional[str]) -> str:
    """
    Accepts "+919876543210", "919876543210", "09876543210" or "9876543210" and returns the
    10-digit national number. Raises ValueError when it is not a valid Indian mobile number.
    """
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not _PHONE_RE.match(digits):
        raise ValueError("Enter a valid 10-digit Indian mobile number.")
    return digits

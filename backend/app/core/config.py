"""
Eco-Campus - app/core/config.py
Reads configuration from environment variables / backend/.env.
Never hardcode prices or factors - runtime values live in the settings DB table.
"""
import logging
import secrets
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (two levels above this file). Paths are resolved against it so the
# app behaves the same no matter which folder uvicorn / pytest is started from.
BASE_DIR = Path(__file__).resolve().parents[2]

_PLACEHOLDER_SECRETS = {"", "change_this_to_a_long_random_secret", "super_secret_jwt_key_change_in_production"}
_log = logging.getLogger("eco_campus.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Eco-Campus"
    app_version: str = "0.2.0"
    debug: bool = False

    # Demo mode: fixed demo OTP (123456) is accepted and shown to the UI. Set DEMO_MODE=false
    # for anything that is not a hackathon demo (OTP is then random and only printed to the
    # server log until a real SMS provider is integrated).
    demo_mode: bool = True

    # Database
    db_url: str = "sqlite:///./eco-campus.db"

    # JWT
    jwt_secret: str = "change_this_to_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # CORS: comma separated list of allowed browser origins
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )

    # Uploads
    upload_dir: str = ""

    # Groq
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"  # any Groq model id with tool calling; see console.groq.com/docs/models

    # Default calculation factors (overridden by DB settings table at runtime)
    default_electricity_price_per_kwh: float = 8.50  # INR
    default_emissions_factor_kg_per_kwh: float = 0.71
    default_fan_watt_equivalent: float = 75.0
    default_bucket_litres: float = 15.0
    default_low_flow_threshold_lph: float = 50.0

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_db_url(self) -> str:
        """Resolve relative sqlite paths against backend/ instead of the current directory."""
        url = self.db_url
        prefix = "sqlite:///"
        if url.startswith(prefix) and not url.startswith("sqlite:////") and ":memory:" not in url:
            rel = url[len(prefix):]
            if not Path(rel).is_absolute():
                return prefix + str((BASE_DIR / rel).resolve())
        return url

    @property
    def uploads_path(self) -> Path:
        return Path(self.upload_dir).resolve() if self.upload_dir else (BASE_DIR / "uploads")


settings = Settings()

# Never run with a well-known signing key. If .env did not provide a real secret, use a random
# one for this process (logins simply expire when the server restarts) and say so loudly.
if settings.jwt_secret in _PLACEHOLDER_SECRETS:
    settings.jwt_secret = secrets.token_urlsafe(48)
    _log.warning(
        "JWT_SECRET is not configured - using a random per-process secret. "
        "Set JWT_SECRET in backend/.env to keep logins valid across restarts."
    )

"""
GhostWatt — app/core/config.py
Reads configuration from environment variables / .env file.
Never hardcode prices or factors — always read from settings DB or here.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "GhostWatt"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    db_url: str = "sqlite:///./ghostwatt.db"

    # JWT
    jwt_secret: str = "change_this_to_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Groq
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"

    # Default calculation factors (overridden by DB settings table at runtime)
    default_electricity_price_per_kwh: float = 8.50  # INR
    default_emissions_factor_kg_per_kwh: float = 0.71
    default_fan_watt_equivalent: float = 75.0
    default_bucket_litres: float = 15.0
    default_low_flow_threshold_lph: float = 50.0


settings = Settings()

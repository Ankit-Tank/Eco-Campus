"""
GhostWatt — services/water_analysis.py
Pure functions for night-flow leak detection.
SPEC §9: Compare 1 AM–4 AM flow vs configurable low-flow baseline.
NO FastAPI imports.
"""
from datetime import datetime
from typing import List
from app.db import models


LEAK_HOURS = {1, 2, 3}  # 1 AM, 2 AM, 3 AM


def is_leak_hour(ts: datetime) -> bool:
    return ts.hour in LEAK_HOURS


def detect_possible_leak(
    reading: models.WaterReading,
    threshold_multiplier: float = 2.0,
) -> bool:
    """
    Flag a reading as a possible leak if flow exceeds baseline by multiplier
    during defined low-flow hours.
    """
    if not is_leak_hour(reading.timestamp):
        return False
    return reading.flow_rate_lph > reading.expected_baseline_lph * threshold_multiplier


def summarise_water_period(readings: List[models.WaterReading], bucket_litres: float = 15.0) -> dict:
    """Aggregate water readings into a summary dict."""
    if not readings:
        return {"total_litres": 0, "avg_flow_lph": 0, "leak_alerts": 0, "bucket_equivalents": 0}

    total = sum(r.interval_litres for r in readings)
    avg_flow = sum(r.flow_rate_lph for r in readings) / len(readings)
    leak_alerts = sum(1 for r in readings if detect_possible_leak(r))

    return {
        "total_litres": round(total, 1),
        "avg_flow_lph": round(avg_flow, 1),
        "leak_alerts": leak_alerts,
        "bucket_equivalents": round(total / bucket_litres, 1) if bucket_litres else 0,
    }

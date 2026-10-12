"""
GhostWatt — services/savings_verification.py
Pure functions for the Verified Savings Meter.
SPEC §8: Verified Power Reduction = max(0, pre_avg - post_avg)
         Verified Energy Saving (kWh) = reduction * 0.25
NO FastAPI imports.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import models


def get_window_average_kw(room_id: int, start: datetime, end: datetime, db: Session) -> float:
    """Return mean actual_demand_kw for a room over [start, end)."""
    readings = (
        db.query(models.MeterReading)
        .filter(
            models.MeterReading.room_id == room_id,
            models.MeterReading.timestamp >= start,
            models.MeterReading.timestamp < end,
        )
        .all()
    )
    if not readings:
        return 0.0
    return sum(r.actual_demand_kw for r in readings) / len(readings)


def verify_action(
    action: models.Action,
    price_per_kwh: float,
    emissions_factor: float,
    db: Session,
    window_minutes: int = 15,
) -> dict:
    """
    Compare pre-action and post-action average demand for the given action.
    Returns a dict ready to persist as a SavingsRecord.
    """
    ts = action.timestamp
    pre_start = ts - timedelta(minutes=window_minutes)
    post_end = ts + timedelta(minutes=window_minutes)

    pre_avg = get_window_average_kw(action.room_id, pre_start, ts, db)
    post_avg = get_window_average_kw(action.room_id, ts, post_end, db)

    reduction_kw = max(0.0, pre_avg - post_avg)
    credited_kwh = reduction_kw * (window_minutes / 60)
    monetary = credited_kwh * price_per_kwh
    emissions = credited_kwh * emissions_factor
    status = "verified" if reduction_kw > 0 else "no_reduction"

    return {
        "action_id": action.id,
        "pre_avg_kw": round(pre_avg, 3),
        "post_avg_kw": round(post_avg, 3),
        "reduction_kw": round(reduction_kw, 3),
        "credited_kwh": round(credited_kwh, 4),
        "monetary_saving_inr": round(monetary, 2),
        "emissions_kg": round(emissions, 4),
        "verification_status": status,
        "is_simulated": True,
    }

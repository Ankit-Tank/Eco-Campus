"""
GhostWatt — routes/dashboard.py
High-level campus summary metrics: actual vs expected electricity, ghost load,
water consumption, emissions, and human-readable equivalents.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.expected_demand import expected_kw
from app.services.carbon_calculator import fan_equivalents, bucket_equivalents

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get campus-wide energy and sustainability summary")
def get_dashboard_summary(
    date_from: Optional[str] = Query(None, alias="from", description="Start datetime (ISO format)"),
    date_to: Optional[str] = Query(None, alias="to", description="End datetime (ISO format)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns aggregated electricity consumption, expected demand, ghost waste,
    water usage, monetary loss, carbon footprint, and human-readable equivalents.
    """
    # 1. Fetch system settings
    settings_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in settings_rows}
    price_per_kwh = float(cfg.get("electricity_price_per_kwh", 8.50))
    emissions_factor = float(cfg.get("emissions_factor_kg_per_kwh", 0.71))
    fan_watts = float(cfg.get("fan_watt_equivalent", 75.0))
    bucket_litres = float(cfg.get("bucket_litres", 15.0))

    # 2. Query meter readings with optional date range filter
    readings_query = db.query(models.MeterReading)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            readings_query = readings_query.filter(models.MeterReading.timestamp >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            readings_query = readings_query.filter(models.MeterReading.timestamp <= dt_to)
        except ValueError:
            pass

    meter_readings = readings_query.all()

    # Pre-index rooms, equipment, and timetables to compute expected demand efficiently
    rooms = db.query(models.Room).all()
    room_map = {r.id: r for r in rooms}
    equipment = db.query(models.Equipment).all()
    eq_by_room = {}
    for eq in equipment:
        eq_by_room.setdefault(eq.room_id, []).append(eq)
    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in timetables:
        tt_by_room.setdefault(t.room_id, []).append(t)

    # Weekly slot cache for expected kW: (room_id, weekday, time_str) -> expected_kw
    expected_cache = {}

    total_actual_kwh = 0.0
    total_expected_kwh = 0.0
    total_ghost_kwh = 0.0
    latest_ts = None
    earliest_ts = None

    for mr in meter_readings:
        total_actual_kwh += mr.interval_kwh
        if earliest_ts is None or mr.timestamp < earliest_ts:
            earliest_ts = mr.timestamp
        if latest_ts is None or mr.timestamp > latest_ts:
            latest_ts = mr.timestamp

        slot_key = (mr.room_id, mr.timestamp.weekday(), mr.timestamp.strftime("%H:%M"))
        if slot_key not in expected_cache:
            r = room_map.get(mr.room_id)
            r_eq = eq_by_room.get(mr.room_id, [])
            r_tt = tt_by_room.get(mr.room_id, [])
            if r:
                exp_kw, _ = expected_kw(r, r_eq, r_tt, mr.timestamp)
            else:
                exp_kw = 0.1
            expected_cache[slot_key] = exp_kw

        exp_kw = expected_cache[slot_key]
        exp_kwh = exp_kw * 0.25
        total_expected_kwh += exp_kwh

        ghost_interval_kwh = max(0.0, mr.interval_kwh - exp_kwh)
        total_ghost_kwh += ghost_interval_kwh

    # 3. Water readings
    water_query = db.query(models.WaterReading)
    if date_from:
        try:
            water_query = water_query.filter(models.WaterReading.timestamp >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            water_query = water_query.filter(models.WaterReading.timestamp <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    water_readings = water_query.all()
    total_water_litres = sum(wr.interval_litres for wr in water_readings)

    # 4. Computed metrics
    cost_inr = round(total_ghost_kwh * price_per_kwh, 2)
    emissions_kg = round(total_ghost_kwh * emissions_factor, 3)

    # Average ghost kW over the duration for instantaneous fan equivalent
    duration_hours = max(1.0, (len(meter_readings) / max(1, len(rooms))) * 0.25)
    avg_ghost_kw = total_ghost_kwh / duration_hours if duration_hours > 0 else 0.0
    fan_eq = fan_equivalents(avg_ghost_kw, fan_watts)["value"]
    bucket_eq = bucket_equivalents(total_water_litres, bucket_litres)["value"]

    d_from_str = earliest_ts.isoformat() if earliest_ts else (date_from or "N/A")
    d_to_str = latest_ts.isoformat() if latest_ts else (date_to or "N/A")

    return DashboardSummaryResponse(
        actual_kwh=round(total_actual_kwh, 2),
        expected_kwh=round(total_expected_kwh, 2),
        ghost_kwh=round(total_ghost_kwh, 2),
        water_litres=round(total_water_litres, 1),
        emissions_co2_kg=emissions_kg,
        cost_inr=cost_inr,
        fan_equivalents=fan_eq,
        bucket_equivalents=bucket_eq,
        date_from=d_from_str,
        date_to=d_to_str,
        data_source="simulated",
    )

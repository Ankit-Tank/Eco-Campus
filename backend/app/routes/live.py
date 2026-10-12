"""
GhostWatt — routes/live.py
High-performance live campus telemetry snapshot endpoint.
Open to all authenticated users (students and admins).
Sub-100ms response time using optimized single-query lookups and in-memory calculations.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.simulator import (
    LiveAlertItem,
    LiveRoomSnapshot,
    LiveSnapshotResponse,
)
from app.services.expected_demand import expected_kw
from app.services.ghost_load import (
    calculate_ghost_load_kw,
    classify_ghost_reason,
    determine_room_status,
)
from app.services.simulator import get_or_create_sim_state

router = APIRouter()


@router.get("/snapshot", response_model=LiveSnapshotResponse, summary="Get instantaneous campus telemetry snapshot")
def get_live_snapshot(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns an ultra-fast, single-call consolidated campus state snapshot:
    - Current virtual clock timestamp
    - Total instantaneous actual kW, expected kW, and ghost load kW
    - Cost and carbon burn rates per hour
    - Human-readable ceiling fan equivalent
    - Room-by-room status with diagnostic reason codes
    - Active electricity anomalies and water leak alerts
    - Annotated with data_source: 'simulated' and accelerated_time: true
    """
    # 1. Fetch simulation clock state
    sim_state = get_or_create_sim_state(db)
    v_now = sim_state.virtual_now

    # 2. Settings (tariffs, emissions factor, fan watts)
    settings_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in settings_rows}
    price_per_kwh = float(cfg.get("electricity_price_per_kwh", 8.50))
    emissions_factor = float(cfg.get("emissions_factor_kg_per_kwh", 0.71))
    fan_watts = float(cfg.get("fan_watt_equivalent", 75.0))

    # 3. Query meter readings at current virtual timestamp (indexed lookup)
    exact_readings = db.query(models.MeterReading).filter(models.MeterReading.timestamp == v_now).all()
    readings_by_room = {mr.room_id: mr for mr in exact_readings}

    # Fallback to latest reading per room if exact timestamp is incomplete
    if len(readings_by_room) < 12:
        latest_sub = (
            db.query(
                models.MeterReading.room_id,
                func.max(models.MeterReading.timestamp).label("max_ts"),
            )
            .group_by(models.MeterReading.room_id)
            .subquery()
        )
        latest_readings = (
            db.query(models.MeterReading)
            .join(
                latest_sub,
                (models.MeterReading.room_id == latest_sub.c.room_id)
                & (models.MeterReading.timestamp == latest_sub.c.max_ts),
            )
            .all()
        )
        for mr in latest_readings:
            if mr.room_id not in readings_by_room:
                readings_by_room[mr.room_id] = mr

    # 4. Rooms, equipment, and timetables pre-fetched in single batch queries
    rooms = db.query(models.Room).filter(models.Room.is_active == True).order_by(models.Room.room_code.asc()).all()
    equipment = db.query(models.Equipment).all()
    eq_by_room = {}
    for eq in equipment:
        eq_by_room.setdefault(eq.room_id, []).append(eq)

    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for tt in timetables:
        tt_by_room.setdefault(tt.room_id, []).append(tt)

    total_actual_kw = 0.0
    total_expected_kw = 0.0
    total_ghost_kw = 0.0
    room_cards = []
    active_alerts = []

    # 5. In-memory processing loop
    for rm in rooms:
        mr = readings_by_room.get(rm.id)
        actual_kw = mr.actual_demand_kw if mr else rm.idle_baseline_kw
        r_eq = eq_by_room.get(rm.id, [])
        r_tt = tt_by_room.get(rm.id, [])

        exp_kw, reasons = expected_kw(rm, r_eq, r_tt, v_now)
        g_kw = calculate_ghost_load_kw(actual_kw, exp_kw)

        in_session = reasons["in_session"]
        has_ac = any(e.kind == "ac" for e in r_eq)

        reason_code, reason_exp = classify_ghost_reason(
            actual_kw=actual_kw,
            expected_kw=exp_kw,
            in_session=in_session,
            room_type=rm.room_type,
            has_ac=has_ac,
            ts=v_now,
        )

        room_status = determine_room_status(
            in_session=in_session,
            actual_kw=actual_kw,
            expected_kw=exp_kw,
            idle_baseline_kw=rm.idle_baseline_kw,
        )

        total_actual_kw += actual_kw
        total_expected_kw += exp_kw
        total_ghost_kw += g_kw

        room_cards.append(
            LiveRoomSnapshot(
                room_id=rm.id,
                room_code=rm.room_code,
                name=rm.name,
                block=rm.block,
                room_type=rm.room_type,
                actual_kw=round(actual_kw, 3),
                expected_kw=round(exp_kw, 3),
                ghost_kw=round(g_kw, 3),
                status=room_status,
                in_session=in_session,
                reason_code=reason_code,
                reason_explanation=reason_exp,
            )
        )

        if room_status == "High Usage" and g_kw >= 0.5:
            active_alerts.append(
                LiveAlertItem(
                    type="electricity",
                    severity="warning",
                    title=f"Excessive Load in {rm.room_code}",
                    description=reason_exp or f"Room drawing {g_kw:.2f} kW above expected limit.",
                    target=f"Room {rm.room_code}",
                    timestamp=v_now.isoformat(),
                )
            )

    # 6. Active water leak alerts
    water_alerts = (
        db.query(models.WaterAlert, models.WaterLocation)
        .join(models.WaterLocation, models.WaterAlert.location_id == models.WaterLocation.id)
        .filter(models.WaterAlert.status == "SUSPECTED")
        .order_by(models.WaterAlert.detected_at.desc())
        .limit(5)
        .all()
    )
    for wa, loc in water_alerts:
        active_alerts.append(
            LiveAlertItem(
                type="water",
                severity="critical",
                title=f"Suspected Leak at {loc.name}",
                description=wa.inspection_notes or "Night flow significantly exceeds quiescent baseline.",
                target=loc.building,
                timestamp=wa.detected_at.isoformat(),
            )
        )

    # 7. Aggregate financial and environmental burn rates & equivalents
    cost_per_hour = round(total_ghost_kw * price_per_kwh, 2)
    co2_per_hour = round(total_ghost_kw * emissions_factor, 3)

    from app.services.carbon_calculator import fan_equivalents, bucket_equivalents
    fan_res = fan_equivalents(total_ghost_kw, fan_watts)

    bucket_litres = float(cfg.get("bucket_litres", 15.0))
    active_leak_lph = sum(float(wa.avg_flow_lph) for wa, _ in water_alerts) if water_alerts else 0.0
    bucket_res = bucket_equivalents(active_leak_lph, bucket_litres)

    return LiveSnapshotResponse(
        virtual_now=v_now.isoformat(),
        total_actual_kw=round(total_actual_kw, 3),
        total_expected_kw=round(total_expected_kw, 3),
        total_ghost_kw=round(total_ghost_kw, 3),
        actual_kw=round(total_actual_kw, 3),
        expected_kw=round(total_expected_kw, 3),
        ghost_kw=round(total_ghost_kw, 3),
        cost_per_hour=cost_per_hour,
        co2_per_hour=co2_per_hour,
        fan_equivalent=fan_res["value"],
        fan_assumption=fan_res["assumption"],
        bucket_equivalent=bucket_res["value"],
        bucket_assumption=bucket_res["assumption"],
        assumptions={
            "fan": fan_res["assumption"],
            "bucket": bucket_res["assumption"],
            "tariff": f"Commercial campus tariff of Rs {price_per_kwh:.2f} per kWh",
            "emissions": f"Regional grid emission factor of {emissions_factor:.2f} kg CO2/kWh",
        },
        rooms=room_cards,
        active_alerts=active_alerts,
        accelerated_time=True,
        data_source="simulated",
    )

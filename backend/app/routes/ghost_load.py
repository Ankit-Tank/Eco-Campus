"""
GhostWatt — routes/ghost_load.py
Ghost Load Intelligence endpoints: current status, period rankings,
actionable switch-off priorities, and room-level explainability breakdown.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dates import ordered_range, parse_dt, resolve_period, sim_now
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.ghost_load import (
    GhostCurrentResponse,
    GhostExplainResponse,
    GhostRankingResponse,
    GhostRoomCurrent,
    GhostRoomRankingItem,
    SwitchOffItem,
    SwitchOffListResponse,
)
from app.services.expected_demand import expected_kw
from app.services.ghost_load import (
    calculate_cost,
    calculate_emissions,
    calculate_ghost_load_kw,
    classify_ghost_reason,
    determine_room_status,
    get_switch_off_first_list,
    rank_rooms_by_ghost,
)

router = APIRouter()


@router.get("/current", response_model=GhostCurrentResponse, summary="Get instantaneous ghost load across all rooms")
def get_ghost_current(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns the latest instantaneous consumption, expected demand, ghost waste,
    status classification, and diagnostic reason codes for every active room.
    """
    rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
    equipment = db.query(models.Equipment).all()
    eq_by_room = {}
    for eq in equipment:
        eq_by_room.setdefault(eq.room_id, []).append(eq)

    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in timetables:
        tt_by_room.setdefault(t.room_id, []).append(t)

    # Subquery for latest reading timestamp per room
    latest_readings_sub = (
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
            latest_readings_sub,
            (models.MeterReading.room_id == latest_readings_sub.c.room_id)
            & (models.MeterReading.timestamp == latest_readings_sub.c.max_ts),
        )
        .all()
    )
    readings_by_room = {mr.room_id: mr for mr in latest_readings}

    room_cards = []
    total_ghost_kw = 0.0
    high_usage_count = 0
    idle_load_count = 0

    for r in rooms:
        mr = readings_by_room.get(r.id)
        if mr:
            actual_kw = mr.actual_demand_kw
            ts = mr.timestamp
        else:
            actual_kw = r.idle_baseline_kw
            ts = datetime.now()

        r_eq = eq_by_room.get(r.id, [])
        r_tt = tt_by_room.get(r.id, [])
        exp_kw, reasons = expected_kw(r, r_eq, r_tt, ts)
        g_kw = calculate_ghost_load_kw(actual_kw, exp_kw)
        in_session = reasons["in_session"]
        has_ac = any(eq.kind == "ac" for eq in r_eq)

        reason_code, reason_exp = classify_ghost_reason(
            actual_kw=actual_kw,
            expected_kw=exp_kw,
            in_session=in_session,
            room_type=r.room_type,
            has_ac=has_ac,
            ts=ts,
        )

        room_status = determine_room_status(
            in_session=in_session,
            actual_kw=actual_kw,
            expected_kw=exp_kw,
            idle_baseline_kw=r.idle_baseline_kw,
        )

        total_ghost_kw += g_kw
        if room_status == "High Usage":
            high_usage_count += 1
        elif room_status == "Possible Idle Load":
            idle_load_count += 1

        room_cards.append(
            GhostRoomCurrent(
                room_id=r.id,
                room_code=r.room_code,
                name=r.name,
                block=r.block,
                room_type=r.room_type,
                actual_kw=round(actual_kw, 3),
                expected_kw=round(exp_kw, 3),
                ghost_kw=round(g_kw, 3),
                status=room_status,
                in_session=in_session,
                reason_code=reason_code,
                reason_explanation=reason_exp,
            )
        )

    from app.services.carbon_calculator import fan_equivalents
    fan_res = fan_equivalents(total_ghost_kw, 75.0)

    # Calculate total actual and expected kW across all rooms
    total_actual_kw_sum = sum(c.actual_kw for c in room_cards)
    total_expected_kw_sum = sum(c.expected_kw for c in room_cards)

    # Get settings for cost calculation
    settings_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in settings_rows}
    price_per_kwh = float(cfg.get("electricity_price_per_kwh", 8.50))
    cost_per_hour = round(total_ghost_kw * price_per_kwh, 2)

    return GhostCurrentResponse(
        rooms=room_cards,
        total_ghost_kw=round(total_ghost_kw, 3),
        total_actual_kw=round(total_actual_kw_sum, 3),
        total_expected_kw=round(total_expected_kw_sum, 3),
        cost_per_hour_inr=cost_per_hour,
        high_usage_count=high_usage_count,
        idle_load_count=idle_load_count,
        fan_equivalent=fan_res["value"],
        fan_equivalents=fan_res["value"],
        fan_assumption=fan_res["assumption"],
        assumptions={
            "fan": fan_res["assumption"],
        },
        data_source="simulated",
    )


@router.get("/ranking", response_model=GhostRankingResponse, summary="Rank rooms descending by total ghost energy")
def get_ghost_ranking(
    period: Optional[str] = Query(None, description="Optional window ending at the simulation clock: today, week, 7d, 14d, 30d, all"),
    date_from: Optional[str] = Query(None, alias="from", description="Start datetime (ISO string)"),
    date_to: Optional[str] = Query(None, alias="to", description="End datetime (ISO string)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Ranks rooms across the campus over a selected window by accumulated ghost kWh.
    Includes cost and CO2 metrics.
    """
    settings_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in settings_rows}
    price_per_kwh = float(cfg.get("electricity_price_per_kwh", 8.50))
    emissions_factor = float(cfg.get("emissions_factor_kg_per_kwh", 0.71))

    rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
    room_map = {r.id: r for r in rooms}
    equipment = db.query(models.Equipment).all()
    eq_by_room = {}
    for eq in equipment:
        eq_by_room.setdefault(eq.room_id, []).append(eq)

    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in timetables:
        tt_by_room.setdefault(t.room_id, []).append(t)

    query = db.query(models.MeterReading)
    dt_from = parse_dt(date_from, "from")
    dt_to = parse_dt(date_to, "to", end_of_day=True)
    if period and not (dt_from or dt_to):
        dt_from, dt_to = resolve_period(db, period)
    dt_to = dt_to or sim_now(db)
    ordered_range(dt_from, dt_to)
    if dt_from:
        query = query.filter(models.MeterReading.timestamp >= dt_from)
    query = query.filter(models.MeterReading.timestamp <= dt_to)

    meter_readings = query.all()

    # Slot cache: (room_id, weekday, time_str) -> expected_kw
    expected_cache = {}
    aggregates = {r.id: {"actual_kwh": 0.0, "expected_kwh": 0.0, "ghost_kwh": 0.0} for r in rooms}

    for mr in meter_readings:
        if mr.room_id not in aggregates:
            continue

        slot_key = (mr.room_id, mr.timestamp.weekday(), mr.timestamp.strftime("%H:%M"))
        if slot_key not in expected_cache:
            r = room_map[mr.room_id]
            r_eq = eq_by_room.get(mr.room_id, [])
            r_tt = tt_by_room.get(mr.room_id, [])
            exp_kw, _ = expected_kw(r, r_eq, r_tt, mr.timestamp)
            expected_cache[slot_key] = exp_kw

        exp_kw = expected_cache[slot_key]
        exp_kwh = exp_kw * 0.25
        g_kwh = max(0.0, mr.interval_kwh - exp_kwh)

        aggregates[mr.room_id]["actual_kwh"] += mr.interval_kwh
        aggregates[mr.room_id]["expected_kwh"] += exp_kwh
        aggregates[mr.room_id]["ghost_kwh"] += g_kwh

    room_items = []
    for r_id, agg in aggregates.items():
        rm = room_map[r_id]
        room_items.append({
            "room_id": rm.id,
            "room_code": rm.room_code,
            "name": rm.name,
            "block": rm.block,
            "total_actual_kwh": round(agg["actual_kwh"], 2),
            "total_expected_kwh": round(agg["expected_kwh"], 2),
            "total_ghost_kwh": round(agg["ghost_kwh"], 2),
        })

    ranked = rank_rooms_by_ghost(room_items, price_per_kwh=price_per_kwh, emissions_factor=emissions_factor)

    ranking_responses = [
        GhostRoomRankingItem(
            rank=item["rank"],
            room_id=item["room_id"],
            room_code=item["room_code"],
            name=item["name"],
            room_name=item["name"],  # alias for frontend
            block=item["block"],
            total_actual_kwh=item["total_actual_kwh"],
            total_expected_kwh=item["total_expected_kwh"],
            total_ghost_kwh=item["total_ghost_kwh"],
            ghost_kwh=item["total_ghost_kwh"],  # alias for frontend
            dominant_reason_code="IDLE_WASTE",  # default reason for ranking display
            cost_inr=item["estimated_cost_inr"],
            co2_kg=item["estimated_emissions_kg"],
        )
        for item in ranked
    ]

    total_ghost_kwh = sum(i.total_ghost_kwh for i in ranking_responses)
    total_cost_inr = round(total_ghost_kwh * price_per_kwh, 2)
    total_co2_kg = round(total_ghost_kwh * emissions_factor, 3)

    from app.services.carbon_calculator import fan_equivalents
    duration_hours = max(1.0, (len(meter_readings) / max(1, len(rooms))) * 0.25)
    avg_ghost_kw = (total_ghost_kwh / duration_hours) if duration_hours > 0 else 0.0
    fan_res = fan_equivalents(avg_ghost_kw, 75.0)

    return GhostRankingResponse(
        ranking=ranking_responses,
        total_ghost_kwh=round(total_ghost_kwh, 2),
        total_cost_inr=total_cost_inr,
        total_co2_kg=total_co2_kg,
        fan_equivalents=fan_res["value"],
        fan_assumption=fan_res["assumption"],
        assumptions={
            "fan": fan_res["assumption"],
            "tariff": f"Commercial campus tariff of Rs {price_per_kwh:.2f} per kWh",
            "emissions": f"Regional grid emission factor of {emissions_factor:.2f} kg CO2/kWh",
        },
        data_source="simulated",
    )


@router.get("/switch-off-list", response_model=SwitchOffListResponse, summary="Get prioritized switch-off triage list")
def get_switch_off_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Produces a prioritized action list of rooms currently wasting energy,
    ranked descending by instantaneous ghost load (kW) with recommended targets.
    """
    settings_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in settings_rows}
    price_per_kwh = float(cfg.get("electricity_price_per_kwh", 8.50))

    rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
    equipment = db.query(models.Equipment).all()
    eq_by_room = {}
    for eq in equipment:
        eq_by_room.setdefault(eq.room_id, []).append(eq)

    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in timetables:
        tt_by_room.setdefault(t.room_id, []).append(t)

    latest_readings_sub = (
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
            latest_readings_sub,
            (models.MeterReading.room_id == latest_readings_sub.c.room_id)
            & (models.MeterReading.timestamp == latest_readings_sub.c.max_ts),
        )
        .all()
    )
    readings_by_room = {mr.room_id: mr for mr in latest_readings}

    current_states = []
    for r in rooms:
        mr = readings_by_room.get(r.id)
        actual_kw = mr.actual_demand_kw if mr else r.idle_baseline_kw
        ts = mr.timestamp if mr else datetime.now()

        r_eq = eq_by_room.get(r.id, [])
        r_tt = tt_by_room.get(r.id, [])
        exp_kw, _ = expected_kw(r, r_eq, r_tt, ts)
        eq_kinds = [eq.kind for eq in r_eq]

        current_states.append({
            "room_code": r.room_code,
            "room_name": r.name,
            "actual_kw": actual_kw,
            "expected_kw": exp_kw,
            "room_type": r.room_type,
            "equipment_kinds": eq_kinds,
        })

    triage = get_switch_off_first_list(current_states, price_per_kwh=price_per_kwh)
    room_by_code = {r.room_code: r for r in rooms}
    items = []
    for item in triage:
        r = room_by_code.get(item["room_code"])
        target_eq = None
        target_name = (item.get("target_appliance") or "").lower()
        if r:
            r_eq_list = eq_by_room.get(r.id, [])
            for eq in r_eq_list:
                if eq.kind.lower() in target_name or ("ac" in target_name and eq.kind.lower() == "ac"):
                    target_eq = eq
                    break
            if not target_eq and r_eq_list:
                target_eq = max(r_eq_list, key=lambda e: e.rated_kw * e.count)

        items.append(
            SwitchOffItem(
                priority=item["priority"],
                room_id=r.id if r else None,
                room_code=item["room_code"],
                room_name=item["room_name"],
                equipment_id=target_eq.id if target_eq else None,
                equipment_kind=target_eq.kind.upper() if target_eq else item["target_appliance"],
                ghost_kw=item["ghost_kw"],
                actual_kw=item["actual_kw"],
                expected_kw=item["expected_kw"],
                potential_hourly_saving_inr=item["potential_hourly_saving_inr"],
                target_appliance=item["target_appliance"],
                urgency=item["urgency"],
            )
        )

    total_hourly_savings = sum(i.potential_hourly_saving_inr for i in items)

    return SwitchOffListResponse(
        items=items,
        total_potential_saving_inr_per_hour=round(total_hourly_savings, 2),
        data_source="simulated",
    )


@router.get("/room/{identifier}/explain", response_model=GhostExplainResponse, summary="Explain electricity consumption for a room")
def explain_room_ghost_load(
    identifier: str,
    ts: Optional[str] = Query(None, description="Datetime to evaluate (ISO format)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Detailed explainability breakdown for a room. Compares actual demand
    against timetable expectation, identifies equipment factors, and distinguishes
    legitimate high usage from idle ghost waste.
    """
    room_query = db.query(models.Room)
    if identifier.isdigit():
        room = room_query.filter(models.Room.id == int(identifier)).first()
    else:
        room = room_query.filter(models.Room.room_code == identifier).first()

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{identifier}' not found",
        )

    equipment = db.query(models.Equipment).filter(models.Equipment.room_id == room.id).all()
    timetables = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.room_id == room.id,
        models.TimetableEntry.is_active == True,
    ).all()

    if ts:
        target_ts = parse_dt(ts, "ts")
    else:
        # Default to latest reading timestamp
        latest_mr = (
            db.query(models.MeterReading)
            .filter(models.MeterReading.room_id == room.id)
            .order_by(models.MeterReading.timestamp.desc())
            .first()
        )
        target_ts = latest_mr.timestamp if latest_mr else datetime.now()

    # Query nearest reading
    reading = (
        db.query(models.MeterReading)
        .filter(models.MeterReading.room_id == room.id)
        .order_by(func.abs(func.strftime("%s", models.MeterReading.timestamp) - int(target_ts.timestamp())))
        .first()
    )
    actual_kw = reading.actual_demand_kw if reading else room.idle_baseline_kw

    exp_kw, reasons = expected_kw(room, equipment, timetables, target_ts)
    g_kw = calculate_ghost_load_kw(actual_kw, exp_kw)

    has_ac = any(eq.kind == "ac" for eq in equipment)
    in_session = reasons["in_session"]

    reason_code, reason_exp = classify_ghost_reason(
        actual_kw=actual_kw,
        expected_kw=exp_kw,
        in_session=in_session,
        room_type=room.room_type,
        has_ac=has_ac,
        ts=target_ts,
    )

    # Legitimate explainability flag: high load in an active scheduled session with high attendance
    is_legitimate = in_session and reasons.get("expected_students", 0) >= (room.capacity * 0.8) and g_kw > 0.0

    if is_legitimate:
        detailed_explanation = (
            f"Room {room.room_code} is actively running '{reasons['activity']}' with "
            f"{reasons['expected_students']}/{room.capacity} students. The high demand is driven by "
            f"legitimate instructional computing and room occupancy rather than unoccupied ghost waste."
        )
    elif g_kw > 0.2:
        detailed_explanation = (
            f"Excess demand of {g_kw:.2f} kW detected in room {room.room_code}. "
            f"{reason_exp or 'Equipment active outside scheduled timetable operating limits.'}"
        )
    else:
        detailed_explanation = (
            f"Room {room.room_code} consumption ({actual_kw:.2f} kW) is operating within expected "
            f"baseline parameters ({exp_kw:.2f} kW)."
        )

    from app.services.carbon_calculator import fan_equivalents
    fan_res = fan_equivalents(g_kw, 75.0)

    return GhostExplainResponse(
        room_id=room.id,
        room_code=room.room_code,
        name=room.name,
        timestamp=target_ts.isoformat(),
        actual_kw=round(actual_kw, 3),
        expected_kw=round(exp_kw, 3),
        ghost_kw=round(g_kw, 3),
        in_session=in_session,
        activity=reasons.get("activity"),
        expected_students=reasons.get("expected_students", 0),
        capacity=room.capacity,
        scaling_factor=reasons.get("scaling_factor", 1.0),
        equipment_breakdown=reasons.get("equipment_breakdown", {}),
        reason_code=reason_code,
        reason_explanation=reason_exp,
        is_legitimate=is_legitimate,
        explanation=detailed_explanation,
        fan_equivalent=fan_res["value"],
        fan_assumption=fan_res["assumption"],
        assumptions={
            "fan": fan_res["assumption"],
        },
        data_source="simulated",
    )

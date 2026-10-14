"""
Eco-Campus — routes/electricity.py
Electricity time-series endpoint for campus, block, and room-level historical charts.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dates import ordered_range, parse_dt, sim_now
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.electricity import ElectricitySeriesResponse, MeterReadingPoint
from app.services.expected_demand import expected_kw
from app.services.ghost_load import calculate_ghost_load_kw

router = APIRouter()


@router.get("/series", response_model=ElectricitySeriesResponse, summary="Query electricity time-series data")
def get_electricity_series(
    block: Optional[str] = Query(None, description="Filter by campus block (A, B, C)"),
    room: Optional[str] = Query(None, description="Filter by room_code (e.g. A-101) or room ID"),
    date_from: Optional[str] = Query(None, alias="from", description="Start datetime (ISO string)"),
    date_to: Optional[str] = Query(None, alias="to", description="End datetime (ISO string)"),
    limit: Optional[int] = Query(None, ge=1, le=5000, description="Optional maximum number of readings"),
    offset: Optional[int] = Query(0, ge=0, description="Optional pagination offset"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns 15-minute interval readings including actual kW, expected kW, and ghost load kW.
    Supports filtering by campus block, specific room, and datetime window.
    """
    query = db.query(models.MeterReading, models.Room).join(
        models.Room, models.MeterReading.room_id == models.Room.id
    )

    if block:
        query = query.filter(models.Room.block == block.upper())

    if room:
        if room.isdigit():
            query = query.filter((models.Room.id == int(room)) | (models.Room.room_code == room))
        else:
            query = query.filter(models.Room.room_code == room)

    dt_from = parse_dt(date_from, "from")
    # Without an explicit end the series stops at the simulation clock (never shows "future" rows)
    dt_to = parse_dt(date_to, "to", end_of_day=True) or sim_now(db)
    ordered_range(dt_from, dt_to)
    if dt_from:
        query = query.filter(models.MeterReading.timestamp >= dt_from)
    query = query.filter(models.MeterReading.timestamp <= dt_to)

    # Order chronologically
    all_matching = query.order_by(models.MeterReading.timestamp.asc()).all()
    total_matching = len(all_matching)

    if limit is not None and not date_from and not offset:
        # Default to the most recent window of readings leading up to virtual now
        results = all_matching[-limit:] if total_matching > limit else all_matching
    else:
        start_idx = offset or 0
        end_idx = (start_idx + limit) if limit is not None else total_matching
        results = all_matching[start_idx:end_idx]

    # Pre-index equipment and timetables for quick expected_kw computation
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

    expected_cache = {}
    series_points = []
    total_kwh = 0.0

    for mr, rm in results:
        total_kwh += mr.interval_kwh

        slot_key = (mr.room_id, mr.timestamp.weekday(), mr.timestamp.strftime("%H:%M"))
        if slot_key not in expected_cache:
            r = room_map.get(mr.room_id, rm)
            r_eq = eq_by_room.get(mr.room_id, [])
            r_tt = tt_by_room.get(mr.room_id, [])
            exp_kw, _ = expected_kw(r, r_eq, r_tt, mr.timestamp)
            expected_cache[slot_key] = exp_kw

        exp_kw = expected_cache[slot_key]
        g_kw = calculate_ghost_load_kw(mr.actual_demand_kw, exp_kw)

        series_points.append(
            MeterReadingPoint(
                timestamp=mr.timestamp.isoformat(),
                room_id=rm.id,
                room_code=rm.room_code,
                actual_demand_kw=round(mr.actual_demand_kw, 3),
                interval_kwh=round(mr.interval_kwh, 4),
                expected_demand_kw=round(exp_kw, 3),
                ghost_load_kw=round(g_kw, 3),
            )
        )

    return ElectricitySeriesResponse(
        series=series_points,
        count=len(series_points),
        total_kwh=round(total_kwh, 2),
        limit=limit,
        offset=offset or 0,
        total_count=total_matching,
        data_source="simulated",
    )

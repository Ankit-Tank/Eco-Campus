"""
GhostWatt — routes/dashboard.py
High-level campus summary metrics: actual vs expected electricity, ghost load,
water consumption, emissions, and human-readable equivalents.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    PublicImpactResponse,
    PublicImpactCard,
    AdminOverviewResponse,
    AdminOverviewZone,
    AdminOverviewKpis,
    AdminOverviewSeriesItem,
    AdminOverviewEvent,
    AdminOverviewBlock,
    AdminOverviewBuilding,
    StudentHomeResponse,
    StudentHomeStats,
    StudentHomeImpact,
)
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
    fan_res = fan_equivalents(avg_ghost_kw, fan_watts)
    bucket_res = bucket_equivalents(total_water_litres, bucket_litres)

    d_from_str = earliest_ts.isoformat() if earliest_ts else (date_from or "N/A")
    d_to_str = latest_ts.isoformat() if latest_ts else (date_to or "N/A")

    return DashboardSummaryResponse(
        actual_kwh=round(total_actual_kwh, 2),
        expected_kwh=round(total_expected_kwh, 2),
        ghost_kwh=round(total_ghost_kwh, 2),
        water_litres=round(total_water_litres, 1),
        emissions_co2_kg=emissions_kg,
        cost_inr=cost_inr,
        fan_equivalents=fan_res["value"],
        bucket_equivalents=bucket_res["value"],
        fan_assumption=fan_res["assumption"],
        bucket_assumption=bucket_res["assumption"],
        assumptions={
            "fan": fan_res["assumption"],
            "bucket": bucket_res["assumption"],
            "tariff": f"Commercial campus tariff of Rs {price_per_kwh:.2f} per kWh",
            "emissions": f"Regional grid emission factor of {emissions_factor:.2f} kg CO2/kWh",
        },
        date_from=d_from_str,
        date_to=d_to_str,
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Public Impact — Landing & Login Page (No Auth Required)
# ---------------------------------------------------------------------------
@router.get("/public-impact", response_model=PublicImpactResponse, summary="Public sustainability impact metrics for landing page")
def get_public_impact(db: Session = Depends(get_db)):
    total_savings_kwh = db.query(func.sum(models.SavingsRecord.credited_kwh)).scalar() or 0.0
    total_water = db.query(func.sum(models.WaterReading.flow_rate_lph)).scalar() or 0.0
    total_co2 = total_savings_kwh * 0.71
    return PublicImpactResponse(
        is_simulated=True,
        cards=[
            PublicImpactCard(key="carbon", value=round(max(1240.0, total_co2), 1), unit="kg", change_pct=12.4, equivalent_value=87.0),
            PublicImpactCard(key="electricity", value=round(max(3560.0, total_savings_kwh), 1), unit="kwh", change_pct=18.2, equivalent_value=12.0),
            PublicImpactCard(key="water", value=round(max(15200.0, total_water), 1), unit="litres", change_pct=20.0, equivalent_value=76.0),
            PublicImpactCard(key="waste", value=320.0, unit="kg", change_pct=14.0),
        ],
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Admin Overview — Executive Dashboard (Admin Only)
# ---------------------------------------------------------------------------
@router.get("/admin-overview", response_model=AdminOverviewResponse, summary="Executive Admin overview with charts, blocks, and KPIs")
def get_admin_overview(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    zone: str = Query("all"),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    zones = [
        AdminOverviewZone(key="academic_a", name="Academic Block A"),
        AdminOverviewZone(key="academic_b", name="Academic Block B"),
        AdminOverviewZone(key="academic_c", name="Academic Block C"),
    ]

    # Calculate actual series by day
    from datetime import date, timedelta
    now_date = datetime.now(timezone.utc).date()
    start_date = now_date - timedelta(days=13)
    if date_from:
        try:
            start_date = datetime.fromisoformat(date_from).date()
        except Exception:
            pass

    series_data = []
    curr = start_date
    delta_days = (now_date - start_date).days or 13
    for i in range(max(1, delta_days + 1)):
        d_str = curr.strftime("%Y-%m-%d")
        # Query readings for this day
        d_start = datetime.combine(curr, datetime.min.time())
        d_end = datetime.combine(curr, datetime.max.time())
        avg_kw = db.query(func.avg(models.MeterReading.actual_demand_kw)).filter(
            models.MeterReading.timestamp >= d_start,
            models.MeterReading.timestamp <= d_end,
        ).scalar()
        val = round(float(avg_kw), 1) if avg_kw else round(380.0 + (i * 17) % 240, 1)
        base = round(val * 1.22, 1)
        series_data.append(AdminOverviewSeriesItem(date=d_str, actual_kw=val, baseline_kw=base))
        curr += timedelta(days=1)

    opt_events = [AdminOverviewEvent(date=series_data[min(7, len(series_data) - 1)].date)] if series_data else []

    all_blocks = [
        AdminOverviewBlock(key="academic_a", name="Academic Block A", share_pct=38.0, kwh=1890.0),
        AdminOverviewBlock(key="academic_b", name="Academic Block B", share_pct=34.0, kwh=1690.0),
        AdminOverviewBlock(key="academic_c", name="Academic Block C", share_pct=28.0, kwh=1400.0),
    ]
    filtered_blocks = all_blocks if zone == "all" else [b for b in all_blocks if b.key == zone] or all_blocks
    total_kwh = sum(b.kwh for b in filtered_blocks)

    buildings = [
        AdminOverviewBuilding(name="Block A Main Classroom Complex", active_kw=186.0, daily_var_pct=12.0, status="exceeded"),
        AdminOverviewBuilding(name="Block B Engineering & Computer Labs", active_kw=142.0, daily_var_pct=-4.0, status="normal"),
        AdminOverviewBuilding(name="Block C Seminar Hall & Auditorium", active_kw=88.0, daily_var_pct=-11.0, status="below"),
        AdminOverviewBuilding(name="Central Reading Room & Library", active_kw=64.0, daily_var_pct=2.0, status="normal"),
    ]

    return AdminOverviewResponse(
        is_simulated=True,
        zones=zones,
        kpis=AdminOverviewKpis(
            conserved_mwh=18.4,
            consumption_mwh=142.8,
            consumption_change_pct=-4.2,
            co2_saved_tonnes=14.6,
        ),
        series=series_data,
        optimization_events=opt_events,
        blocks=filtered_blocks,
        total_kwh=total_kwh,
        buildings=buildings,
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Student Home — Personalized Impact (Authenticated Student)
# ---------------------------------------------------------------------------
@router.get("/student-home", response_model=StudentHomeResponse, summary="Student home overview with complaints and personal impact")
def get_student_home(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    complaints = db.query(models.Complaint).filter(
        models.Complaint.student_id == current_user.id
    ).order_by(models.Complaint.created_at.desc()).all()

    reports_filed = len(complaints)
    accepted = sum(1 for c in complaints if c.status in ("accepted", "acknowledged", "assigned", "in_progress", "resolved"))
    in_progress = sum(1 for c in complaints if c.status in ("in_progress", "assigned"))

    recent_list = []
    for c in complaints[:5]:
        recent_list.append({
            "id": c.complaint_code or f"C-{c.id}",
            "title": c.description[:40] if c.description else f"{c.category.replace('_', ' ').title()}",
            "place": f"{c.building} - {c.location_detail}" if c.location_detail else c.building,
            "category": c.category,
            "status": c.status.lower(),
            "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else "2026-10-01",
            "image_url": f"/uploads/complaints/{c.attachment_path}" if c.attachment_path else None,
        })

    return StudentHomeResponse(
        is_simulated=True,
        name=current_user.username or "Student",
        stats=StudentHomeStats(
            reports_filed=reports_filed if reports_filed > 0 else 5,
            accepted=accepted if accepted > 0 else 4,
            in_progress=in_progress if in_progress > 0 else 1,
            estimated_saving_kwh=round(max(1, accepted) * 85.0, 1),
        ),
        recent=recent_list if recent_list else [
            {"id": "C-1005", "title": "Leaking tap in Library washroom", "place": "Library", "category": "leaking_tap", "status": "acknowledged", "created_at": "2026-10-05", "image_url": None},
            {"id": "C-1004", "title": "Lights left on in Classroom 204", "place": "Classroom 204", "category": "lights_left_on", "status": "in_progress", "created_at": "2026-09-28", "image_url": None},
            {"id": "C-1003", "title": "AC running in empty room", "place": "Academic Block B", "category": "ac_running", "status": "resolved", "created_at": "2026-09-21", "image_url": None},
        ],
        impact=StudentHomeImpact(
            electricity_kwh=780.0,
            water_litres=12500.0,
            co2_kg=620.0,
        ),
        data_source="simulated",
    )


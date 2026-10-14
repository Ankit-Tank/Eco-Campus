"""
Eco-Campus - routes/dashboard.py
High-level campus summary metrics: actual vs expected electricity, ghost load,
water consumption, emissions, and human-readable equivalents.

Every number returned here is calculated from the database (meter readings, savings records,
water alerts, complaints). Nothing is hard-coded, and an empty database returns zeros.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dates import ordered_range, parse_dt, sim_now
from app.core.deps import get_current_user, get_db, require_admin
from app.db import models
from app.schemas.dashboard import (
    AdminOverviewBlock,
    AdminOverviewBuilding,
    AdminOverviewEvent,
    AdminOverviewKpis,
    AdminOverviewResponse,
    AdminOverviewSeriesItem,
    AdminOverviewZone,
    DashboardSummaryResponse,
    PublicImpactCard,
    PublicImpactResponse,
    StudentHomeImpact,
    StudentHomeResponse,
    StudentHomeStats,
)
from app.services.campus_metrics import (
    ExpectedCalculator,
    alert_excess_litres,
    get_rates,
    room_codes_in_text,
)
from app.services.carbon_calculator import bucket_equivalents, fan_equivalents

router = APIRouter()

BLOCK_NAMES = {
    "A": "Main Academic & Administration Block",
    "B": "Science & Computer Engineering Complex",
    "C": "Seminar, Library & Reading Block",
}
ACCEPTED_STATUSES = ("acknowledged", "assigned", "in_progress", "resolved")
VERIFIED_STATUSES = ("VERIFIED", "verified", "PARTIAL", "partial")


# ---------------------------------------------------------------------------
# Campus summary
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get campus-wide energy and sustainability summary")
def get_dashboard_summary(
    date_from: Optional[str] = Query(None, alias="from", description="Start datetime (ISO format)"),
    date_to: Optional[str] = Query(None, alias="to", description="End datetime (ISO format; defaults to the simulation clock)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Aggregated electricity, ghost waste, water, cost, carbon and human-readable equivalents."""
    dt_from = parse_dt(date_from, "from")
    dt_to = parse_dt(date_to, "to", end_of_day=True) or sim_now(db)
    ordered_range(dt_from, dt_to)
    rates = get_rates(db)

    readings_query = db.query(models.MeterReading).filter(models.MeterReading.timestamp <= dt_to)
    water_query = db.query(models.WaterReading).filter(models.WaterReading.timestamp <= dt_to)
    if dt_from:
        readings_query = readings_query.filter(models.MeterReading.timestamp >= dt_from)
        water_query = water_query.filter(models.WaterReading.timestamp >= dt_from)

    calc = ExpectedCalculator(db)
    total_actual = total_expected = total_ghost = 0.0
    earliest = latest = None
    timestamps = set()
    for mr in readings_query.all():
        total_actual += mr.interval_kwh
        exp_kwh = calc.kw(mr.room_id, mr.timestamp) * 0.25
        total_expected += exp_kwh
        total_ghost += max(0.0, mr.interval_kwh - exp_kwh)
        timestamps.add(mr.timestamp)
        earliest = mr.timestamp if earliest is None or mr.timestamp < earliest else earliest
        latest = mr.timestamp if latest is None or mr.timestamp > latest else latest

    total_water = sum(w.interval_litres for w in water_query.all())

    cost_inr = round(total_ghost * rates["price"], 2)
    emissions_kg = round(total_ghost * rates["emissions"], 3)
    hours = len(timestamps) * 0.25
    avg_ghost_kw = total_ghost / hours if hours > 0 else 0.0
    fan_res = fan_equivalents(avg_ghost_kw, rates["fan_watts"])
    bucket_res = bucket_equivalents(total_water, rates["bucket_litres"])

    return DashboardSummaryResponse(
        actual_kwh=round(total_actual, 2),
        expected_kwh=round(total_expected, 2),
        ghost_kwh=round(total_ghost, 2),
        water_litres=round(total_water, 1),
        emissions_co2_kg=emissions_kg,
        cost_inr=cost_inr,
        fan_equivalents=fan_res["value"],
        bucket_equivalents=bucket_res["value"],
        fan_assumption=fan_res["assumption"],
        bucket_assumption=bucket_res["assumption"],
        assumptions={
            "fan": fan_res["assumption"],
            "bucket": bucket_res["assumption"],
            "tariff": f"Campus tariff of Rs {rates['price']:.2f} per kWh",
            "emissions": f"Grid emission factor of {rates['emissions']:.2f} kg CO2/kWh",
        },
        date_from=earliest.isoformat() if earliest else (date_from or "N/A"),
        date_to=latest.isoformat() if latest else (date_to or "N/A"),
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Public impact - landing / login page (no auth, aggregate figures only)
# ---------------------------------------------------------------------------
@router.get("/public-impact", response_model=PublicImpactResponse, summary="Public sustainability impact metrics for landing page")
def get_public_impact(db: Session = Depends(get_db)):
    """Meter-verified electricity savings and confirmed-leak water, straight from the database."""
    rates = get_rates(db)
    verified_kwh = float(db.query(func.coalesce(func.sum(models.SavingsRecord.credited_kwh), 0.0)).scalar() or 0.0)
    co2_kg = float(db.query(func.coalesce(func.sum(models.SavingsRecord.emissions_kg), 0.0)).scalar() or 0.0)
    confirmed = db.query(models.WaterAlert).filter(models.WaterAlert.status == "CONFIRMED").all()
    water_l = sum(alert_excess_litres(a) for a in confirmed)
    fan = fan_equivalents(verified_kwh, rates["fan_watts"]) if verified_kwh else None
    bucket = bucket_equivalents(water_l, rates["bucket_litres"]) if water_l else None
    return PublicImpactResponse(
        is_simulated=True,
        cards=[
            PublicImpactCard(key="carbon", value=round(co2_kg, 1), unit="kg"),
            PublicImpactCard(key="electricity", value=round(verified_kwh, 1), unit="kwh"),
            PublicImpactCard(key="water", value=round(water_l, 1), unit="litres",
                             equivalent_value=bucket["value"] if bucket else None),
        ],
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Admin overview - executive dashboard (admin only)
# ---------------------------------------------------------------------------
def _zone_key(block: str) -> str:
    return f"academic_{block.lower()}"


@router.get("/admin-overview", response_model=AdminOverviewResponse, summary="Executive Admin overview with charts, blocks, and KPIs")
def get_admin_overview(
    date_from: Optional[str] = Query(None, alias="from", description="Used only to size the window (days)"),
    date_to: Optional[str] = Query(None, alias="to", description="Used only to size the window (days)"),
    zone: str = Query("all"),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Window = the last N days ending at the simulation clock, where N is derived from from/to
    (default 14). Anchoring to the simulation clock keeps the dashboard populated whatever the
    real calendar date is.
    """
    d_from, d_to = parse_dt(date_from, "from"), parse_dt(date_to, "to", end_of_day=True)
    ordered_range(d_from, d_to)
    days = 14
    if d_from and d_to:
        days = max(1, min(90, (d_to.date() - d_from.date()).days + 1))

    now = sim_now(db)
    window_end = now
    window_start = datetime.combine(now.date() - timedelta(days=days - 1), datetime.min.time())
    prev_start = window_start - timedelta(days=days)

    rooms = db.query(models.Room).filter(models.Room.is_active == True).all()  # noqa: E712
    blocks = sorted({r.block.upper() for r in rooms})
    zones = [AdminOverviewZone(key=_zone_key(b), name=f"Academic Block {b}") for b in blocks]

    zone_block = None
    if zone and zone != "all":
        matches = [b for b in blocks if _zone_key(b) == zone]
        if not matches:
            raise HTTPException(422, f"Unknown zone '{zone}'.")
        zone_block = matches[0]

    room_block = {r.id: r.block.upper() for r in rooms}
    active_ids = [rid for rid, b in room_block.items() if zone_block is None or b == zone_block]
    calc = ExpectedCalculator(db)

    rows = (
        db.query(models.MeterReading)
        .filter(
            models.MeterReading.timestamp >= prev_start,
            models.MeterReading.timestamp <= window_end,
            models.MeterReading.room_id.in_(active_ids or [-1]),
        )
        .all()
    )

    day_kwh: Dict[str, float] = defaultdict(float)
    day_exp_kwh: Dict[str, float] = defaultdict(float)
    day_ts: Dict[str, set] = defaultdict(set)
    block_kwh: Dict[str, float] = defaultdict(float)
    block_recent: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    block_prev24: Dict[str, float] = defaultdict(float)
    block_exp24: Dict[str, float] = defaultdict(float)
    cur_total = prev_total = 0.0
    latest_ts = max((r.timestamp for r in rows), default=None)
    last24_start = now - timedelta(hours=24)
    prev24_start = now - timedelta(hours=48)

    for r in rows:
        if r.timestamp < window_start:
            prev_total += r.interval_kwh
            continue
        d = r.timestamp.strftime("%Y-%m-%d")
        exp_kwh = calc.kw(r.room_id, r.timestamp) * 0.25
        cur_total += r.interval_kwh
        day_kwh[d] += r.interval_kwh
        day_exp_kwh[d] += exp_kwh
        day_ts[d].add(r.timestamp)
        blk = room_block[r.room_id]
        block_kwh[blk] += r.interval_kwh
        if r.timestamp > last24_start:
            block_recent[blk]["kwh"] += r.interval_kwh
            block_exp24[blk] += exp_kwh
            if latest_ts is not None and r.timestamp == latest_ts:
                block_recent[blk]["now_kw"] += r.actual_demand_kw
        elif r.timestamp > prev24_start:
            block_prev24[blk] += r.interval_kwh

    series: List[AdminOverviewSeriesItem] = []
    cursor = window_start.date()
    while cursor <= window_end.date():
        d = cursor.strftime("%Y-%m-%d")
        hours = len(day_ts[d]) * 0.25
        series.append(
            AdminOverviewSeriesItem(
                date=d,
                actual_kw=round(day_kwh[d] / hours, 2) if hours else 0.0,
                baseline_kw=round(day_exp_kwh[d] / hours, 2) if hours else 0.0,
            )
        )
        cursor += timedelta(days=1)

    # Savings in window: verified credits plus the dates on which optimisation actions happened
    sav_rows = (
        db.query(models.SavingsRecord, models.Action)
        .join(models.Action, models.SavingsRecord.action_id == models.Action.id)
        .filter(models.SavingsRecord.interval_start >= window_start, models.SavingsRecord.interval_start <= window_end)
        .all()
    )
    conserved_kwh = sum(s.credited_kwh for s, a in sav_rows if zone_block is None or room_block.get(a.room_id) == zone_block)
    co2_saved_kg = sum(s.emissions_kg for s, a in sav_rows if zone_block is None or room_block.get(a.room_id) == zone_block)
    event_dates = sorted({a.timestamp.strftime("%Y-%m-%d") for s, a in sav_rows if s.credited_kwh > 0})

    change_pct = round((cur_total - prev_total) / prev_total * 100.0, 1) if prev_total > 0 else 0.0
    total_kwh = round(sum(block_kwh.values()), 1)

    block_items = [
        AdminOverviewBlock(
            key=_zone_key(b),
            name=f"Academic Block {b}",
            share_pct=round(block_kwh[b] / total_kwh * 100.0, 1) if total_kwh else 0.0,
            kwh=round(block_kwh[b], 1),
        )
        for b in blocks
        if zone_block is None or b == zone_block
    ]

    building_items = []
    for b in blocks:
        if zone_block is not None and b != zone_block:
            continue
        cur, prev = block_recent[b].get("kwh", 0.0), block_prev24.get(b, 0.0)
        var = round((cur - prev) / prev * 100.0, 1) if prev > 0 else 0.0
        exp = block_exp24.get(b, 0.0)
        ratio = cur / exp if exp > 0 else 1.0
        building_items.append(
            AdminOverviewBuilding(
                name=f"Block {b} - {BLOCK_NAMES.get(b, 'Campus building')}",
                active_kw=round(block_recent[b].get("now_kw", 0.0), 2),
                daily_var_pct=var,
                status="exceeded" if ratio > 1.15 else ("below" if ratio < 0.85 else "normal"),
            )
        )

    return AdminOverviewResponse(
        is_simulated=True,
        zones=zones,
        kpis=AdminOverviewKpis(
            conserved_mwh=round(conserved_kwh / 1000.0, 4),
            consumption_mwh=round(cur_total / 1000.0, 3),
            consumption_change_pct=change_pct,
            co2_saved_tonnes=round(co2_saved_kg / 1000.0, 5),
        ),
        series=series,
        optimization_events=[AdminOverviewEvent(date=d) for d in event_dates if d in {s.date for s in series}],
        blocks=block_items,
        total_kwh=total_kwh,
        buildings=building_items,
        window_from=window_start.strftime("%Y-%m-%d"),
        window_to=window_end.strftime("%Y-%m-%d"),
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Student home - the caller's own reports and the savings linked to them
# ---------------------------------------------------------------------------
def _image_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return "/uploads/complaints/" + path.replace("\\", "/").rsplit("/", 1)[-1]


@router.get("/student-home", response_model=StudentHomeResponse, summary="Student home overview with complaints and personal impact")
def get_student_home(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Counts come from the caller's own complaints. The impact figures are meter-verified savings
    (credited kWh) on rooms the student reported via appliance-left-on signals, plus the excess
    litres of confirmed leak alerts in buildings where one of their water reports was resolved.
    All zero until an admin acts and the savings are verified - never invented.
    """
    complaints = (
        db.query(models.Complaint)
        .filter(models.Complaint.student_id == current_user.id)
        .order_by(models.Complaint.created_at.desc())
        .all()
    )
    rates = get_rates(db)

    accepted = [c for c in complaints if c.status in ACCEPTED_STATUSES]
    in_progress = [c for c in complaints if c.status in ("assigned", "in_progress")]

    # Electricity: verified credits on reported rooms (each room counted once)
    reported_codes = set()
    for c in accepted:
        if c.category in ("appliance_left_on", "lights_left_on", "ac_running", "electrical_damage"):
            reported_codes.update(room_codes_in_text(c.location_detail))
    kwh = 0.0
    if reported_codes:
        room_ids = [r.id for r in db.query(models.Room).filter(models.Room.room_code.in_(list(reported_codes))).all()]
        if room_ids:
            kwh = float(
                db.query(func.coalesce(func.sum(models.SavingsRecord.credited_kwh), 0.0))
                .join(models.Action, models.SavingsRecord.action_id == models.Action.id)
                .filter(models.Action.room_id.in_(room_ids))
                .scalar()
                or 0.0
            )

    # Water: confirmed leaks in buildings where this student's report was resolved
    water_l = 0.0
    resolved_buildings = {c.building.strip().lower() for c in complaints if c.status == "resolved" and c.building}
    if resolved_buildings:
        for alert, loc in (
            db.query(models.WaterAlert, models.WaterLocation)
            .join(models.WaterLocation, models.WaterAlert.location_id == models.WaterLocation.id)
            .filter(models.WaterAlert.status == "CONFIRMED")
            .all()
        ):
            b = (loc.building or "").strip().lower()
            if any(rb in b or b in rb for rb in resolved_buildings):
                water_l += alert_excess_litres(alert)

    recent = [
        {
            "id": c.complaint_code or f"C-{c.id}",
            "db_id": c.id,
            "title": ((c.description or "").split("\n", 1)[0][:60] or c.category.replace("_", " ").title()),
            "place": f"{c.building} - {c.location_detail}" if c.location_detail else c.building,
            "category": c.category,
            "status": str(c.status).lower(),
            "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
            "image_url": _image_url(c.attachment_path),
        }
        for c in complaints[:5]
    ]

    return StudentHomeResponse(
        is_simulated=True,
        name=current_user.full_name or current_user.username or "Student",
        stats=StudentHomeStats(
            reports_filed=len(complaints),
            accepted=len(accepted),
            in_progress=len(in_progress),
            estimated_saving_kwh=round(kwh, 2),
        ),
        recent=recent,
        impact=StudentHomeImpact(
            electricity_kwh=round(kwh, 2),
            water_litres=round(water_l, 1),
            co2_kg=round(kwh * rates["emissions"], 2),
        ),
        data_source="simulated",
    )

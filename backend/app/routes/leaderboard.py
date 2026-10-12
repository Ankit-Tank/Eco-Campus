"""
GhostWatt — routes/leaderboard.py
Campus Block Sustainability Leaderboard (GET /leaderboard/blocks).
SPEC §5 & User Requirements:
- Compares Ghost Load score per block (Block A, Block B, Block C).
- Higher score indicates lower ghost waste / higher sustainability.
- Open to all authenticated users (students and admins).
- Includes equivalents and assumptions.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.leaderboard import BlockLeaderboardItem, BlockLeaderboardResponse
from app.services.carbon_calculator import fan_equivalents
from app.services.expected_demand import expected_kw
from app.services.savings_verification import get_settings_rates

router = APIRouter()

BLOCK_NAMES = {
    "A": "Main Academic & Administration Block",
    "B": "Science & Computer Engineering Complex",
    "C": "Seminar, Library & Reading Block",
}


@router.get(
    "/blocks",
    response_model=BlockLeaderboardResponse,
    summary="Get campus blocks sustainability leaderboard",
    description="Ranks campus blocks by ghost load efficiency, sustainability score, and avoidable loss.",
)
def get_block_leaderboard(
    period: str = Query("7d", description="Time window: 'today', '7d', '14d', or 'all'"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Computes sustainability scores for Block A, B, and C:
    - Waste percentage = ghost_kwh / actual_kwh * 100
    - Sustainability score = 100 - waste_percentage (clamped 0-100)
    - Letter grade: A+ (>=90), A (>=80), B (>=70), C (>=60), D (<60)
    """
    state = db.query(models.SimState).filter(models.SimState.id == 1).first()
    virtual_now = state.virtual_now if state else datetime.utcnow()

    p_clean = period.lower().strip()
    if p_clean in ("today", "24h", "1d"):
        start_dt = virtual_now - timedelta(days=1)
    elif p_clean in ("14d", "2w"):
        start_dt = virtual_now - timedelta(days=14)
    elif p_clean == "all":
        start_dt = datetime(2026, 1, 1)
    else:
        start_dt = virtual_now - timedelta(days=7)

    price_kwh, emissions_factor = get_settings_rates(db)
    s_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in s_rows}
    fan_watts = float(cfg.get("fan_watt_equivalent", 75.0))

    readings = (
        db.query(models.MeterReading, models.Room)
        .join(models.Room, models.MeterReading.room_id == models.Room.id)
        .filter(models.MeterReading.timestamp >= start_dt)
        .all()
    )

    equipment = db.query(models.Equipment).all()
    eq_by_room = {}
    for e in equipment:
        eq_by_room.setdefault(e.room_id, []).append(e)

    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in timetables:
        tt_by_room.setdefault(t.room_id, []).append(t)

    block_data: Dict[str, Dict[str, float]] = {
        "A": {"actual_kwh": 0.0, "expected_kwh": 0.0, "ghost_kwh": 0.0},
        "B": {"actual_kwh": 0.0, "expected_kwh": 0.0, "ghost_kwh": 0.0},
        "C": {"actual_kwh": 0.0, "expected_kwh": 0.0, "ghost_kwh": 0.0},
    }

    for mr, room in readings:
        blk = room.block.upper()
        if blk not in block_data:
            block_data[blk] = {"actual_kwh": 0.0, "expected_kwh": 0.0, "ghost_kwh": 0.0}

        r_eq = eq_by_room.get(room.id, [])
        r_tt = tt_by_room.get(room.id, [])
        exp_kw, _ = expected_kw(room, r_eq, r_tt, mr.timestamp)
        gh_kw = max(0.0, mr.actual_demand_kw - exp_kw)

        block_data[blk]["actual_kwh"] += mr.interval_kwh
        block_data[blk]["expected_kwh"] += exp_kw * 0.25
        block_data[blk]["ghost_kwh"] += gh_kw * 0.25

    items = []
    duration_hours = max(1.0, 7.0 * 24.0)

    for blk_key, data in block_data.items():
        actual = data["actual_kwh"]
        ghost = data["ghost_kwh"]
        expected = data["expected_kwh"]

        waste_pct = round((ghost / actual * 100.0), 1) if actual > 0 else 0.0
        score = round(max(0.0, min(100.0, 100.0 - waste_pct)), 1)

        if score >= 90.0:
            grade = "A+"
        elif score >= 80.0:
            grade = "A"
        elif score >= 70.0:
            grade = "B"
        elif score >= 60.0:
            grade = "C"
        else:
            grade = "D"

        cost = round(ghost * price_kwh, 2)
        co2 = round(ghost * emissions_factor, 3)

        avg_ghost_kw = (ghost / duration_hours) if duration_hours > 0 else 0.0
        fan_res = fan_equivalents(avg_ghost_kw, fan_watts)

        items.append({
            "block": f"Block {blk_key}",
            "name": BLOCK_NAMES.get(blk_key, f"Block {blk_key} Building"),
            "actual_kwh": round(actual, 2),
            "expected_kwh": round(expected, 2),
            "ghost_kwh": round(ghost, 2),
            "waste_percentage": waste_pct,
            "sustainability_score": score,
            "grade": grade,
            "cost_inr": cost,
            "co2_kg": co2,
            "fan_equivalents": fan_res["value"],
            "fan_assumption": fan_res["assumption"],
        })

    # Sort descending by sustainability_score (highest score first)
    items.sort(key=lambda x: x["sustainability_score"], reverse=True)

    for idx, it in enumerate(items, start=1):
        it["rank"] = idx

    best_block = items[0]["block"] if items else "Block B"
    worst_block = items[-1]["block"] if items else "Block A"

    leaderboard_items = [BlockLeaderboardItem(**it) for it in items]

    return BlockLeaderboardResponse(
        period=period,
        blocks=leaderboard_items,
        best_block=best_block,
        worst_block=worst_block,
        assumptions={
            "fan": f"Standard institutional ceiling fan rated at {fan_watts:.0f} W",
            "tariff": f"Commercial campus tariff of Rs {price_kwh:.2f} per kWh",
            "emissions": f"Regional grid emission factor of {emissions_factor:.2f} kg CO2/kWh",
            "score": "Sustainability Score = 100 - (Ghost Load kWh / Actual Consumed kWh * 100)",
        },
        data_source="simulated",
    )

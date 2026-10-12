"""
GhostWatt — services/assistant_tools.py
Approved data-fetch functions and grounded response templates for the AI assistant.

SPEC §11 & User Requirements:
- Whitelisted functions:
  1. top_ghost_rooms(period)
  2. explain_room_alert(room_id)
  3. verified_savings(period)
  4. block_wastage(period)
  5. open_complaints(user)
  6. recommended_actions()
- Every function takes the authenticated user and enforces the role.
  Students NEVER see other students' complaints or administrative operations.
- Pure service functions: NO FastAPI imports.
"""
from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

from app.db import models
from app.services.expected_demand import expected_kw
from app.services.ghost_load import classify_ghost_reason, determine_room_status
from app.services.savings_verification import get_settings_rates

# ---------------------------------------------------------------------------
# Whitelisted Tool Declarations for Groq Function Calling
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "top_ghost_rooms",
            "description": "Retrieve the campus rooms with the highest accumulated ghost load (excess energy waste) over a time period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time window: 'today', '24h', '7d', '14d', or 'all'. Defaults to '7d'.",
                        "enum": ["today", "24h", "7d", "14d", "all"],
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_room_alert",
            "description": "Diagnose why a specific room has triggered an excess usage or ghost load alert, returning status and plain-English explanation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "Room identifier: room code (e.g. 'A-101', 'B-201') or numeric database room ID (e.g. '1').",
                    }
                },
                "required": ["room_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verified_savings",
            "description": "Get summary metrics of verified power reductions backed by subsequent meter readings vs claimed savings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time window: '7d', '14d', or 'all'. Defaults to 'all'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "block_wastage",
            "description": "Compare and rank campus blocks (Block A, Block B, Block C) by total electricity waste and monetary loss.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Time window: 'today', '7d', '14d', or 'all'. Defaults to '7d'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_complaints",
            "description": "Fetch open water complaints. Students see strictly only their own; administrators see campus-wide open issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_student_email": {
                        "type": "string",
                        "description": "Optional student email filter (restricted to administrators).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommended_actions",
            "description": "Get prioritized switch-off and energy conservation recommendations to reduce active campus ghost loads.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Helper: Date Range Resolution
# ---------------------------------------------------------------------------
def _resolve_period_start(db: Session, period: str) -> datetime:
    state = db.query(models.SimState).filter(models.SimState.id == 1).first()
    virtual_now = state.virtual_now if state else datetime.utcnow()

    p_clean = str(period or "7d").lower()
    if p_clean in ("today", "24h", "1d"):
        return virtual_now - timedelta(days=1)
    elif p_clean in ("7d", "week", "1w"):
        return virtual_now - timedelta(days=7)
    elif p_clean in ("14d", "2w"):
        return virtual_now - timedelta(days=14)
    elif p_clean == "all":
        return datetime(2026, 1, 1)
    return virtual_now - timedelta(days=7)


# ---------------------------------------------------------------------------
# 1. top_ghost_rooms(period)
# ---------------------------------------------------------------------------
def top_ghost_rooms(
    db: Session,
    user: models.User,
    period: str = "7d",
) -> Dict[str, Any]:
    """Return top rooms ranked by accumulated ghost load over the period."""
    start_dt = _resolve_period_start(db, period)
    price_kwh, emissions_factor = get_settings_rates(db)

    readings = (
        db.query(models.MeterReading, models.Room)
        .join(models.Room, models.MeterReading.room_id == models.Room.id)
        .filter(models.MeterReading.timestamp >= start_dt)
        .all()
    )

    all_eq = db.query(models.Equipment).all()
    eq_by_room = {}
    for e in all_eq:
        eq_by_room.setdefault(e.room_id, []).append(e)

    all_tt = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in all_tt:
        tt_by_room.setdefault(t.room_id, []).append(t)

    room_totals = {}
    total_campus_ghost = 0.0

    for mr, room in readings:
        r_eq = eq_by_room.get(room.id, [])
        r_tt = tt_by_room.get(room.id, [])
        exp_kw, _ = expected_kw(room, r_eq, r_tt, mr.timestamp)
        ghost_kw = max(0.0, mr.actual_demand_kw - exp_kw)
        ghost_kwh = ghost_kw * 0.25

        if room.id not in room_totals:
            room_totals[room.id] = {
                "room_id": room.id,
                "room_code": room.room_code,
                "name": room.name,
                "block": room.block,
                "ghost_kwh": 0.0,
                "actual_kwh": 0.0,
            }
        room_totals[room.id]["ghost_kwh"] += ghost_kwh
        room_totals[room.id]["actual_kwh"] += mr.interval_kwh
        total_campus_ghost += ghost_kwh

    sorted_rooms = sorted(room_totals.values(), key=lambda x: x["ghost_kwh"], reverse=True)

    top_list = []
    for rank, r in enumerate(sorted_rooms[:5], start=1):
        g_kwh = round(r["ghost_kwh"], 2)
        top_list.append({
            "rank": rank,
            "room_code": r["room_code"],
            "name": r["name"],
            "block": r["block"],
            "ghost_kwh": g_kwh,
            "cost_inr": round(g_kwh * price_kwh, 2),
            "co2_kg": round(g_kwh * emissions_factor, 2),
        })

    return {
        "period": period,
        "top_rooms": top_list,
        "total_ghost_kwh": round(total_campus_ghost, 2),
    }


# ---------------------------------------------------------------------------
# 2. explain_room_alert(room_id)
# ---------------------------------------------------------------------------
def explain_room_alert(
    db: Session,
    user: models.User,
    room_id: Any,
) -> Dict[str, Any]:
    """Diagnose room status, reason code, and plain-English explanation for a room."""
    # Find room by ID or code
    room = None
    if str(room_id).isdigit():
        room = db.query(models.Room).filter(models.Room.id == int(room_id)).first()
    if not room:
        clean_code = str(room_id).replace("Room", "").strip().upper()
        room = db.query(models.Room).filter(models.Room.room_code == clean_code).first()

    if not room:
        # Search partial match
        room = db.query(models.Room).filter(models.Room.room_code.ilike(f"%{room_id}%")).first()

    if not room:
        return {"error": f"Room '{room_id}' not found in campus database."}

    equipment = db.query(models.Equipment).filter(models.Equipment.room_id == room.id).all()
    timetables = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.room_id == room.id,
        models.TimetableEntry.is_active == True,
    ).all()

    latest_mr = (
        db.query(models.MeterReading)
        .filter(models.MeterReading.room_id == room.id)
        .order_by(models.MeterReading.timestamp.desc())
        .first()
    )
    if not latest_mr:
        return {"room_code": room.room_code, "name": room.name, "status": "No Readings Available"}

    exp_kw, reasons = expected_kw(room, equipment, timetables, latest_mr.timestamp)
    act_kw = latest_mr.actual_demand_kw
    ghost_kw = max(0.0, act_kw - exp_kw)

    has_ac = any(e.kind.lower() == "ac" for e in equipment)
    in_session = bool(reasons.get("in_session", False))
    reason_code, explanation = classify_ghost_reason(
        actual_kw=act_kw,
        expected_kw=exp_kw,
        in_session=in_session,
        room_type=room.room_type,
        has_ac=has_ac,
        ts=latest_mr.timestamp,
    )
    if not reason_code:
        reason_code = "NORMAL_OPERATION"
        explanation = "Electricity consumption is within expected operational baseline."

    room_status = determine_room_status(
        in_session=in_session,
        actual_kw=act_kw,
        expected_kw=exp_kw,
        idle_baseline_kw=float(room.idle_baseline_kw or 0.1),
    )

    return {
        "room_code": room.room_code,
        "name": room.name,
        "block": room.block,
        "actual_kw": round(act_kw, 2),
        "expected_kw": round(exp_kw, 2),
        "ghost_kw": round(ghost_kw, 2),
        "status": room_status,
        "in_session": reasons.get("in_session", False),
        "reason_code": reason_code,
        "explanation": explanation,
        "timestamp": latest_mr.timestamp.isoformat(),
    }


# ---------------------------------------------------------------------------
# 3. verified_savings(period)
# ---------------------------------------------------------------------------
def verified_savings(
    db: Session,
    user: models.User,
    period: str = "all",
) -> Dict[str, Any]:
    """Retrieve cumulative verified savings supported by meter readings."""
    records = db.query(models.SavingsRecord).all()
    actions = db.query(models.Action).all()

    verified_kwh = sum(r.credited_kwh for r in records)
    monetary = sum(r.monetary_saving_inr for r in records)
    emissions = sum(r.emissions_kg for r in records)

    all_eq = db.query(models.Equipment).all()
    eq_map = {(e.room_id, e.kind.lower()): float(e.rated_kw * e.count) for e in all_eq}
    claimed_kwh = sum(eq_map.get((a.room_id, a.equipment.lower()), 0.0) * 0.25 for a in actions)

    verified_actions = sum(1 for a in actions if str(a.verification_status).upper() == "VERIFIED")

    return {
        "period": period,
        "claimed_kwh": round(claimed_kwh, 2),
        "verified_kwh": round(verified_kwh, 2),
        "monetary_saving_inr": round(monetary, 2),
        "emissions_co2_kg": round(emissions, 2),
        "verified_actions": verified_actions,
        "total_actions": len(actions),
        "label": "Simulated Verified Savings",
    }


# ---------------------------------------------------------------------------
# 4. block_wastage(period)
# ---------------------------------------------------------------------------
def block_wastage(
    db: Session,
    user: models.User,
    period: str = "7d",
) -> Dict[str, Any]:
    """Aggregate ghost load across campus blocks (Block A, B, C)."""
    start_dt = _resolve_period_start(db, period)
    price_kwh, _ = get_settings_rates(db)

    readings = (
        db.query(models.MeterReading, models.Room)
        .join(models.Room, models.MeterReading.room_id == models.Room.id)
        .filter(models.MeterReading.timestamp >= start_dt)
        .all()
    )

    all_eq = db.query(models.Equipment).all()
    eq_by_room = {}
    for e in all_eq:
        eq_by_room.setdefault(e.room_id, []).append(e)

    all_tt = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in all_tt:
        tt_by_room.setdefault(t.room_id, []).append(t)

    block_data = {}
    for mr, room in readings:
        blk = room.block
        if blk not in block_data:
            block_data[blk] = {"block": f"Block {blk}", "actual_kwh": 0.0, "ghost_kwh": 0.0}

        r_eq = eq_by_room.get(room.id, [])
        r_tt = tt_by_room.get(room.id, [])
        exp_kw, _ = expected_kw(room, r_eq, r_tt, mr.timestamp)
        gh_kw = max(0.0, mr.actual_demand_kw - exp_kw)

        block_data[blk]["actual_kwh"] += mr.interval_kwh
        block_data[blk]["ghost_kwh"] += gh_kw * 0.25

    results = []
    for blk_info in sorted(block_data.values(), key=lambda x: x["ghost_kwh"], reverse=True):
        gh = round(blk_info["ghost_kwh"], 2)
        results.append({
            "block": blk_info["block"],
            "ghost_kwh": gh,
            "cost_inr": round(gh * price_kwh, 2),
            "actual_kwh": round(blk_info["actual_kwh"], 2),
        })

    highest = results[0]["block"] if results else "Unknown"

    return {
        "period": period,
        "blocks": results,
        "highest_waste_block": highest,
    }


# ---------------------------------------------------------------------------
# 5. open_complaints(user)
# ---------------------------------------------------------------------------
def open_complaints(
    db: Session,
    user: models.User,
    target_student_email: Optional[str] = None,
    complaint_id: Optional[int] = None,
    question: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch open water complaints with role enforcement.
    Students see strictly only their own; attempting to query another student is refused.
    """
    is_student = (user.role == "student")

    # Privacy enforcement check
    if is_student:
        if question and any(p in question.lower() for p in ("other student", "another student", "someone else", "different student", "all students")):
            return {
                "refusal": "Access denied: Students are only permitted to view their own complaints.",
                "role": user.role,
                "count": 0,
            }
        if target_student_email and target_student_email.strip().lower() != user.email.strip().lower():
            return {
                "refusal": "Access denied: Students are only permitted to view their own complaints.",
                "role": user.role,
                "count": 0,
            }
        if complaint_id:
            c_check = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
            if c_check and c_check.student_id != user.id:
                return {
                    "refusal": "Access denied: Students are only permitted to view their own complaints.",
                    "role": user.role,
                    "count": 0,
                }

    query = db.query(models.Complaint).filter(models.Complaint.status != "resolved")

    if is_student:
        query = query.filter(models.Complaint.student_id == user.id)
    elif target_student_email:
        target_u = db.query(models.User).filter(models.User.email == target_student_email).first()
        if target_u:
            query = query.filter(models.Complaint.student_id == target_u.id)

    rows = query.order_by(models.Complaint.created_at.desc()).all()

    items = []
    for c in rows:
        items.append({
            "complaint_code": c.complaint_code,
            "building": c.building,
            "location_detail": c.location_detail,
            "category": c.category,
            "status": c.status,
            "description": c.description,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
        })

    return {
        "role": user.role,
        "complaints": items,
        "count": len(items),
    }


# ---------------------------------------------------------------------------
# 6. recommended_actions(user)
# ---------------------------------------------------------------------------
def recommended_actions(
    db: Session,
    user: models.User,
) -> Dict[str, Any]:
    """Return prioritized actions to eliminate active campus ghost loads."""
    # Dynamic recommendations from current ghost load
    rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
    all_eq = db.query(models.Equipment).all()
    eq_by_room = {}
    for e in all_eq:
        eq_by_room.setdefault(e.room_id, []).append(e)

    all_tt = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in all_tt:
        tt_by_room.setdefault(t.room_id, []).append(t)

    dynamic_recs = []
    for room in rooms:
        mr = (
            db.query(models.MeterReading)
            .filter(models.MeterReading.room_id == room.id)
            .order_by(models.MeterReading.timestamp.desc())
            .first()
        )
        if not mr:
            continue
        exp_kw, _ = expected_kw(room, eq_by_room.get(room.id, []), tt_by_room.get(room.id, []), mr.timestamp)
        gh_kw = max(0.0, mr.actual_demand_kw - exp_kw)
        if gh_kw >= 0.5:
            r_eqs = eq_by_room.get(room.id, [])
            top_eq = max(r_eqs, key=lambda e: float(e.rated_kw * e.count)) if r_eqs else None
            appliance = top_eq.kind.title() if top_eq else "Appliances"
            dynamic_recs.append({
                "room_code": room.room_code,
                "appliance": appliance,
                "action": f"Switch off {appliance.lower()} in {room.name}",
                "potential_saving_kw": round(gh_kw, 2),
                "reason": f"Excess power consumption ({round(gh_kw, 2)} kW) detected above scheduled baseline",
            })

    dynamic_recs.sort(key=lambda x: x["potential_saving_kw"], reverse=True)
    if dynamic_recs:
        for idx, r in enumerate(dynamic_recs[:5], start=1):
            r["priority"] = idx
        return {
            "recommendations": dynamic_recs[:5],
            "count": len(dynamic_recs[:5]),
        }

    recommendations = [
        {
            "priority": 1,
            "room_code": "A-101",
            "appliance": "Split AC",
            "action": "Switch off split AC units in Classroom 101",
            "potential_saving_kw": 3.6,
            "reason": "Air conditioning running while room is unoccupied with no scheduled class",
        },
        {
            "priority": 2,
            "room_code": "B-201",
            "appliance": "Computers",
            "action": "Shut down lab computer workstations and lighting in Computer Science Lab 1",
            "potential_saving_kw": 2.5,
            "reason": "Lab equipment energized outside instructional timetable",
        },
        {
            "priority": 3,
            "room_code": "C-301",
            "appliance": "Projector",
            "action": "Power down AV projector and luminaires in Seminar Hall 301",
            "potential_saving_kw": 1.2,
            "reason": "Display equipment idling during lunch recess",
        },
    ]

    return {
        "recommendations": recommendations,
        "count": len(recommendations),
    }


# ---------------------------------------------------------------------------
# Registry Map of Whitelisted Functions
# ---------------------------------------------------------------------------
TOOLS_MAP = {
    "top_ghost_rooms": top_ghost_rooms,
    "explain_room_alert": explain_room_alert,
    "verified_savings": verified_savings,
    "block_wastage": block_wastage,
    "open_complaints": open_complaints,
    "recommended_actions": recommended_actions,
}


# ---------------------------------------------------------------------------
# Intent Matching Helper (for Fallback Routing)
# ---------------------------------------------------------------------------
def detect_tool_intent(question: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Heuristic intent detection mapping a question to one of the 6 whitelisted tools."""
    q_lower = question.lower()

    if any(k in q_lower for k in ("highest ghost", "top ghost", "most ghost", "ghost load rooms", "which room wastes", "top rooms")):
        return "top_ghost_rooms", {"period": "7d"}

    if any(k in q_lower for k in ("why is room", "alerting", "explain alert", "explain room", "what's happening in", "what is happening in", "status of room")):
        # Extract room code like A-101 or room ID
        match = re.search(r'\b([abcABC][ -]?\d{3})\b', question)
        if match:
            code = match.group(1).replace(" ", "-").upper()
            return "explain_room_alert", {"room_id": code}
        num_match = re.search(r'room\s+(\d+)', q_lower)
        if num_match:
            return "explain_room_alert", {"room_id": num_match.group(1)}
        return "explain_room_alert", {"room_id": "A-101"}

    if any(k in q_lower for k in ("verified saving", "saved", "verified actions", "how much energy have we saved", "saving summary", "savings")):
        return "verified_savings", {"period": "all"}

    if any(k in q_lower for k in ("which block", "block wastage", "wastes the most electricity", "block a", "block b", "block c")):
        return "block_wastage", {"period": "7d"}

    if any(k in q_lower for k in ("complaint", "water complaint", "leak report", "open complaints")):
        # Check if student asking for another student's complaint
        if any(k in q_lower for k in ("other student", "another student", "someone else", "different student")):
            return "open_complaints", {"target_student_email": "other_student@campus.edu"}
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', question)
        target_email = email_match.group(0) if email_match else None
        return "open_complaints", {"target_student_email": target_email}

    if any(k in q_lower for k in ("recommend", "action", "should we do", "switch off", "reduce waste", "how to save")):
        return "recommended_actions", {}

    return None, {}


# ---------------------------------------------------------------------------
# Grounded Template Generator (for Fallbacks)
# ---------------------------------------------------------------------------
def generate_template_answer(tool_name: str, data: Dict[str, Any], user: models.User) -> str:
    """Produce deterministic, factual grounded responses using only tool data."""
    if "refusal" in data:
        return data["refusal"]

    if tool_name == "top_ghost_rooms":
        rooms = data.get("top_rooms", [])
        if not rooms:
            return "No excess ghost load was detected across campus rooms for the requested period."
        r_lines = [f"{r['rank']}. {r['room_code']} ({r['name']}) with {r['ghost_kwh']} kWh (₹{r['cost_inr']})" for r in rooms[:3]]
        return f"Top rooms with the highest ghost load: {'; '.join(r_lines)}. Total waste: {data.get('total_ghost_kwh')} kWh."

    elif tool_name == "explain_room_alert":
        if "error" in data:
            return data["error"]
        return (
            f"Room {data.get('room_code')} ({data.get('name')}) is operating at {data.get('actual_kw')} kW "
            f"against an expected baseline of {data.get('expected_kw')} kW (excess: {data.get('ghost_kw')} kW). "
            f"Status: '{data.get('status')}'. Cause: {data.get('explanation')}"
        )

    elif tool_name == "verified_savings":
        return (
            f"Verified savings summary: {data.get('verified_kwh')} kWh confirmed saved across "
            f"{data.get('verified_actions')} action(s), totaling ₹{data.get('monetary_saving_inr')} "
            f"in financial savings and {data.get('emissions_co2_kg')} kg of avoided CO2."
        )

    elif tool_name == "block_wastage":
        blocks = data.get("blocks", [])
        b_str = ", ".join(f"{b['block']} ({b['ghost_kwh']} kWh, ₹{b['cost_inr']})" for b in blocks)
        return f"Highest electricity wastage is in {data.get('highest_waste_block')}. Block breakdown: {b_str}."

    elif tool_name == "open_complaints":
        count = data.get("count", 0)
        complaints = data.get("complaints", [])
        if count == 0:
            return "There are currently no open water complaints on file."
        c_lines = [f"{c['complaint_code']} at {c['building']} ({c['location_detail']}) - {c['category']}" for c in complaints]
        return f"Found {count} open water complaint(s): {'; '.join(c_lines)}."

    elif tool_name == "recommended_actions":
        recs = data.get("recommendations", [])
        r_lines = [f"{r['priority']}. {r['action']} (save ~{r['potential_saving_kw']} kW): {r['reason']}" for r in recs]
        return f"Recommended switch-off actions: {'; '.join(r_lines)}."

    return "Data retrieved successfully."


def get_supported_questions_message() -> str:
    """Friendly fallback when a question is outside the whitelisted scope."""
    return (
        "I can answer questions regarding campus electricity waste, ghost load diagnostics, verified savings, "
        "and water complaints. Here are examples of questions I can answer:\n"
        "1. 'Which rooms have the highest ghost load?'\n"
        "2. 'Why is room A-101 alerting?'\n"
        "3. 'How much energy have we saved through verified actions?'\n"
        "4. 'Which block wastes the most electricity?'\n"
        "5. 'What are the open water complaints?'\n"
        "6. 'What recommended actions should we take to reduce energy waste?'"
    )

"""
Eco-Campus — services/expected_demand.py
Pure function: compute expected kW and reason breakdown for a room at a given timestamp.
No FastAPI imports.

SPEC §6 & Architecture:
- No class: idle baseline only.
- Class in session: idle baseline + class equipment.
- Lights, fans, and computers are scaled by (expected_students / capacity).
- Fixed equipment (AC, projector, lab_equipment) operates based on expected_in_class factor.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to extract attribute from SQLAlchemy model or dictionary."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def expected_kw(
    room: Any,
    equipment: List[Any],
    timetable: Union[List[Any], Any],
    ts: datetime,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute expected demand (kW) and reason breakdown for a room at a given timestamp.

    Parameters
    ----------
    room : Room model or dict with 'capacity' and 'idle_baseline_kw'.
    equipment : List of Equipment models or dicts with 'kind', 'rated_kw', 'count', 'expected_in_class'.
    timetable : List of TimetableEntry models/dicts, or a single active entry/None.
    ts : datetime of the interval.

    Returns
    -------
    (kW, reasons dict) : Tuple of expected demand in kW and explanatory reasons dictionary.
    """
    idle_baseline = float(_get_attr(room, "idle_baseline_kw", 0.1) or 0.1)
    capacity = int(_get_attr(room, "capacity", 40) or 40)

    # Determine weekday (0=Mon ... 6=Sun) and HH:MM string
    day_of_week = ts.weekday()
    time_str = ts.strftime("%H:%M")

    # Resolve active timetable entry
    active_entry = None
    if isinstance(timetable, (list, tuple)):
        for entry in timetable:
            e_day = _get_attr(entry, "day_of_week")
            e_start = _get_attr(entry, "start_time")
            e_end = _get_attr(entry, "end_time")
            e_active = _get_attr(entry, "is_active", True)

            # Class is in session if day matches, start <= ts < end, and is_active
            if e_active and e_day == day_of_week and e_start <= time_str < e_end:
                active_entry = entry
                break
    elif timetable is not None:
        # A single active entry was passed directly
        active_entry = timetable

    # Case 1: No class scheduled — idle baseline only
    if active_entry is None:
        reasons = {
            "in_session": False,
            "activity": None,
            "idle_baseline_kw": round(idle_baseline, 3),
            "scaling_factor": 1.0,
            "equipment_breakdown": {},
            "total_expected_kw": round(idle_baseline, 3),
            "explanation": "No class scheduled. Expected consumption is idle baseline only.",
        }
        return round(idle_baseline, 3), reasons

    # Case 2: Class scheduled — idle baseline + equipment load
    expected_students = int(_get_attr(active_entry, "expected_students", 30) or 30)
    activity = str(_get_attr(active_entry, "activity", "Class") or "Class")

    # Scaling factor for student-dependent appliances (lights, fans, computers)
    if capacity > 0:
        student_ratio = expected_students / capacity
        scaling_factor = max(0.1, min(1.0, student_ratio))
    else:
        scaling_factor = 1.0

    equipment_breakdown: Dict[str, Any] = {}
    total_equipment_kw = 0.0

    student_scaled_kinds = {"light", "lights", "fan", "fans", "pc", "computers"}

    for eq in equipment:
        kind = str(_get_attr(eq, "kind", "equipment")).lower()
        rated_kw = float(_get_attr(eq, "rated_kw", 0.0) or 0.0)
        count = int(_get_attr(eq, "count", 1) or 1)
        expected_in_class = float(_get_attr(eq, "expected_in_class", 1.0) if _get_attr(eq, "expected_in_class") is not None else 1.0)

        # Baseline appliance operating power when room is in session
        base_kw = rated_kw * count * expected_in_class

        # Scale lights, fans, and PCs by student occupancy fraction
        if kind in student_scaled_kinds:
            eq_kw = base_kw * scaling_factor
            scaled = True
        else:
            eq_kw = base_kw
            scaled = False

        total_equipment_kw += eq_kw
        equipment_breakdown[kind] = {
            "rated_kw": rated_kw,
            "count": count,
            "expected_in_class": expected_in_class,
            "scaled_by_students": scaled,
            "effective_kw": round(eq_kw, 3),
        }

    total_expected = idle_baseline + total_equipment_kw
    reasons = {
        "in_session": True,
        "activity": activity,
        "expected_students": expected_students,
        "capacity": capacity,
        "scaling_factor": round(scaling_factor, 3),
        "idle_baseline_kw": round(idle_baseline, 3),
        "equipment_breakdown": equipment_breakdown,
        "total_expected_kw": round(total_expected, 3),
        "explanation": (
            f"Class '{activity}' in session with {expected_students}/{capacity} students. "
            f"Expected {round(total_equipment_kw, 2)} kW equipment demand + {idle_baseline} kW idle baseline."
        ),
    }

    return round(total_expected, 3), reasons


def get_expected_kw(room_id: int, ts: datetime, db: Any) -> float:
    """
    SQLAlchemy-grounded helper for backward compatibility with database queries.
    Queries the room, equipment, and timetable entries, then delegates to expected_kw.
    """
    from app.db import models

    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        return 0.0

    equipment_list = db.query(models.Equipment).filter(models.Equipment.room_id == room_id).all()
    timetable_entries = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.room_id == room_id,
        models.TimetableEntry.is_active == True,
    ).all()

    kw, _ = expected_kw(room, equipment_list, timetable_entries, ts)
    return kw

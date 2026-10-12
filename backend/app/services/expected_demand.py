"""
GhostWatt — services/expected_demand.py
Pure function: compute expected kW for a room at a given datetime.
Reads from Timetable + Room equipment.
NO FastAPI imports.
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models


def get_expected_kw(room_id: int, ts: datetime, db: Session) -> float:
    """
    Return the expected demand (kW) for the given room at the given timestamp.
    Uses the timetable and room equipment configuration.
    Falls back to idle_baseline_kw when no class is scheduled.
    """
    room: models.Room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        return 0.0

    day = ts.weekday()          # 0=Mon … 6=Sun
    time_str = ts.strftime("%H:%M")

    entry = (
        db.query(models.TimetableEntry)
        .filter(
            models.TimetableEntry.room_id == room_id,
            models.TimetableEntry.day_of_week == day,
            models.TimetableEntry.start_time <= time_str,
            models.TimetableEntry.end_time > time_str,
            models.TimetableEntry.is_active == True,
        )
        .first()
    )

    idle = float(room.idle_baseline_kw or 0.1)
    if entry is None:
        # No scheduled class — return idle baseline
        return idle

    # Class is scheduled — sum up idle + equipment expected to operate
    if room.equipment:
        expected = idle + sum(
            eq.rated_kw * eq.count * (eq.expected_in_class if eq.expected_in_class is not None else 1.0)
            for eq in room.equipment
        )
    else:
        equipment: dict = json.loads(room.equipment_config or "{}")
        expected = idle + sum(equipment.values())

    return max(0.0, float(expected))

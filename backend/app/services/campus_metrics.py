"""
Eco-Campus - services/campus_metrics.py
Reusable, DB-backed aggregation helpers shared by the dashboard endpoints.
Pure service code (no FastAPI imports).
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db import models
from app.services.expected_demand import expected_kw

_ROOM_CODE_RE = re.compile(r"\b([A-Z]{1,3}-\d{2,4})\b")


class ExpectedCalculator:
    """Pre-loads rooms / equipment / timetables once and caches expected kW per weekly time slot."""

    def __init__(self, db: Session):
        self.rooms: Dict[int, models.Room] = {r.id: r for r in db.query(models.Room).all()}
        self.equipment: Dict[int, List[models.Equipment]] = {}
        for eq in db.query(models.Equipment).all():
            self.equipment.setdefault(eq.room_id, []).append(eq)
        self.timetable: Dict[int, List[models.TimetableEntry]] = {}
        for tt in db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all():  # noqa: E712
            self.timetable.setdefault(tt.room_id, []).append(tt)
        self._cache: Dict[Tuple[int, int, str], float] = {}

    def kw(self, room_id: int, ts: datetime) -> float:
        key = (room_id, ts.weekday(), ts.strftime("%H:%M"))
        if key not in self._cache:
            room = self.rooms.get(room_id)
            if room is None:
                self._cache[key] = 0.0
            else:
                value, _ = expected_kw(room, self.equipment.get(room_id, []), self.timetable.get(room_id, []), ts)
                self._cache[key] = value
        return self._cache[key]


def get_rates(db: Session) -> Dict[str, float]:
    cfg = {s.key: s.value for s in db.query(models.Setting).all()}

    def f(key: str, default: float) -> float:
        try:
            return float(cfg.get(key, default))
        except (TypeError, ValueError):
            return default

    return {
        "price": f("electricity_price_per_kwh", 8.50),
        "emissions": f("emissions_factor_kg_per_kwh", 0.71),
        "fan_watts": f("fan_watt_equivalent", 75.0),
        "bucket_litres": f("bucket_litres", 15.0),
    }


def room_codes_in_text(text: Optional[str]) -> List[str]:
    return list({m.group(1).upper() for m in _ROOM_CODE_RE.finditer((text or "").upper())})


def alert_excess_litres(alert: models.WaterAlert) -> float:
    hours = max(1.0, (alert.window_end - alert.window_start).total_seconds() / 3600.0)
    return max(0.0, (alert.avg_flow_lph - alert.baseline_lph) * hours)

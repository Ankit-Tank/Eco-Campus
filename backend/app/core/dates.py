"""
GhostWatt - core/dates.py
Shared helpers for query-string dates and the simulation clock.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models

DEFAULT_SIM_START = datetime(2026, 10, 12, 0, 0, 0)

PERIOD_DAYS = {
    "today": 1, "day": 1, "24h": 1, "1d": 1,
    "week": 7, "7d": 7,
    "14d": 14, "2w": 14,
    "30d": 30, "month": 30,
}


def parse_dt(value: Optional[str], field: str = "date", end_of_day: bool = False) -> Optional[datetime]:
    """
    Parse an ISO date / datetime query value. Raises HTTP 422 (instead of silently ignoring it).
    With end_of_day=True a date-only value ("2026-10-12") means the END of that day, so a
    "to" date includes its whole last day.
    """
    if value is None or str(value).strip() == "":
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid '{field}' value '{value}'. Use ISO format, e.g. 2026-10-12 or 2026-10-12T08:30:00.",
        )
    dt = dt.replace(tzinfo=None) if dt.tzinfo else dt
    if end_of_day and len(str(value).strip()) == 10:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


def sim_now(db: Session) -> datetime:
    """Current virtual (simulation) time."""
    state = db.query(models.SimState).filter(models.SimState.id == 1).first()
    return state.virtual_now if state else DEFAULT_SIM_START


def ordered_range(start: Optional[datetime], end: Optional[datetime]) -> None:
    if start and end and start > end:
        raise HTTPException(
            status_code=422,
            detail="'from' must not be later than 'to'.",
        )


def resolve_period(db: Session, period: Optional[str]) -> Tuple[Optional[datetime], datetime]:
    """
    Turn a period keyword into (start, end) anchored on the simulation clock.
    'all' -> (None, virtual_now). Unknown keywords raise HTTP 422.
    """
    end = sim_now(db)
    key = (period or "7d").lower().strip()
    if key == "all":
        return None, end
    if key not in PERIOD_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Use one of: today, day, week, 7d, 14d, 30d, month, all.",
        )
    return end - timedelta(days=PERIOD_DAYS[key]), end

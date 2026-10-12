"""
GhostWatt — services/savings_verification.py
Pure service functions for the Verified Savings Meter.

SPEC §8 & Requirements:
- Pre-window and post-window average demand computation.
- Verified reduction = min(max(0, pre_avg - post_avg), max(0, pre_avg - expected_kw)).
- Credited kWh = reduction * 0.25 per qualifying 15-minute interval.
- Status: VERIFIED, PARTIAL, NOT_VERIFIED, PENDING.
- Never credit when there is no reduction.
- Never credit a drop caused by a class ending (detected when pre was in session and post is not).
- Prevent double counting with UNIQUE(action_id, interval_start) and an explicit code check.
- Monetary and CO2 savings computed using runtime settings.
- Pure service functions: NO FastAPI imports.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models
from app.services.expected_demand import expected_kw


def get_settings_rates(db: Session) -> Tuple[float, float]:
    """
    Retrieve electricity price per kWh and emissions factor (kg CO2 per kWh) from settings.
    Falls back to default demo values if settings table entries are absent.
    """
    price_setting = db.query(models.Setting).filter(models.Setting.key == "electricity_price_per_kwh").first()
    co2_setting = db.query(models.Setting).filter(models.Setting.key == "emissions_factor_kg_per_kwh").first()

    try:
        price = float(price_setting.value) if price_setting and price_setting.value else 8.50
    except (ValueError, TypeError):
        price = 8.50

    try:
        emissions = float(co2_setting.value) if co2_setting and co2_setting.value else 0.71
    except (ValueError, TypeError):
        emissions = 0.71

    return price, emissions


def get_window_average_kw(room_id: int, start: datetime, end: datetime, db: Session) -> float:
    """Return mean actual_demand_kw for a room over [start, end]."""
    readings = (
        db.query(models.MeterReading)
        .filter(
            models.MeterReading.room_id == room_id,
            models.MeterReading.timestamp >= start,
            models.MeterReading.timestamp <= end,
        )
        .all()
    )
    if not readings:
        return 0.0
    return sum(r.actual_demand_kw for r in readings) / len(readings)


def calculate_savings_reduction(
    pre_avg_kw: float,
    post_avg_kw: float,
    expected_kw_val: float,
    class_ended: bool,
    claimed_kw: float = 0.0,
) -> Tuple[float, float, str]:
    """
    Core mathematical calculation of power reduction and credited energy:
    - If class ended: drop is attributable to timetable schedule change, not the action.
    - reduction = min(max(0, pre_avg - post_avg), max(0, pre_avg - expected_kw))
    - credited_kwh = reduction * 0.25 per 15-minute interval.
    - Status: VERIFIED, PARTIAL, NOT_VERIFIED.

    Returns (reduction_kw, credited_kwh, status).
    """
    if class_ended:
        return 0.0, 0.0, "NOT_VERIFIED"

    observed_drop = max(0.0, pre_avg_kw - post_avg_kw)
    excess_pre = max(0.0, pre_avg_kw - expected_kw_val)
    reduction = min(observed_drop, excess_pre)
    reduction = round(reduction, 3)

    if reduction <= 0.0:
        return 0.0, 0.0, "NOT_VERIFIED"

    credited_kwh = round(reduction * 0.25, 4)

    # Status classification: PARTIAL if reduction < 80% of claimed appliance rating
    if claimed_kw > 0 and reduction < 0.8 * claimed_kw:
        status = "PARTIAL"
    else:
        status = "VERIFIED"

    return reduction, credited_kwh, status


def verify_action(
    action: models.Action,
    db: Session,
    window_minutes: int = 15,
    current_ts: Optional[datetime] = None,
) -> Optional[models.SavingsRecord]:
    """
    Perform pre/post window verification for a single corrective action.

    1. Checks if the post window has closed.
    2. Gathers pre-action and post-action meter readings.
    3. Evaluates room schedule to ensure drop was not caused by a class ending.
    4. Applies the reduction formula and rate calculation.
    5. Prevents double counting via in-code check before persisting SavingsRecord.
    6. Updates action.verification_status to VERIFIED, PARTIAL, or NOT_VERIFIED.

    Returns the created or existing SavingsRecord, or None if post window has not closed.
    """
    # Determine the reference simulation timestamp
    if current_ts is None:
        state = db.query(models.SimState).filter(models.SimState.id == 1).first()
        current_ts = state.virtual_now if state else datetime.now(timezone.utc).replace(tzinfo=None)

    action_ts = action.timestamp
    post_end = action_ts + timedelta(minutes=window_minutes)

    # 1. Post window check: cannot verify until current_ts >= post_end
    if current_ts < post_end:
        return None

    interval_start = action_ts

    # 2. Check for duplicate record in code before doing work
    existing_rec = (
        db.query(models.SavingsRecord)
        .filter(
            models.SavingsRecord.action_id == action.id,
            models.SavingsRecord.interval_start == interval_start,
        )
        .first()
    )
    if existing_rec is not None:
        return existing_rec

    # 3. Post-action readings (first full interval after action)
    post_readings = (
        db.query(models.MeterReading)
        .filter(
            models.MeterReading.room_id == action.room_id,
            models.MeterReading.timestamp > action_ts,
            models.MeterReading.timestamp <= post_end,
        )
        .order_by(models.MeterReading.timestamp.asc())
        .all()
    )
    if not post_readings:
        return None

    # 4. Pre-action readings (interval(s) before the action)
    pre_start = action_ts - timedelta(minutes=window_minutes)
    pre_readings = (
        db.query(models.MeterReading)
        .filter(
            models.MeterReading.room_id == action.room_id,
            models.MeterReading.timestamp <= action_ts,
            models.MeterReading.timestamp >= pre_start,
        )
        .order_by(models.MeterReading.timestamp.desc())
        .all()
    )
    if not pre_readings:
        # Fallback: most recent reading at or before action_ts
        last_mr = (
            db.query(models.MeterReading)
            .filter(
                models.MeterReading.room_id == action.room_id,
                models.MeterReading.timestamp <= action_ts,
            )
            .order_by(models.MeterReading.timestamp.desc())
            .first()
        )
        pre_readings = [last_mr] if last_mr else []

    pre_avg = sum(r.actual_demand_kw for r in pre_readings) / len(pre_readings) if pre_readings else 0.0
    post_avg = sum(r.actual_demand_kw for r in post_readings) / len(post_readings)

    # 5. Room context: expected demand and class session status
    room = db.query(models.Room).filter(models.Room.id == action.room_id).first()
    equipment_list = db.query(models.Equipment).filter(models.Equipment.room_id == action.room_id).all()
    timetable_entries = db.query(models.TimetableEntry).filter(
        models.TimetableEntry.room_id == action.room_id,
        models.TimetableEntry.is_active == True,
    ).all()

    expected_pre_kw, pre_reasons = expected_kw(room, equipment_list, timetable_entries, action_ts)
    first_post_ts = post_readings[0].timestamp
    expected_post_kw, post_reasons = expected_kw(room, equipment_list, timetable_entries, first_post_ts)

    pre_in_session = bool(pre_reasons.get("in_session", False))
    post_in_session = bool(post_reasons.get("in_session", False))

    # Guard: never credit a drop caused by a class ending
    class_ended = pre_in_session and not post_in_session

    # Find claimed appliance rating
    target_eq = next((e for e in equipment_list if e.kind.lower() == action.equipment.lower()), None)
    claimed_kw = float(target_eq.rated_kw * target_eq.count) if target_eq else 0.0

    # Compute reduction, credited kWh, and verification status
    reduction_kw, credited_kwh, status = calculate_savings_reduction(
        pre_avg_kw=pre_avg,
        post_avg_kw=post_avg,
        expected_kw_val=expected_pre_kw,
        class_ended=class_ended,
        claimed_kw=claimed_kw,
    )

    # Financial & Carbon metrics using system settings
    price_per_kwh, emissions_factor = get_settings_rates(db)
    monetary = round(credited_kwh * price_per_kwh, 2)
    emissions = round(credited_kwh * emissions_factor, 4)

    record = models.SavingsRecord(
        action_id=action.id,
        interval_start=interval_start,
        pre_avg_kw=round(pre_avg, 3),
        post_avg_kw=round(post_avg, 3),
        reduction_kw=round(reduction_kw, 3),
        credited_kwh=round(credited_kwh, 4),
        monetary_saving_inr=monetary,
        emissions_kg=emissions,
        verification_status=status,
        is_simulated=True,
    )
    db.add(record)
    setattr(action, "verification_status", status)
    db.commit()
    db.refresh(record)

    return record


def verify_all_pending_actions(
    db: Session,
    current_ts: Optional[datetime] = None,
) -> List[models.SavingsRecord]:
    """
    Find all actions with status PENDING and verify those whose post-action window has closed.
    Executed automatically on each simulation tick.
    """
    pending = (
        db.query(models.Action)
        .filter(models.Action.verification_status.in_(["PENDING", "pending"]))
        .all()
    )
    verified_records: List[models.SavingsRecord] = []
    for act in pending:
        rec = verify_action(act, db, window_minutes=15, current_ts=current_ts)
        if rec is not None:
            verified_records.append(rec)
    return verified_records

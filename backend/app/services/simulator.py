"""
Eco-Campus — services/simulator.py
Simulation execution engine: virtual clock, equipment state evaluation,
15-minute interval ticking, and automated meter & water telemetry persistence.

SPEC §7:
- Virtual clock stored and tracked in sim_state (id=1).
- tick() advances virtual_now by one 15-minute interval.
- Generates meter readings from the equipment state model:
    actual = idle baseline + sum(ON equipment rated kW) + noise
- Evaluates active timetable schedules and applies scripted ghost load scenarios.
- Persists meter readings and hourly water readings to SQLite database.
- Pure service functions: NO FastAPI imports.
"""
from datetime import datetime, timedelta
import random
import threading
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.db import models
from app.services.expected_demand import expected_kw
from app.services.ghost_load import (
    calculate_ghost_load_kw,
    classify_ghost_reason,
    determine_room_status,
)
from app.services.savings_verification import verify_all_pending_actions
from app.services.water_analysis import analyze_night_flow

# ---------------------------------------------------------------------------
# In-memory interactive appliance overrides (SPEC §7)
# Maps room_code -> {equipment_kind: bool (True = forced ON, False = forced OFF)}
# ---------------------------------------------------------------------------
_appliance_state: Dict[str, Dict[str, bool]] = {}

# tick() can be called by the background clock AND by POST /sim/tick at the same moment.
# Serialising it keeps the virtual clock and the stored readings consistent.
_tick_lock = threading.Lock()


def restore_overrides_from_actions(db: Session, lookback_hours: int = 24) -> int:
    """
    The interactive appliance overrides live in memory. After a server restart, re-apply the
    switch-offs recorded in the actions table (within the last `lookback_hours` of simulated time)
    so a restart does not silently turn a switched-off appliance back on.
    """
    state = get_or_create_sim_state(db)
    since = state.virtual_now - timedelta(hours=lookback_hours)
    restored = 0
    for act in (
        db.query(models.Action)
        .filter(models.Action.action_type == "switch_off", models.Action.timestamp >= since, models.Action.timestamp <= state.virtual_now)
        .all()
    ):
        room = db.query(models.Room).filter(models.Room.id == act.room_id).first()
        if room and act.equipment:
            set_appliance(room.room_code, act.equipment.lower(), False)
            restored += 1
    return restored


def get_room_state(room_code: str) -> Dict[str, bool]:
    """Return in-memory appliance states for a room."""
    return dict(_appliance_state.get(room_code, {}))


def set_appliance(room_code: str, equipment: str, on: bool) -> Dict[str, bool]:
    """Explicitly force an appliance state ON or OFF."""
    if room_code not in _appliance_state:
        _appliance_state[room_code] = {}
    _appliance_state[room_code][equipment.lower()] = on
    return dict(_appliance_state[room_code])


def toggle_appliance(room_code: str, equipment: str) -> bool:
    """Toggle current appliance state and return new state."""
    eq_clean = equipment.lower()
    current = _appliance_state.get(room_code, {}).get(eq_clean, True)
    new_state = not current
    set_appliance(room_code, eq_clean, new_state)
    return new_state


def get_all_states() -> Dict[str, Dict[str, bool]]:
    """Return all manual appliance overrides."""
    return {k: dict(v) for k, v in _appliance_state.items()}


def clear_appliance_states() -> None:
    """Reset all interactive appliance overrides."""
    _appliance_state.clear()


# ---------------------------------------------------------------------------
# Simulation State (sim_state table row id=1)
# ---------------------------------------------------------------------------
def get_or_create_sim_state(db: Session) -> models.SimState:
    """Retrieve the single-row simulation control record, creating it if absent."""
    state = db.query(models.SimState).filter(models.SimState.id == 1).first()
    if state is None:
        state = models.SimState(
            id=1,
            virtual_now=datetime(2026, 10, 12, 0, 0, 0),
            speed=1.0,
            running=False,
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def set_sim_running(db: Session, running: bool) -> models.SimState:
    """Start or pause the simulation clock."""
    state = get_or_create_sim_state(db)
    state.running = running
    db.commit()
    db.refresh(state)
    return state


def set_sim_speed(db: Session, speed: float) -> models.SimState:
    """Update simulation speed factor (multiplier)."""
    if speed <= 0:
        raise ValueError(f"Simulation speed must be strictly positive (> 0), got {speed}")
    state = get_or_create_sim_state(db)
    state.speed = float(speed)
    db.commit()
    db.refresh(state)
    return state


def reset_sim(db: Session, to_date: Optional[datetime] = None) -> models.SimState:
    """Reset the virtual clock to anchor date and pause simulation."""
    state = get_or_create_sim_state(db)
    state.virtual_now = to_date or datetime(2026, 10, 12, 0, 0, 0)
    state.running = False
    state.speed = 1.0
    clear_appliance_states()
    db.commit()
    db.refresh(state)
    return state


def setup_demo_scenario(db: Session) -> Dict[str, Any]:
    """
    Demo scenario setup (SPEC §7):
    Resets the virtual clock to evening (21:30), injects an AC-left-on ghost event in A-102,
    ensures consecutive intervals above threshold so the alert immediately triggers,
    and sets speed to 60x with running=True so user can mark it switched off and
    verification completes within seconds.
    """
    demo_evening = datetime(2026, 10, 12, 21, 30, 0)

    # 1. Update sim_state
    state = get_or_create_sim_state(db)
    state.virtual_now = demo_evening
    state.speed = 60.0
    state.running = True

    # 2. Reset appliance state overrides and force AC on in A-102
    clear_appliance_states()
    set_appliance("A-102", "ac", True)

    # 3. Resolve room A-102
    room = db.query(models.Room).filter(models.Room.room_code == "A-102").first()
    if not room:
        room = db.query(models.Room).first()

    ac_eq = (
        db.query(models.Equipment)
        .filter(models.Equipment.room_id == room.id, models.Equipment.kind == "ac")
        .first()
    )
    ac_kw = float(ac_eq.rated_kw * ac_eq.count) if ac_eq else 3.6
    idle_kw = float(room.idle_baseline_kw or 0.08)
    total_demand = round(idle_kw + ac_kw, 3)

    # 4. Ensure consecutive readings at 21:15 and 21:30 for all rooms so live snapshot works
    all_rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
    t_prev = demo_evening - timedelta(minutes=15)

    for t_step in (t_prev, demo_evening):
        for rm in all_rooms:
            rm_demand = total_demand if rm.id == room.id else rm.idle_baseline_kw
            existing_mr = (
                db.query(models.MeterReading)
                .filter(models.MeterReading.room_id == rm.id, models.MeterReading.timestamp == t_step)
                .first()
            )
            if existing_mr:
                existing_mr.actual_demand_kw = rm_demand
                existing_mr.interval_kwh = round(rm_demand * 0.25, 4)
            else:
                new_mr = models.MeterReading(
                    room_id=rm.id,
                    timestamp=t_step,
                    actual_demand_kw=rm_demand,
                    interval_kwh=round(rm_demand * 0.25, 4),
                    source="simulated",
                    is_simulated=True,
                )
                db.add(new_mr)

    db.commit()
    db.refresh(state)

    return {
        "status": "demo_scenario_active",
        "message": f"Demo scenario initialized: Room {room.room_code} ({room.name}) AC running after-hours at {demo_evening.strftime('%H:%M')}. Alert triggered.",
        "room_id": room.id,
        "room_code": room.room_code,
        "room_name": room.name,
        "equipment_kind": "ac",
        "equipment_id": ac_eq.id if ac_eq else None,
        "virtual_now": state.virtual_now.isoformat(),
        "speed": state.speed,
        "running": state.running,
        "ghost_kw": round(ac_kw, 2),
        "alert_status": "TRIGGERED",
        "data_source": "simulated",
    }


def calculate_sleep_duration(speed: float, base_seconds: float = 2.0) -> float:
    """Calculate asyncio sleep duration in seconds scaled inversely by speed."""
    eff_speed = max(0.01, float(speed))
    return max(0.05, min(60.0, base_seconds / eff_speed))


# ---------------------------------------------------------------------------
# Core Tick Engine
# ---------------------------------------------------------------------------
def tick(db: Session, delta_minutes: int = 15) -> Dict[str, Any]:
    """
    Advance the virtual clock by one 15-minute interval.
    1. Advances sim_state.virtual_now.
    2. Evaluates equipment state model and active timetables per room.
    3. Injects scripted ghost scenarios.
    4. Persists new 15-minute MeterReading records for all rooms.
    5. Persists hourly WaterReading records when crossing hour boundaries.

    Returns summary dictionary of generated telemetry.
    """
    with _tick_lock:
        return _tick_locked(db, delta_minutes)


def _tick_locked(db: Session, delta_minutes: int) -> Dict[str, Any]:
    state = get_or_create_sim_state(db)
    state.virtual_now = state.virtual_now + timedelta(minutes=delta_minutes)
    current_ts = state.virtual_now

    weekday = current_ts.weekday()  # 0=Mon, ..., 6=Sun
    time_str = current_ts.strftime("%H:%M")
    hour = current_ts.hour

    rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
    equipment = db.query(models.Equipment).all()
    eq_by_room: Dict[int, List[models.Equipment]] = {}
    for eq in equipment:
        eq_by_room.setdefault(eq.room_id, []).append(eq)

    timetables = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room: Dict[int, List[models.TimetableEntry]] = {}
    for t in timetables:
        tt_by_room.setdefault(t.room_id, []).append(t)

    meter_readings_created = 0
    # Readings already stored for this timestamp (re-running a period must overwrite, not duplicate)
    existing_meter = {
        mr.room_id: mr
        for mr in db.query(models.MeterReading).filter(models.MeterReading.timestamp == current_ts).all()
    }

    for room in rooms:
        r_eq = eq_by_room.get(room.id, [])
        r_tt = tt_by_room.get(room.id, [])

        # Check if class is scheduled
        active_class = None
        if weekday < 6:
            for slot in r_tt:
                if slot.day_of_week == weekday and slot.start_time <= time_str < slot.end_time:
                    active_class = slot
                    break
        in_session = (active_class is not None)

        idle_kw = room.idle_baseline_kw
        on_kw = 0.0
        room_overrides = _appliance_state.get(room.room_code, {})

        # Equipment state model
        for eq in r_eq:
            eq_kind = eq.kind.lower()
            if eq_kind in room_overrides:
                # User manually toggled this appliance
                if room_overrides[eq_kind]:
                    on_kw += eq.rated_kw * eq.count
            elif eq.state == "ON":
                on_kw += eq.rated_kw * eq.count
            elif in_session:
                scaling = (active_class.expected_students / room.capacity) if room.capacity > 0 else 1.0
                scaling = max(0.2, min(1.0, scaling))
                if eq.kind in ("light", "fan", "pc"):
                    on_kw += eq.rated_kw * eq.count * eq.expected_in_class * scaling
                else:
                    on_kw += eq.rated_kw * eq.count * eq.expected_in_class

        # -------------------------------------------------------------------
        # Scripted Ghost Events (SPEC §4, §5)
        # -------------------------------------------------------------------
        # Ghost Event 1: Room A-102 overnight AC left running (21:00 to 07:00)
        if room.room_code in ("A-101", "A-102") and (hour >= 21 or hour < 7):
            if room_overrides.get("ac", True) is not False:
                ac_eqs = [e for e in r_eq if e.kind == "ac"]
                if ac_eqs and "ac" not in room_overrides and not any(e.state == "ON" for e in ac_eqs):
                    on_kw += sum(e.rated_kw * e.count for e in ac_eqs)

        # Ghost Event 2: Room B-201 after-hours computers left on (17:00 to 22:30)
        if room.room_code == "B-201" and (17 <= hour < 22 or (hour == 22 and current_ts.minute <= 30)):
            if "pc" not in room_overrides:
                pc_eqs = [e for e in r_eq if e.kind == "pc"]
                on_kw += sum(e.rated_kw * e.count * 0.95 for e in pc_eqs)
            if "light" not in room_overrides:
                light_eqs = [e for e in r_eq if e.kind == "light"]
                on_kw += sum(e.rated_kw * e.count * 0.8 for e in light_eqs)

        # Ghost Event 3: Room C-301 projector running during lunch break (13:00 to 14:00 Mon-Fri)
        if room.room_code == "C-301" and weekday < 5 and (13 <= hour < 14):
            if "projector" not in room_overrides:
                proj_eqs = [e for e in r_eq if e.kind == "projector"]
                on_kw += sum(e.rated_kw * e.count for e in proj_eqs)
            if "light" not in room_overrides:
                light_eqs = [e for e in r_eq if e.kind == "light"]
                on_kw += sum(e.rated_kw * e.count * 0.75 for e in light_eqs)

        # Realistic subtle sensor noise
        noise = random.gauss(0.0, 0.012)
        actual_kw = max(idle_kw, round(idle_kw + on_kw + noise, 3))
        interval_kwh = round(actual_kw * 0.25, 4)

        prior = existing_meter.get(room.id)
        if prior is not None:
            prior.actual_demand_kw = actual_kw
            prior.interval_kwh = interval_kwh
        else:
            db.add(
                models.MeterReading(
                    room_id=room.id,
                    timestamp=current_ts,
                    actual_demand_kw=actual_kw,
                    interval_kwh=interval_kwh,
                    source="simulated",
                    is_simulated=True,
                )
            )
        meter_readings_created += 1

    # -----------------------------------------------------------------------
    # Hourly Water Readings Persistence
    # -----------------------------------------------------------------------
    water_readings_created = 0
    if current_ts.minute == 0:
        water_locations = db.query(models.WaterLocation).all()
        existing_water = {
            w.location_id: w
            for w in db.query(models.WaterReading).filter(models.WaterReading.timestamp == current_ts).all()
        }
        for loc in water_locations:
            baseline = 20.0 if "Block C" in loc.name else 15.0
            if 0 <= hour < 5:
                flow = baseline + random.gauss(0.0, 1.5)
            elif 5 <= hour < 8:
                flow = 60.0 + (hour - 5) * 35.0 + random.gauss(0.0, 4.0)
            elif 8 <= hour < 12:
                flow = 160.0 + random.gauss(0.0, 10.0)
            elif 12 <= hour < 14:
                flow = 240.0 + (50.0 if "Cafeteria" in loc.name else 0.0) + random.gauss(0.0, 12.0)
            elif 14 <= hour < 18:
                flow = 140.0 + random.gauss(0.0, 8.0)
            elif 18 <= hour < 21:
                flow = 80.0 + random.gauss(0.0, 6.0)
            else:
                flow = 30.0 + random.gauss(0.0, 3.0)

            # Block C night-flow leak scenario during 1 AM - 4 AM
            if "Block C" in loc.name and (1 <= hour < 4):
                flow = 230.0 + random.gauss(0.0, 8.0)

            flow = max(round(flow, 1), 2.0)
            prior_w = existing_water.get(loc.id)
            if prior_w is not None:
                prior_w.flow_rate_lph = flow
                prior_w.interval_litres = round(flow * 1.0, 1)
                prior_w.expected_baseline_lph = baseline
            else:
                db.add(
                    models.WaterReading(
                        location_id=loc.id,
                        timestamp=current_ts,
                        flow_rate_lph=flow,
                        interval_litres=round(flow * 1.0, 1),
                        expected_baseline_lph=baseline,
                        source="simulated",
                        is_simulated=True,
                    )
                )
            water_readings_created += 1

        # -------------------------------------------------------------------
        # Automated Night-Flow Leak Detection (SPEC §9)
        # -------------------------------------------------------------------
        if 1 <= hour <= 4:
            db.flush()  # session has autoflush off: make this tick's readings visible to the query below
            day_start = datetime(current_ts.year, current_ts.month, current_ts.day, 1, 0, 0)
            window_readings = (
                db.query(models.WaterReading)
                .filter(
                    models.WaterReading.timestamp >= day_start,
                    models.WaterReading.timestamp <= current_ts,
                )
                .all()
            )
            # Thresholds are the administrator's configurable settings (Settings page), not constants.
            cfg = {s.key: s.value for s in db.query(models.Setting).all()}

            def _num(key: str, default: float) -> float:
                try:
                    v = float(cfg.get(key, default))
                    return v if v > 0 else default
                except (TypeError, ValueError):
                    return default

            detected_alerts = analyze_night_flow(
                window_readings,
                threshold_lph=_num("water_night_threshold_lph", 50.0),
                default_baseline_lph=_num("water_low_flow_baseline_lph", 20.0),
            )
            for alert_data in detected_alerts:
                existing_alert = (
                    db.query(models.WaterAlert)
                    .filter(
                        models.WaterAlert.location_id == alert_data["location_id"],
                        models.WaterAlert.window_start == alert_data["window_start"],
                    )
                    .first()
                )
                if not existing_alert:
                    new_alert = models.WaterAlert(
                        location_id=alert_data["location_id"],
                        detected_at=current_ts,
                        window_start=alert_data["window_start"],
                        window_end=alert_data["window_end"],
                        avg_flow_lph=alert_data["avg_flow_lph"],
                        baseline_lph=alert_data["baseline_lph"],
                        status="SUSPECTED",
                        inspection_notes=alert_data["inspection_notes"],
                        resolved_at=None,
                    )
                    db.add(new_alert)
                elif existing_alert.status == "SUSPECTED":
                    existing_alert.window_end = alert_data["window_end"]
                    existing_alert.avg_flow_lph = alert_data["avg_flow_lph"]
                    existing_alert.inspection_notes = alert_data["inspection_notes"]

    db.commit()
    db.refresh(state)

    # -----------------------------------------------------------------------
    # Automated Savings Verification (SPEC §8)
    # -----------------------------------------------------------------------
    verified_savings = verify_all_pending_actions(db, current_ts)

    return {
        "virtual_now": current_ts.isoformat(),
        "readings_count": meter_readings_created,
        "rooms_ticked": meter_readings_created,
        "water_readings_count": water_readings_created,
        "verified_savings_count": len(verified_savings),
    }

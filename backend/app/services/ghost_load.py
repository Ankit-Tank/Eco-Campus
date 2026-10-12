"""
GhostWatt — services/ghost_load.py
Pure functions for Ghost Load Intelligence calculation, reasoning, hysteresis alerts,
room status classification, ranking, and actionable switch-off recommendations.
No FastAPI imports.

SPEC §5, §6:
- Ghost Load (kW) = max(0, Actual Demand − Expected Demand)
- Ghost Load (kWh) = Ghost Load (kW) × 0.25 hours (15-min interval)
- Reason codes: NO_CLASS_AC_ON, LAB_AFTER_HOURS, OVER_EXPECTED_DURING_CLASS, OUTSIDE_SCHEDULE
- Room statuses: "In Session", "No Class", "Upcoming Class", "Within Expected Usage",
                 "High Usage", "Possible Idle Load"
- Hysteresis: Alert triggers only after 2 consecutive intervals above threshold.
- Ranking: Rooms sorted descending by ghost_kwh.
- Switch-off-first: Rooms ranked descending by current ghost_kw.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Reason Code Catalog & Explanations (SPEC §5, §6)
# ---------------------------------------------------------------------------
REASON_EXPLANATIONS = {
    "NO_CLASS_AC_ON": (
        "High power consumption consistent with air conditioning running in an "
        "unoccupied room with no scheduled class."
    ),
    "LAB_AFTER_HOURS": (
        "Computer workstations or specialized laboratory equipment left running "
        "outside scheduled lab session hours."
    ),
    "OVER_EXPECTED_DURING_CLASS": (
        "Electricity consumption significantly exceeded expected equipment demand "
        "during an active scheduled class."
    ),
    "OUTSIDE_SCHEDULE": (
        "Unnecessary lighting, fans, or auxiliary appliances active outside "
        "scheduled timetable operating hours."
    ),
}


# ---------------------------------------------------------------------------
# Core Ghost Load Calculations
# ---------------------------------------------------------------------------
def calculate_ghost_load_kw(actual_kw: float, expected_kw: float) -> float:
    """
    Ghost Load in kW for a single interval.
    Ghost Load (kW) = max(0, Actual Demand − Expected Demand)
    """
    return round(max(0.0, float(actual_kw) - float(expected_kw)), 4)


def calculate_ghost_load_kwh(ghost_kw: float, interval_hours: float = 0.25) -> float:
    """
    Ghost Load energy for the interval.
    Ghost Load (kWh) = Ghost Load (kW) × 0.25 (for 15-minute intervals).
    """
    return round(max(0.0, float(ghost_kw)) * float(interval_hours), 4)


def calculate_cost(ghost_kwh: float, price_per_kwh: float = 8.50) -> float:
    """Estimated financial cost of ghost load in INR."""
    return round(float(ghost_kwh) * float(price_per_kwh), 2)


def calculate_emissions(ghost_kwh: float, emissions_factor: float = 0.71) -> float:
    """Estimated carbon emissions of ghost load in kg CO2."""
    return round(float(ghost_kwh) * float(emissions_factor), 4)


def summarise_interval(
    actual_kw: float,
    expected_kw: float,
    price_per_kwh: float = 8.50,
    emissions_factor: float = 0.71,
    interval_hours: float = 0.25,
    fan_watt: float = 75.0,
) -> Dict[str, Any]:
    """
    Return a comprehensive summary dictionary for a single monitoring interval.
    """
    g_kw = calculate_ghost_load_kw(actual_kw, expected_kw)
    g_kwh = calculate_ghost_load_kwh(g_kw, interval_hours)
    cost = calculate_cost(g_kwh, price_per_kwh)
    co2 = calculate_emissions(g_kwh, emissions_factor)
    fan_equiv = round((g_kw * 1000.0) / fan_watt, 1) if fan_watt > 0 else 0.0

    return {
        "actual_kw": round(float(actual_kw), 3),
        "expected_kw": round(float(expected_kw), 3),
        "ghost_kw": round(g_kw, 3),
        "ghost_kwh": round(g_kwh, 4),
        "cost_inr": cost,
        "emissions_kg": co2,
        "fan_equivalent": fan_equiv,
    }


# ---------------------------------------------------------------------------
# Reason Code Classification
# ---------------------------------------------------------------------------
def classify_ghost_reason(
    actual_kw: float,
    expected_kw: float,
    in_session: bool,
    room_type: str = "classroom",
    has_ac: bool = False,
    ts: Optional[datetime] = None,
    threshold_kw: float = 0.2,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Determine the primary reason code and plain-English explanation for ghost load.

    Returns
    -------
    (reason_code, explanation) or (None, None) if consumption is within expected limits.
    """
    ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)
    if ghost_kw < threshold_kw:
        return None, None

    # Case 1: Room is currently in session, but actual is significantly above expected
    if in_session:
        code = "OVER_EXPECTED_DURING_CLASS"
        return code, REASON_EXPLANATIONS[code]

    # Case 2: Room is empty (no class). Distinguish based on appliance profile
    hour = ts.hour if ts else 12

    # High power in empty room with AC installed (typically overnight or after-hours)
    if has_ac and ghost_kw >= 1.2:
        code = "NO_CLASS_AC_ON"
        return code, REASON_EXPLANATIONS[code]

    # Lab with computer workstations or lab benches on after hours (>= 17:00 or < 08:00)
    if (room_type in ("lab", "computer_lab") or "lab" in str(room_type).lower()) and (hour >= 17 or hour < 8):
        code = "LAB_AFTER_HOURS"
        return code, REASON_EXPLANATIONS[code]

    # Default empty room waste (lights, fans, projector left on)
    code = "OUTSIDE_SCHEDULE"
    return code, REASON_EXPLANATIONS[code]


# ---------------------------------------------------------------------------
# Room Status Classification (SPEC §6)
# ---------------------------------------------------------------------------
def determine_room_status(
    in_session: bool,
    actual_kw: float,
    expected_kw: float,
    upcoming_class: bool = False,
    idle_baseline_kw: float = 0.1,
    high_usage_threshold_kw: float = 0.5,
) -> str:
    """
    Classify a room into one of the 6 canonical statuses defined in SPEC §6:
    - "In Session"
    - "No Class"
    - "Upcoming Class"
    - "Within Expected Usage"
    - "High Usage"
    - "Possible Idle Load"
    """
    ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)

    # High usage takes priority when ghost load is severe
    if ghost_kw >= high_usage_threshold_kw:
        return "High Usage"

    # In session
    if in_session:
        return "In Session"

    # Upcoming class in next 30-45 minutes
    if upcoming_class:
        return "Upcoming Class"

    # Mild idle waste when room should be at pure baseline
    if ghost_kw > 0.08 and actual_kw > (idle_baseline_kw + 0.08):
        return "Possible Idle Load"

    # Exactly within normal idle expectation
    if actual_kw <= (idle_baseline_kw + 0.08):
        return "Within Expected Usage"

    return "No Class"


# ---------------------------------------------------------------------------
# Hysteresis Alerting (2 Consecutive Intervals Rule)
# ---------------------------------------------------------------------------
def evaluate_ghost_alert(
    recent_ghost_kw: List[float],
    threshold_kw: float = 0.5,
) -> Dict[str, Any]:
    """
    Evaluates whether an alert should be triggered based on the 2-consecutive-interval rule.
    Single-interval spikes are suppressed to avoid false alarms from measurement noise.

    Parameters
    ----------
    recent_ghost_kw : List of ghost_kw values in chronological order, ending with the latest.
    threshold_kw : Minimum ghost load (kW) to trigger an alert.

    Returns
    -------
    dict with:
      - alert: bool
      - consecutive_count: int
      - latest_ghost_kw: float
      - threshold_kw: float
      - status: "TRIGGERED" | "PENDING_CONFIRMATION" | "CLEARED"
    """
    if not recent_ghost_kw:
        return {
            "alert": False,
            "consecutive_count": 0,
            "latest_ghost_kw": 0.0,
            "threshold_kw": threshold_kw,
            "status": "CLEARED",
        }

    # Count consecutive intervals >= threshold_kw ending at the most recent reading
    consecutive = 0
    for val in reversed(recent_ghost_kw):
        if val >= threshold_kw:
            consecutive += 1
        else:
            break

    latest = recent_ghost_kw[-1]
    alert_triggered = consecutive >= 2

    if alert_triggered:
        status = "TRIGGERED"
    elif consecutive == 1:
        status = "PENDING_CONFIRMATION"
    else:
        status = "CLEARED"

    return {
        "alert": alert_triggered,
        "consecutive_count": consecutive,
        "latest_ghost_kw": round(latest, 3),
        "threshold_kw": threshold_kw,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Room Ranking by Ghost Energy
# ---------------------------------------------------------------------------
def rank_rooms_by_ghost(
    room_aggregates: List[Dict[str, Any]],
    price_per_kwh: float = 8.50,
    emissions_factor: float = 0.71,
) -> List[Dict[str, Any]]:
    """
    Rank rooms over a time period in descending order of total ghost energy (kWh).

    Parameters
    ----------
    room_aggregates : List of dicts, each containing:
      - room_id or room_code
      - total_ghost_kwh (or total_ghost_kw)
      - total_actual_kwh (optional)
      - total_expected_kwh (optional)

    Returns
    -------
    Sorted list of room summaries with rank, financial cost, and emissions.
    """
    processed = []
    for r in room_aggregates:
        item = dict(r)
        g_kwh = float(item.get("total_ghost_kwh", 0.0) or 0.0)
        item["total_ghost_kwh"] = round(g_kwh, 3)
        item["estimated_cost_inr"] = calculate_cost(g_kwh, price_per_kwh)
        item["estimated_emissions_kg"] = calculate_emissions(g_kwh, emissions_factor)
        processed.append(item)

    # Sort descending by total_ghost_kwh
    processed.sort(key=lambda x: x["total_ghost_kwh"], reverse=True)

    # Assign 1-indexed ranks
    for idx, item in enumerate(processed, start=1):
        item["rank"] = idx

    return processed


# ---------------------------------------------------------------------------
# Switch-Off-First Actionable Priority List
# ---------------------------------------------------------------------------
def get_switch_off_first_list(
    current_room_states: List[Dict[str, Any]],
    price_per_kwh: float = 8.50,
    min_ghost_kw: float = 0.1,
) -> List[Dict[str, Any]]:
    """
    Produces a prioritized "Switch-Off-First" triage list of rooms currently
    experiencing ghost load, ranked descending by instantaneous ghost_kw.

    Parameters
    ----------
    current_room_states : List of dicts, each containing:
      - room_code
      - actual_kw
      - expected_kw
      - (optional) equipment_kinds or room_type

    Returns
    -------
    Sorted list of candidate rooms for immediate intervention.
    """
    candidates = []
    for r in current_room_states:
        actual_kw = float(r.get("actual_kw", 0.0))
        expected_kw = float(r.get("expected_kw", 0.0))
        ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)

        if ghost_kw >= min_ghost_kw:
            # Hourly rate of financial loss if left running
            hourly_cost_inr = round(ghost_kw * price_per_kwh, 2)

            # Recommended target appliance
            eq_types = r.get("equipment_kinds", [])
            r_type = str(r.get("room_type", "")).lower()

            if "ac" in eq_types or ghost_kw >= 1.5:
                target_appliance = "Air Conditioning (AC)"
            elif "lab" in r_type or "pc" in eq_types:
                target_appliance = "Workstations & Lab Equipment"
            elif "projector" in eq_types and ghost_kw >= 0.3:
                target_appliance = "Projector & Room Lights"
            else:
                target_appliance = "Lighting & Ceiling Fans"

            candidates.append({
                "room_code": r.get("room_code", "Unknown"),
                "room_name": r.get("room_name", r.get("room_code", "Unknown")),
                "ghost_kw": round(ghost_kw, 3),
                "actual_kw": round(actual_kw, 3),
                "expected_kw": round(expected_kw, 3),
                "potential_hourly_saving_inr": hourly_cost_inr,
                "target_appliance": target_appliance,
                "urgency": "HIGH" if ghost_kw >= 1.5 else ("MEDIUM" if ghost_kw >= 0.5 else "LOW"),
            })

    # Sort descending by current ghost_kw
    candidates.sort(key=lambda x: x["ghost_kw"], reverse=True)

    for idx, item in enumerate(candidates, start=1):
        item["priority"] = idx

    return candidates

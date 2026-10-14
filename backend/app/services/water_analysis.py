"""
Eco-Campus — services/water_analysis.py
Pure functions for night-flow leak detection and water conservation analytics.
No FastAPI imports.

SPEC §9:
- Monitors flow between 1 AM–4 AM against baseline (expected quiescent flow).
- Flags unusual sustained flow as SUSPECTED alerts.
- Computes expected, actual, and excess litres with plain-English inspection notes.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


LEAK_HOURS = {1, 2, 3}  # 01:00, 02:00, 03:00 (the 1 AM – 4 AM night window)


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def is_leak_hour(ts: datetime) -> bool:
    """True if timestamp falls in the 1 AM – 4 AM quiescent monitoring window."""
    return ts.hour in LEAK_HOURS


def detect_possible_leak(
    reading: Any,
    threshold_multiplier: float = 2.0,
) -> bool:
    """
    Evaluate if an individual water reading represents potential leak flow.
    Flags True if timestamp is during 1–4 AM and flow exceeds baseline by multiplier.
    """
    ts = _get_val(reading, "timestamp")
    if ts is None or not is_leak_hour(ts):
        return False

    flow = float(_get_val(reading, "flow_rate_lph", 0.0) or 0.0)
    baseline = float(_get_val(reading, "expected_baseline_lph", 20.0) or 20.0)
    return flow > (baseline * threshold_multiplier)


def analyze_night_flow(
    readings: List[Any],
    baseline_lph: Optional[float] = None,
    threshold_lph: float = 50.0,
    threshold_multiplier: float = 2.0,
    default_baseline_lph: float = 20.0,
) -> List[Dict[str, Any]]:
    """
    Inspect a series of hourly water readings for night-flow anomalies (1 AM – 4 AM).
    Groups consecutive 1–4 AM readings by date and generates SUSPECTED alerts
    reporting expected litres, actual litres, and excess litres.

    Parameters
    ----------
    readings : List of WaterReading models or dicts with timestamp, flow_rate_lph, interval_litres.
    baseline_lph : Expected quiescent baseline in L/h. If None, uses reading.expected_baseline_lph.
    threshold_lph : Absolute flow threshold in L/h above which night flow is suspicious.
    threshold_multiplier : Multiplier over baseline considered anomalous.

    Returns
    -------
    List of SUSPECTED alert dictionaries.
    """
    alerts = []
    if not readings:
        return alerts

    # Filter to 1-4 AM readings
    night_readings = [r for r in readings if is_leak_hour(_get_val(r, "timestamp"))]
    if not night_readings:
        return alerts

    # Group by (location_id, date)
    grouped: Dict[Tuple, List[Any]] = {}
    for r in night_readings:
        ts: datetime = _get_val(r, "timestamp")
        loc_id = _get_val(r, "location_id", 1)
        key = (loc_id, ts.date())
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)

    for (loc_id, date_val), group in grouped.items():
        group_sorted = sorted(group, key=lambda x: _get_val(x, "timestamp"))
        window_start = _get_val(group_sorted[0], "timestamp")
        window_end = _get_val(group_sorted[-1], "timestamp") + timedelta(hours=1)
        duration_hours = len(group_sorted)

        # Calculate flow totals
        actual_litres = sum(float(_get_val(r, "interval_litres", 0.0) or 0.0) for r in group_sorted)
        avg_flow = sum(float(_get_val(r, "flow_rate_lph", 0.0) or 0.0) for r in group_sorted) / duration_hours

        # Resolve effective baseline
        if baseline_lph is not None:
            effective_baseline = baseline_lph
        else:
            effective_baseline = float(_get_val(group_sorted[0], "expected_baseline_lph", default_baseline_lph) or default_baseline_lph)

        expected_litres = round(effective_baseline * duration_hours, 1)
        excess_litres = max(0.0, round(actual_litres - expected_litres, 1))

        # Check if flow triggers alert: exceeds threshold_lph OR exceeds baseline * multiplier
        is_anomalous = (avg_flow > threshold_lph) or (avg_flow > effective_baseline * threshold_multiplier)

        if is_anomalous and excess_litres > 0:
            notes = (
                f"Sustained night flow detected between {window_start.strftime('%H:%M')} and "
                f"{window_end.strftime('%H:%M')}: observed avg {avg_flow:.1f} L/h against normal "
                f"{effective_baseline:.1f} L/h baseline. Potential pipe break, running urinal, or leaking cistern."
            )
            alerts.append({
                "location_id": loc_id,
                "status": "SUSPECTED",
                "window_start": window_start,
                "window_end": window_end,
                "avg_flow_lph": round(avg_flow, 1),
                "baseline_lph": round(effective_baseline, 1),
                "threshold_lph": round(threshold_lph, 1),
                "expected_litres": expected_litres,
                "actual_litres": round(actual_litres, 1),
                "excess_litres": excess_litres,
                "inspection_notes": notes,
            })

    return alerts


def summarise_water_period(
    readings: List[Any],
    bucket_litres: float = 15.0,
    threshold_multiplier: float = 2.0,
) -> Dict[str, Any]:
    """Aggregate water readings into a summary dictionary with equivalents."""
    if not readings:
        return {
            "total_litres": 0.0,
            "avg_flow_lph": 0.0,
            "leak_alerts": 0,
            "bucket_equivalents": 0.0,
            "night_excess_litres": 0.0,
        }

    total = sum(float(_get_val(r, "interval_litres", 0.0) or 0.0) for r in readings)
    avg_flow = sum(float(_get_val(r, "flow_rate_lph", 0.0) or 0.0) for r in readings) / len(readings)
    leak_alerts = sum(1 for r in readings if detect_possible_leak(r, threshold_multiplier))

    # Calculate excess litres during 1-4 AM
    night_readings = [r for r in readings if is_leak_hour(_get_val(r, "timestamp"))]
    night_excess = 0.0
    for r in night_readings:
        flow = float(_get_val(r, "flow_rate_lph", 0.0) or 0.0)
        base = float(_get_val(r, "expected_baseline_lph", 20.0) or 20.0)
        if flow > base:
            night_excess += (flow - base) * 1.0

    buckets = round(total / bucket_litres, 1) if bucket_litres > 0 else 0.0

    return {
        "total_litres": round(total, 1),
        "avg_flow_lph": round(avg_flow, 1),
        "leak_alerts": leak_alerts,
        "bucket_equivalents": buckets,
        "night_excess_litres": round(night_excess, 1),
    }

"""
Tests for expected_demand service (boundary cases, student scaling)
and carbon_calculator service (equivalents, assumption strings, 0.75 kW -> 10 fans).
"""
from datetime import datetime
import pytest

from app.services.expected_demand import expected_kw
from app.services.carbon_calculator import (
    cost_rupees,
    co2_kg,
    fan_equivalents,
    bucket_equivalents,
    calculate_impact_equivalents,
)


# ---------------------------------------------------------------------------
# Expected Demand Tests
# ---------------------------------------------------------------------------

def test_expected_demand_class_boundaries():
    """
    Test start/end boundary cases for class schedules.
    Schedule: Monday 09:00 to 10:30.
    - 08:59 -> No class (idle baseline only)
    - 09:00 -> Class start boundary (in session)
    - 10:15 -> In session
    - 10:29 -> In session
    - 10:30 -> Class end boundary (no class, idle baseline only)
    - 10:31 -> No class
    """
    room = {"capacity": 40, "idle_baseline_kw": 0.15}
    equipment = [
        {"kind": "light", "rated_kw": 0.04, "count": 10, "expected_in_class": 1.0}, # 0.4 kW
        {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},   # 0.45 kW
        {"kind": "ac", "rated_kw": 1.8, "count": 1, "expected_in_class": 1.0},       # 1.8 kW
    ]
    timetable = [
        {
            "day_of_week": 0,  # Monday
            "start_time": "09:00",
            "end_time": "10:30",
            "activity": "Computer Networks",
            "expected_students": 40,  # 100% capacity
            "is_active": True,
        }
    ]

    # Monday timestamps (2026-10-12 is Monday)
    ts_before = datetime(2026, 10, 12, 8, 59)
    ts_start  = datetime(2026, 10, 12, 9, 0)
    ts_mid    = datetime(2026, 10, 12, 10, 15)
    ts_end_m1 = datetime(2026, 10, 12, 10, 29)
    ts_end    = datetime(2026, 10, 12, 10, 30)
    ts_after  = datetime(2026, 10, 12, 10, 31)

    # 1. Before class: 08:59 -> Idle only
    kw_before, r_before = expected_kw(room, equipment, timetable, ts_before)
    assert kw_before == 0.15
    assert r_before["in_session"] is False

    # 2. Start boundary: 09:00 -> In session (idle 0.15 + lights 0.4 + fans 0.45 + ac 1.8 = 2.80 kW)
    kw_start, r_start = expected_kw(room, equipment, timetable, ts_start)
    assert kw_start == 2.80
    assert r_start["in_session"] is True
    assert r_start["activity"] == "Computer Networks"

    # 3. Mid class: 10:15 -> In session
    kw_mid, r_mid = expected_kw(room, equipment, timetable, ts_mid)
    assert kw_mid == 2.80
    assert r_mid["in_session"] is True

    # 4. Final minute: 10:29 -> In session
    kw_end_m1, r_end_m1 = expected_kw(room, equipment, timetable, ts_end_m1)
    assert kw_end_m1 == 2.80
    assert r_end_m1["in_session"] is True

    # 5. End boundary: 10:30 -> Not in session (idle only)
    kw_end, r_end = expected_kw(room, equipment, timetable, ts_end)
    assert kw_end == 0.15
    assert r_end["in_session"] is False

    # 6. After class: 10:31 -> Not in session
    kw_after, r_after = expected_kw(room, equipment, timetable, ts_after)
    assert kw_after == 0.15
    assert r_after["in_session"] is False


def test_expected_demand_student_occupancy_scaling():
    """
    Class: baseline + class equipment, scaled by expected_students / capacity
    for lights, fans, and computers (PCs). AC and projectors remain unscaled.
    """
    room = {"capacity": 50, "idle_baseline_kw": 0.20}
    equipment = [
        # Lights: 0.04 * 10 = 0.40 kW base
        {"kind": "light", "rated_kw": 0.04, "count": 10, "expected_in_class": 1.0},
        # Fans: 0.075 * 8 = 0.60 kW base
        {"kind": "fan", "rated_kw": 0.075, "count": 8, "expected_in_class": 1.0},
        # PCs: 0.15 * 20 = 3.00 kW base
        {"kind": "pc", "rated_kw": 0.15, "count": 20, "expected_in_class": 1.0},
        # AC (fixed): 2.0 kW * 1 = 2.00 kW base (not scaled by students)
        {"kind": "ac", "rated_kw": 2.0, "count": 1, "expected_in_class": 1.0},
    ]

    # Half occupancy: 25 students in capacity 50 -> scaling_factor = 0.5
    timetable = [
        {
            "day_of_week": 1,  # Tuesday
            "start_time": "14:00",
            "end_time": "16:00",
            "activity": "Operating Systems Lab",
            "expected_students": 25,
            "is_active": True,
        }
    ]

    ts = datetime(2026, 10, 13, 14, 30)  # Tuesday 14:30
    kw, reasons = expected_kw(room, equipment, timetable, ts)

    assert reasons["in_session"] is True
    assert reasons["scaling_factor"] == 0.5

    # Expected:
    # idle: 0.20 kW
    # lights: 0.40 * 0.5 = 0.20 kW
    # fans:   0.60 * 0.5 = 0.30 kW
    # pcs:    3.00 * 0.5 = 1.50 kW
    # ac:     2.00 * 1.0 = 2.00 kW (unscaled)
    # Total = 0.20 + 0.20 + 0.30 + 1.50 + 2.00 = 4.20 kW
    assert kw == 4.20
    assert reasons["equipment_breakdown"]["light"]["effective_kw"] == 0.20
    assert reasons["equipment_breakdown"]["fan"]["effective_kw"] == 0.30
    assert reasons["equipment_breakdown"]["pc"]["effective_kw"] == 1.50
    assert reasons["equipment_breakdown"]["ac"]["effective_kw"] == 2.00


# ---------------------------------------------------------------------------
# Carbon Calculator Tests
# ---------------------------------------------------------------------------

def test_fan_equivalent_example():
    """
    Spec required example:
    0.75 kW load with standard 75 W ceiling fans -> exactly 10.0 fans!
    Must return an assumption string detailing the 75 W rating.
    """
    result = fan_equivalents(kw=0.75, fan_watts=75.0)

    assert result["value"] == 10.0
    assert result["fans"] == 10.0
    assert "assumption" in result
    assert "75 W" in result["assumption"]


def test_carbon_and_financial_equivalents_with_assumptions():
    """Verify cost, carbon emissions, and water bucket equivalents always provide assumption strings."""
    # Financial cost
    cost = cost_rupees(kwh=10.0, price_per_kwh=8.50)
    assert cost["value"] == 85.0
    assert "8.50" in cost["assumption"]

    # Carbon emissions
    emissions = co2_kg(kwh=10.0, factor_kg_per_kwh=0.71)
    assert emissions["value"] == 7.1
    assert "0.71" in emissions["assumption"]

    # Water buckets
    buckets = bucket_equivalents(litres=150.0, bucket_litres=15.0)
    assert buckets["value"] == 10.0
    assert "15 L" in buckets["assumption"]

    # Aggregated suite
    suite = calculate_impact_equivalents(
        ghost_kwh=2.0,
        ghost_kw=0.75,
        water_excess_litres=45.0,
        price_per_kwh=8.50,
        emissions_factor=0.71,
        fan_watts=75.0,
        bucket_litres=15.0,
    )
    assert suite["fans"]["value"] == 10.0
    assert suite["buckets"]["value"] == 3.0
    assert suite["cost"]["value"] == 17.0
    assert suite["co2"]["value"] == 1.42
    assert "summary_statement" in suite

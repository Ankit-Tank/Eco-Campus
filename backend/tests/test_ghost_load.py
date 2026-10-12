"""
Tests for Ghost Load calculation, reason classification, room status,
hysteresis alerting, ranking, and switch-off-first prioritization.
"""
from datetime import datetime
import pytest

from app.services.ghost_load import (
    calculate_ghost_load_kw,
    calculate_ghost_load_kwh,
    calculate_cost,
    calculate_emissions,
    summarise_interval,
    classify_ghost_reason,
    determine_room_status,
    evaluate_ghost_alert,
    rank_rooms_by_ghost,
    get_switch_off_first_list,
    REASON_EXPLANATIONS,
)


def test_spec_example():
    """
    SPEC §5 primary example:
    Expected: 5.0 kW, Actual: 12.0 kW -> Ghost: 7.0 kW, 1.75 kWh.
    """
    actual_kw = 12.0
    expected_kw = 5.0

    ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)
    ghost_kwh = calculate_ghost_load_kwh(ghost_kw, interval_hours=0.25)

    assert ghost_kw == 7.0
    assert ghost_kwh == 1.75

    summary = summarise_interval(actual_kw, expected_kw, price_per_kwh=8.50, emissions_factor=0.71)
    assert summary["ghost_kw"] == 7.0
    assert summary["ghost_kwh"] == 1.75
    assert summary["cost_inr"] == round(1.75 * 8.50, 2)
    assert summary["emissions_kg"] == round(1.75 * 0.71, 4)


def test_zero_gap():
    """When actual equals expected, ghost load must be exactly 0.0 kW and 0.0 kWh."""
    actual_kw = 5.0
    expected_kw = 5.0

    ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)
    ghost_kwh = calculate_ghost_load_kwh(ghost_kw)

    assert ghost_kw == 0.0
    assert ghost_kwh == 0.0


def test_negative_gap():
    """When actual is less than expected, ghost load must never be negative (clamped to 0.0)."""
    actual_kw = 3.0
    expected_kw = 5.0

    ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)
    ghost_kwh = calculate_ghost_load_kwh(ghost_kw)

    assert ghost_kw == 0.0
    assert ghost_kwh == 0.0


def test_hysteresis_alert_two_consecutive_intervals():
    """
    Verify alert triggers ONLY after 2 consecutive intervals above threshold (hysteresis).
    Single-interval spikes are suppressed to prevent false alarms.
    """
    threshold = 0.5

    # 1. Empty history -> No alert
    res1 = evaluate_ghost_alert([], threshold_kw=threshold)
    assert res1["alert"] is False
    assert res1["status"] == "CLEARED"

    # 2. Single interval above threshold -> Suppressed (PENDING_CONFIRMATION)
    res2 = evaluate_ghost_alert([0.8], threshold_kw=threshold)
    assert res2["alert"] is False
    assert res2["consecutive_count"] == 1
    assert res2["status"] == "PENDING_CONFIRMATION"

    # 3. Two consecutive intervals above threshold -> TRIGGERED!
    res3 = evaluate_ghost_alert([0.8, 0.9], threshold_kw=threshold)
    assert res3["alert"] is True
    assert res3["consecutive_count"] == 2
    assert res3["status"] == "TRIGGERED"

    # 4. Non-consecutive: spike, drop, spike -> Suppressed (consecutive=1)
    res4 = evaluate_ghost_alert([0.8, 0.1, 0.9], threshold_kw=threshold)
    assert res4["alert"] is False
    assert res4["consecutive_count"] == 1
    assert res4["status"] == "PENDING_CONFIRMATION"

    # 5. Drop below threshold after alert -> CLEARED
    res5 = evaluate_ghost_alert([0.8, 0.9, 0.2], threshold_kw=threshold)
    assert res5["alert"] is False
    assert res5["consecutive_count"] == 0
    assert res5["status"] == "CLEARED"


def test_reason_codes_and_explanations():
    """
    Verify all 4 required reason codes and plain-English explanations:
    NO_CLASS_AC_ON, LAB_AFTER_HOURS, OVER_EXPECTED_DURING_CLASS, OUTSIDE_SCHEDULE.
    """
    assert len(REASON_EXPLANATIONS) == 4
    for code, exp in REASON_EXPLANATIONS.items():
        assert len(exp) > 20
        assert isinstance(exp, str)

    # 1. OVER_EXPECTED_DURING_CLASS
    code1, exp1 = classify_ghost_reason(
        actual_kw=8.0, expected_kw=5.0, in_session=True
    )
    assert code1 == "OVER_EXPECTED_DURING_CLASS"
    assert "scheduled class" in exp1

    # 2. NO_CLASS_AC_ON (empty room with AC and high load)
    code2, exp2 = classify_ghost_reason(
        actual_kw=3.8, expected_kw=0.1, in_session=False, has_ac=True
    )
    assert code2 == "NO_CLASS_AC_ON"
    assert "air conditioning" in exp2

    # 3. LAB_AFTER_HOURS (lab after 17:00)
    code3, exp3 = classify_ghost_reason(
        actual_kw=4.5,
        expected_kw=0.3,
        in_session=False,
        room_type="lab",
        ts=datetime(2026, 10, 8, 19, 0),
    )
    assert code3 == "LAB_AFTER_HOURS"
    assert "laboratory equipment" in exp3

    # 4. OUTSIDE_SCHEDULE (standard empty classroom waste)
    code4, exp4 = classify_ghost_reason(
        actual_kw=0.9,
        expected_kw=0.1,
        in_session=False,
        room_type="classroom",
        ts=datetime(2026, 10, 8, 13, 15),
    )
    assert code4 == "OUTSIDE_SCHEDULE"
    assert "outside scheduled" in exp4


def test_room_status_classification():
    """
    Verify classification of the 6 canonical room statuses defined in SPEC §6:
    'In Session', 'No Class', 'Upcoming Class', 'Within Expected Usage', 'High Usage', 'Possible Idle Load'.
    """
    # High Usage (ghost load exceeds threshold)
    s1 = determine_room_status(in_session=False, actual_kw=4.0, expected_kw=0.1)
    assert s1 == "High Usage"

    # In Session (class active, normal consumption)
    s2 = determine_room_status(in_session=True, actual_kw=3.5, expected_kw=3.4)
    assert s2 == "In Session"

    # Upcoming Class
    s3 = determine_room_status(in_session=False, actual_kw=0.1, expected_kw=0.1, upcoming_class=True)
    assert s3 == "Upcoming Class"

    # Within Expected Usage
    s4 = determine_room_status(in_session=False, actual_kw=0.1, expected_kw=0.1, idle_baseline_kw=0.1)
    assert s4 == "Within Expected Usage"

    # Possible Idle Load (small excess in empty room)
    s5 = determine_room_status(in_session=False, actual_kw=0.35, expected_kw=0.1, idle_baseline_kw=0.1)
    assert s5 == "Possible Idle Load"

    # No Class
    s6 = determine_room_status(in_session=False, actual_kw=0.15, expected_kw=0.15, idle_baseline_kw=0.1)
    assert s6 in ["Within Expected Usage", "No Class"]


def test_room_ranking_by_ghost_kwh():
    """Verify room ranking sorts descending by ghost kWh and computes costs."""
    rooms = [
        {"room_code": "B-101", "total_ghost_kwh": 5.2},
        {"room_code": "A-102", "total_ghost_kwh": 84.0},
        {"room_code": "C-301", "total_ghost_kwh": 18.5},
    ]
    ranked = rank_rooms_by_ghost(rooms, price_per_kwh=8.50)

    assert ranked[0]["room_code"] == "A-102"
    assert ranked[0]["rank"] == 1
    assert ranked[1]["room_code"] == "C-301"
    assert ranked[1]["rank"] == 2
    assert ranked[2]["room_code"] == "B-101"
    assert ranked[2]["rank"] == 3
    assert ranked[0]["estimated_cost_inr"] == round(84.0 * 8.50, 2)


def test_switch_off_first_list():
    """Verify switch-off-first list ranks active ghost loads descending by kW."""
    current_states = [
        {"room_code": "C-301", "actual_kw": 1.2, "expected_kw": 0.1, "equipment_kinds": ["projector", "light"]},
        {"room_code": "A-102", "actual_kw": 3.8, "expected_kw": 0.1, "equipment_kinds": ["ac"]},
        {"room_code": "B-101", "actual_kw": 0.1, "expected_kw": 0.1, "equipment_kinds": []},
    ]
    triage = get_switch_off_first_list(current_states, price_per_kwh=8.50)

    assert len(triage) == 2  # B-101 excluded because ghost_kw == 0
    assert triage[0]["room_code"] == "A-102"
    assert triage[0]["priority"] == 1
    assert triage[0]["target_appliance"] == "Air Conditioning (AC)"
    assert triage[0]["urgency"] == "HIGH"
    assert triage[1]["room_code"] == "C-301"
    assert triage[1]["priority"] == 2

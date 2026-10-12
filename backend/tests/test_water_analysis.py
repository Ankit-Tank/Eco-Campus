"""
Tests for water_analysis service — night flow leak detection, alert generation, and aggregation.
"""
from datetime import datetime
from app.services.water_analysis import (
    is_leak_hour,
    detect_possible_leak,
    analyze_night_flow,
    summarise_water_period,
)


def test_leak_hour_detection():
    """Verify 1 AM, 2 AM, and 3 AM are designated quiescent leak hours."""
    assert is_leak_hour(datetime(2026, 10, 8, 1, 0)) is True
    assert is_leak_hour(datetime(2026, 10, 8, 2, 30)) is True
    assert is_leak_hour(datetime(2026, 10, 8, 3, 59)) is True
    assert is_leak_hour(datetime(2026, 10, 8, 4, 0)) is False
    assert is_leak_hour(datetime(2026, 10, 8, 14, 0)) is False


def test_no_false_positive_daytime():
    """High daytime flow during cafeteria lunch hours must never trigger a leak flag."""
    reading = {
        "timestamp": datetime(2026, 10, 8, 13, 0),
        "flow_rate_lph": 500.0,
        "expected_baseline_lph": 20.0,
    }
    assert detect_possible_leak(reading) is False


def test_night_leak_suspected_alert():
    """
    Sustained high flow between 1 AM and 4 AM must generate a SUSPECTED alert
    with expected_litres, actual_litres, and excess_litres.
    """
    # 3 hourly readings during 1 AM – 4 AM (hours 1, 2, 3)
    readings = [
        {
            "location_id": 4,
            "timestamp": datetime(2026, 10, 8, 1, 0),
            "flow_rate_lph": 240.0,
            "interval_litres": 240.0,
            "expected_baseline_lph": 20.0,
        },
        {
            "location_id": 4,
            "timestamp": datetime(2026, 10, 8, 2, 0),
            "flow_rate_lph": 250.0,
            "interval_litres": 250.0,
            "expected_baseline_lph": 20.0,
        },
        {
            "location_id": 4,
            "timestamp": datetime(2026, 10, 8, 3, 0),
            "flow_rate_lph": 230.0,
            "interval_litres": 230.0,
            "expected_baseline_lph": 20.0,
        },
    ]

    alerts = analyze_night_flow(readings, baseline_lph=20.0, threshold_lph=50.0)
    assert len(alerts) == 1

    alert = alerts[0]
    assert alert["status"] == "SUSPECTED"
    assert alert["location_id"] == 4
    # Expected: 20 L/h * 3 h = 60.0 L
    assert alert["expected_litres"] == 60.0
    # Actual: 240 + 250 + 230 = 720.0 L
    assert alert["actual_litres"] == 720.0
    # Excess: 720 - 60 = 660.0 L
    assert alert["excess_litres"] == 660.0
    assert "Sustained night flow detected" in alert["inspection_notes"]


def test_summarise_water_period():
    """Verify period aggregation and bucket equivalents."""
    readings = [
        {"timestamp": datetime(2026, 10, 8, 10, 0), "flow_rate_lph": 150.0, "interval_litres": 150.0, "expected_baseline_lph": 20.0},
        {"timestamp": datetime(2026, 10, 8, 11, 0), "flow_rate_lph": 150.0, "interval_litres": 150.0, "expected_baseline_lph": 20.0},
    ]
    summary = summarise_water_period(readings, bucket_litres=15.0)

    assert summary["total_litres"] == 300.0
    assert summary["avg_flow_lph"] == 150.0
    assert summary["bucket_equivalents"] == 20.0  # 300 / 15

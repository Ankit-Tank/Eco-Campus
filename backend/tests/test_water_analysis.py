"""Tests for water_analysis service."""
from datetime import datetime
from app.services.water_analysis import is_leak_hour, detect_possible_leak


def test_leak_hour_detection():
    assert is_leak_hour(datetime(2024, 1, 1, 2, 0)) is True
    assert is_leak_hour(datetime(2024, 1, 1, 10, 0)) is False


def test_no_false_positive_daytime():
    # Create a mock reading
    class FakeReading:
        timestamp = datetime(2024, 1, 1, 14, 0)
        flow_rate_lph = 500.0
        expected_baseline_lph = 50.0
    assert detect_possible_leak(FakeReading()) is False

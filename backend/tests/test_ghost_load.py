"""Tests for ghost_load service."""
from app.services.ghost_load import calculate_ghost_load_kw, summarise_interval


def test_ghost_load_positive():
    assert calculate_ghost_load_kw(10.0, 5.0) == 5.0


def test_ghost_load_no_negative():
    assert calculate_ghost_load_kw(3.0, 5.0) == 0.0


def test_summarise_interval():
    result = summarise_interval(12.0, 5.0, price_per_kwh=8.50, emissions_factor=0.71)
    assert result["ghost_kw"] == 7.0
    assert result["ghost_kwh"] == 1.75
    assert result["cost_inr"] == round(1.75 * 8.50, 2)

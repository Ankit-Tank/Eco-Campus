"""
GhostWatt — services/ghost_load.py
Pure functions for Ghost Load calculation.
SPEC §5: Ghost Load (kW) = max(0, Actual - Expected)
         Ghost Load (kWh) = Ghost Load (kW) * 0.25  (15-min interval)
NO FastAPI imports.
"""


def calculate_ghost_load_kw(actual_kw: float, expected_kw: float) -> float:
    """Ghost Load in kW for a single interval."""
    return max(0.0, actual_kw - expected_kw)


def calculate_ghost_load_kwh(ghost_kw: float, interval_hours: float = 0.25) -> float:
    """Ghost Load energy for the interval (default 15 min = 0.25 h)."""
    return ghost_kw * interval_hours


def calculate_cost(ghost_kwh: float, price_per_kwh: float) -> float:
    """Estimated financial cost of the ghost load."""
    return ghost_kwh * price_per_kwh


def calculate_emissions(ghost_kwh: float, emissions_factor: float) -> float:
    """Estimated CO2 emissions in kg from ghost load."""
    return ghost_kwh * emissions_factor


def fan_equivalent(kw: float, fan_watt: float = 75.0) -> float:
    """How many equivalent ceiling fans does this kW represent?"""
    return (kw * 1000) / fan_watt if fan_watt > 0 else 0.0


def summarise_interval(
    actual_kw: float,
    expected_kw: float,
    price_per_kwh: float,
    emissions_factor: float,
    interval_hours: float = 0.25,
) -> dict:
    """Return a full summary dict for one monitoring interval."""
    ghost_kw = calculate_ghost_load_kw(actual_kw, expected_kw)
    ghost_kwh = calculate_ghost_load_kwh(ghost_kw, interval_hours)
    return {
        "actual_kw": round(actual_kw, 3),
        "expected_kw": round(expected_kw, 3),
        "ghost_kw": round(ghost_kw, 3),
        "ghost_kwh": round(ghost_kwh, 4),
        "cost_inr": round(calculate_cost(ghost_kwh, price_per_kwh), 2),
        "emissions_kg": round(calculate_emissions(ghost_kwh, emissions_factor), 4),
        "fan_equivalent": round(fan_equivalent(ghost_kw), 1),
    }

"""
GhostWatt — services/carbon_calculator.py
Human-readable environmental and financial equivalents. SPEC §13.
No FastAPI imports.

Provides:
- cost_rupees: Financial cost with explicit tariff assumption.
- co2_kg: Carbon emissions with explicit grid factor assumption.
- fan_equivalents: kW * 1000 / fan_watts with rated wattage assumption (0.75 kW -> 10 fans).
- bucket_equivalents: Litres / bucket_litres with container capacity assumption.
"""
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Equivalent Calculations with Assumptions (SPEC §13)
# ---------------------------------------------------------------------------

def cost_rupees(kwh: float, price_per_kwh: float = 8.50) -> Dict[str, Any]:
    """
    Calculate financial cost in INR from energy consumption (kWh).
    Always returns a dictionary with the calculated value and the tariff assumption.
    """
    amount = round(max(0.0, float(kwh)) * float(price_per_kwh), 2)
    return {
        "value": amount,
        "rupees": amount,
        "assumption": f"Commercial campus tariff of Rs {float(price_per_kwh):.2f} per kWh",
    }


def co2_kg(kwh: float, factor_kg_per_kwh: float = 0.71) -> Dict[str, Any]:
    """
    Calculate carbon emissions in kg CO2 from energy consumption (kWh).
    Always returns a dictionary with the calculated value and the grid factor assumption.
    """
    emissions = round(max(0.0, float(kwh)) * float(factor_kg_per_kwh), 4)
    return {
        "value": emissions,
        "co2_kg": emissions,
        "assumption": f"Regional grid emission factor of {float(factor_kg_per_kwh):.2f} kg CO2/kWh",
    }


def fan_equivalents(kw: float, fan_watts: float = 75.0) -> Dict[str, Any]:
    """
    Calculate equivalent number of standard ceiling fans running continuously.
    Formula: (kW × 1000) / fan_watts
    Example: 0.75 kW -> (750 / 75) = 10 fans.
    Always returns a dictionary with the calculated value and the wattage assumption.
    """
    if fan_watts <= 0:
        fans = 0.0
    else:
        fans = round((max(0.0, float(kw)) * 1000.0) / float(fan_watts), 1)

    return {
        "value": fans,
        "fans": fans,
        "assumption": f"Standard institutional ceiling fan rated at {float(fan_watts):.0f} W",
    }


def bucket_equivalents(litres: float, bucket_litres: float = 15.0) -> Dict[str, Any]:
    """
    Calculate equivalent domestic water buckets from volume in litres.
    Formula: litres / bucket_litres
    Always returns a dictionary with the calculated value and bucket volume assumption.
    """
    if bucket_litres <= 0:
        buckets = 0.0
    else:
        buckets = round(max(0.0, float(litres)) / float(bucket_litres), 1)

    return {
        "value": buckets,
        "buckets": buckets,
        "assumption": f"Standard domestic utility bucket capacity of {float(bucket_litres):.0f} L",
    }


def calculate_impact_equivalents(
    ghost_kwh: float,
    ghost_kw: float,
    water_excess_litres: float = 0.0,
    price_per_kwh: float = 8.50,
    emissions_factor: float = 0.71,
    fan_watts: float = 75.0,
    bucket_litres: float = 15.0,
) -> Dict[str, Any]:
    """
    Aggregated human-readable impact suite combining financial, carbon,
    electrical appliance, and water container metrics with their respective assumptions.
    """
    cost_data = cost_rupees(ghost_kwh, price_per_kwh)
    co2_data = co2_kg(ghost_kwh, emissions_factor)
    fan_data = fan_equivalents(ghost_kw, fan_watts)
    bucket_data = bucket_equivalents(water_excess_litres, bucket_litres)

    return {
        "cost": cost_data,
        "co2": co2_data,
        "fans": fan_data,
        "buckets": bucket_data,
        "summary_statement": (
            f"Estimated waste: {ghost_kwh:.3f} kWh (≈ {fan_data['value']:.0f} ceiling fans at {fan_watts:.0f} W) • "
            f"Cost: Rs {cost_data['value']:.2f} • Emissions: {co2_data['value']:.3f} kg CO2"
        ),
    }


# ---------------------------------------------------------------------------
# Backward Compatibility Helpers
# ---------------------------------------------------------------------------

def kwh_to_co2_kg(kwh: float, factor_kg_per_kwh: float = 0.71) -> float:
    return co2_kg(kwh, factor_kg_per_kwh)["value"]


def kw_to_fan_equivalent(kw: float, fan_watts: float = 75.0) -> float:
    return fan_equivalents(kw, fan_watts)["value"]


def litres_to_buckets(litres: float, bucket_litres: float = 15.0) -> float:
    return bucket_equivalents(litres, bucket_litres)["value"]


def format_impact_statement(ghost_kwh: float, co2_kg: float, fans: float) -> str:
    return (
        f"Estimated ghost load: {ghost_kwh:.3f} kWh "
        f"(≈ {fans:.0f} ceiling fans at 75 W) • "
        f"CO2 equivalent: {co2_kg:.3f} kg"
    )

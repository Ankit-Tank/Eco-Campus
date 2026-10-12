"""
GhostWatt — services/carbon_calculator.py
Human-readable environmental equivalents. SPEC §13.
NO FastAPI imports.
"""


def kwh_to_co2_kg(kwh: float, factor_kg_per_kwh: float) -> float:
    return round(kwh * factor_kg_per_kwh, 4)


def kw_to_fan_equivalent(kw: float, fan_watts: float = 75.0) -> float:
    """How many ceiling fans (at given wattage) equal this kW load?"""
    return round((kw * 1000) / fan_watts, 1) if fan_watts else 0.0


def litres_to_buckets(litres: float, bucket_litres: float = 15.0) -> float:
    return round(litres / bucket_litres, 1) if bucket_litres else 0.0


def format_impact_statement(ghost_kwh: float, co2_kg: float, fans: float) -> str:
    return (
        f"Estimated ghost load: {ghost_kwh:.3f} kWh "
        f"(≈ {fans:.0f} ceiling fans at 75 W) • "
        f"CO₂ equivalent: {co2_kg:.3f} kg"
    )

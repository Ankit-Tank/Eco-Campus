"""
GhostWatt — services/report_builder.py
Aggregate DB data into report dictionaries. SPEC §12.
Placeholder — Phase 6 implementation.
NO FastAPI imports.
"""


def build_electricity_report(start, end, db) -> dict:
    return {"status": "placeholder", "period": f"{start} to {end}"}


def build_water_report(start, end, db) -> dict:
    return {"status": "placeholder", "period": f"{start} to {end}"}

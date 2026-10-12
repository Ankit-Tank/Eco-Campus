"""
GhostWatt — schemas/dashboard.py
Pydantic schemas for dashboard summary cards and high-level KPIs.
"""
from typing import Dict, Optional
from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    actual_kwh: float
    expected_kwh: float
    ghost_kwh: float
    water_litres: float
    emissions_co2_kg: float
    cost_inr: float
    fan_equivalents: float
    bucket_equivalents: float
    fan_assumption: Optional[str] = None
    bucket_assumption: Optional[str] = None
    assumptions: Optional[dict] = None
    date_from: str
    date_to: str
    data_source: str = "simulated"

"""
Eco-Campus — schemas/dashboard.py
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


class PublicImpactCard(BaseModel):
    key: str
    value: float
    unit: str
    change_pct: Optional[float] = None
    equivalent_value: Optional[float] = None


class PublicImpactResponse(BaseModel):
    is_simulated: bool = True
    cards: list[PublicImpactCard]
    data_source: str = "simulated"


class AdminOverviewZone(BaseModel):
    key: str
    name: str


class AdminOverviewKpis(BaseModel):
    conserved_mwh: float
    consumption_mwh: float
    consumption_change_pct: float
    co2_saved_tonnes: float


class AdminOverviewSeriesItem(BaseModel):
    date: str
    actual_kw: float
    baseline_kw: float


class AdminOverviewEvent(BaseModel):
    date: str


class AdminOverviewBlock(BaseModel):
    key: str
    name: str
    share_pct: float
    kwh: float


class AdminOverviewBuilding(BaseModel):
    name: str
    active_kw: float
    daily_var_pct: float
    status: str


class AdminOverviewResponse(BaseModel):
    is_simulated: bool = True
    zones: list[AdminOverviewZone]
    kpis: AdminOverviewKpis
    series: list[AdminOverviewSeriesItem]
    optimization_events: list[AdminOverviewEvent]
    blocks: list[AdminOverviewBlock]
    total_kwh: float
    buildings: list[AdminOverviewBuilding]
    window_from: Optional[str] = None  # first day of the window actually shown (YYYY-MM-DD)
    window_to: Optional[str] = None    # last day = the simulation clock's date
    data_source: str = "simulated"


class StudentHomeStats(BaseModel):
    reports_filed: int
    accepted: int
    in_progress: int
    estimated_saving_kwh: float


class StudentHomeImpact(BaseModel):
    electricity_kwh: float
    water_litres: float
    co2_kg: float


class StudentHomeResponse(BaseModel):
    is_simulated: bool = True
    name: str
    stats: StudentHomeStats
    recent: list[dict]
    impact: StudentHomeImpact
    data_source: str = "simulated"


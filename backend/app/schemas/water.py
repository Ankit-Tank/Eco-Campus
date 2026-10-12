"""
GhostWatt — schemas/water.py
Pydantic schemas for water readings, time-series, and leak alerts.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class WaterReadingPoint(BaseModel):
    timestamp: str
    location_id: int
    location_name: str
    flow_rate_lph: float
    interval_litres: float
    baseline_lph: float


class WaterSeriesResponse(BaseModel):
    series: List[WaterReadingPoint]
    count: int
    total_litres: float
    data_source: str = "simulated"


class WaterAlertResponse(BaseModel):
    id: int
    location_id: int
    location_name: str
    building: str
    detected_at: str
    window_start: str
    window_end: str
    avg_flow_lph: float
    baseline_lph: float
    status: str
    inspection_notes: str
    resolved_at: Optional[str] = None
    expected_litres: Optional[float] = None
    actual_litres: Optional[float] = None
    excess_litres: Optional[float] = None
    data_source: str = "simulated"


class WaterAlertsListResponse(BaseModel):
    alerts: List[WaterAlertResponse]
    count: int
    data_source: str = "simulated"


class WaterAlertPatch(BaseModel):
    status: Optional[str] = Field(None, description="Updated status: SUSPECTED, CONFIRMED, or FALSE_ALARM")
    inspection_notes: Optional[str] = Field(None, description="Notes from facility maintenance inspection")

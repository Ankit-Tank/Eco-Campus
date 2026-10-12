"""
GhostWatt — schemas/electricity.py
Pydantic schemas for electricity time-series and meter readings.
"""
from typing import List, Optional
from pydantic import BaseModel


class MeterReadingPoint(BaseModel):
    timestamp: str
    room_id: int
    room_code: str
    actual_demand_kw: float
    interval_kwh: float
    expected_demand_kw: float
    ghost_load_kw: float


class ElectricitySeriesResponse(BaseModel):
    series: List[MeterReadingPoint]
    count: int
    total_kwh: float
    limit: Optional[int] = None
    offset: Optional[int] = None
    total_count: Optional[int] = None
    data_source: str = "simulated"

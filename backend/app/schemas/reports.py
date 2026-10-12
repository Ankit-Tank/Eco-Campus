"""
GhostWatt — schemas/reports.py
Pydantic schemas for executive campus sustainability reports and exports.
Every numerical figure is tagged as simulated, calculated, or verified.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TopGhostRoomReport(BaseModel):
    rank: int
    room_id: int
    room_code: str
    name: str
    block: str
    ghost_kwh: float
    cost_inr: float
    co2_kg: float
    explanation: str
    recommended_action: str
    tag: str = "calculated"


class RoomOverLimitReport(BaseModel):
    room_code: str
    name: str
    actual_kwh: float
    expected_kwh: float
    ghost_kwh: float
    excess_percentage: float
    tag: str = "calculated"


class VerifiedSavingsReport(BaseModel):
    claimed_kwh: float
    verified_kwh: float
    monetary_saving_inr: float
    emissions_co2_kg: float
    action_count: int
    verified_count: int
    tag: str = "verified"


class WaterReport(BaseModel):
    total_litres: float
    tag_total: str = "simulated"
    night_excess_litres: float
    tag_excess: str = "calculated"
    leak_alerts_count: int
    active_alerts_count: int
    tag_alerts: str = "calculated"


class ComplaintsReport(BaseModel):
    total_complaints: int
    resolved_complaints: int
    open_complaints: int
    tag: str = "calculated"
    is_restricted: bool = False
    own_complaints: Optional[int] = None
    category_breakdown: Optional[Dict[str, int]] = None
    building_breakdown: Optional[Dict[str, int]] = None


class ReportSummaryResponse(BaseModel):
    date_from: str
    date_to: str
    actual_kwh: float
    expected_kwh: float
    ghost_kwh: float
    cost_inr: float
    co2_kg: float
    top_ghost_rooms: List[TopGhostRoomReport]
    rooms_over_limit: List[RoomOverLimitReport]
    verified_savings: VerifiedSavingsReport
    water: WaterReport
    complaints: ComplaintsReport
    data_tags: Dict[str, str]
    is_restricted: bool = False
    data_source: str = "simulated"

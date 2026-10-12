"""
GhostWatt — schemas/ghost_load.py
Pydantic schemas for Ghost Load current status, rankings, switch-off lists, and room explainability.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class GhostRoomCurrent(BaseModel):
    room_id: int
    room_code: str
    name: str
    block: str
    room_type: str
    actual_kw: float
    expected_kw: float
    ghost_kw: float
    status: str
    in_session: bool
    reason_code: Optional[str] = None
    reason_explanation: Optional[str] = None


class GhostCurrentResponse(BaseModel):
    rooms: List[GhostRoomCurrent]
    total_ghost_kw: float
    total_actual_kw: float = 0.0
    total_expected_kw: float = 0.0
    high_usage_count: int
    idle_load_count: int
    fan_equivalent: Optional[float] = None
    fan_equivalents: Optional[float] = None
    fan_assumption: Optional[str] = None
    cost_per_hour_inr: Optional[float] = None
    assumptions: Optional[dict] = None
    data_source: str = "simulated"


class GhostRoomRankingItem(BaseModel):
    rank: int
    room_id: int
    room_code: str
    name: str
    room_name: Optional[str] = None  # alias for name, used by frontend
    block: str
    total_actual_kwh: float
    total_expected_kwh: float
    total_ghost_kwh: float
    ghost_kwh: Optional[float] = None  # alias for total_ghost_kwh, used by frontend
    dominant_reason_code: Optional[str] = "IDLE_WASTE"  # for frontend ranking table
    cost_inr: float
    co2_kg: float


class GhostRankingResponse(BaseModel):
    ranking: List[GhostRoomRankingItem]
    total_ghost_kwh: float
    total_cost_inr: float
    total_co2_kg: Optional[float] = None
    fan_equivalents: Optional[float] = None
    fan_assumption: Optional[str] = None
    assumptions: Optional[dict] = None
    data_source: str = "simulated"


class SwitchOffItem(BaseModel):
    priority: int
    room_id: Optional[int] = None
    room_code: str
    room_name: str
    equipment_id: Optional[int] = None
    equipment_kind: Optional[str] = None
    ghost_kw: float
    actual_kw: float
    expected_kw: float
    potential_hourly_saving_inr: float
    target_appliance: str
    urgency: str


class SwitchOffListResponse(BaseModel):
    items: List[SwitchOffItem]
    total_potential_saving_inr_per_hour: float
    data_source: str = "simulated"


class GhostExplainResponse(BaseModel):
    room_id: int
    room_code: str
    name: str
    timestamp: str
    actual_kw: float
    expected_kw: float
    ghost_kw: float
    in_session: bool
    activity: Optional[str]
    expected_students: int
    capacity: int
    scaling_factor: float
    equipment_breakdown: Dict[str, Any]
    reason_code: Optional[str]
    reason_explanation: Optional[str]
    is_legitimate: bool
    explanation: str
    fan_equivalent: Optional[float] = None
    fan_assumption: Optional[str] = None
    assumptions: Optional[dict] = None
    data_source: str = "simulated"

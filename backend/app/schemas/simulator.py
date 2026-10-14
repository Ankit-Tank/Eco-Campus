"""
GhostWatt — schemas/simulator.py
Pydantic schemas for simulation clock management, control endpoints, and live snapshots.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SimStateResponse(BaseModel):
    virtual_now: str = Field(..., description="Current simulated datetime (ISO 8601)")
    speed: float = Field(..., description="Simulation speed factor (multiplier)")
    running: bool = Field(..., description="Simulation execution status (True if active)")
    data_source: str = "simulated"


class SimSpeedRequest(BaseModel):
    speed: float = Field(..., gt=0.0, description="Simulation speed multiplier (must be strictly > 0)")


class SimResetRequest(BaseModel):
    to_date: Optional[str] = Field(None, description="Optional target datetime string in ISO format")
    timestamp: Optional[str] = Field(None, description="Alias of to_date (used by the frontend)")


class SimTickRequest(BaseModel):
    delta_minutes: int = Field(15, ge=15, le=240, description="Minutes to advance (multiple of 15)")


class SimApplianceRequest(BaseModel):
    equipment_id: int = Field(..., description="Equipment row to switch")
    state: str = Field(..., description="ON or OFF")


class SimApplianceResponse(BaseModel):
    equipment_id: int
    room_code: str
    kind: str
    state: str
    note: str = "Takes effect from the next simulation tick."
    data_source: str = "simulated"


class LiveRoomSnapshot(BaseModel):
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


class LiveAlertItem(BaseModel):
    type: str = Field(..., description="Alert domain: electricity or water")
    severity: str = Field(..., description="Urgency: warning, critical, info")
    title: str
    description: str
    target: str
    timestamp: str


class LiveSnapshotResponse(BaseModel):
    virtual_now: str
    total_actual_kw: float
    total_expected_kw: float
    total_ghost_kw: float
    actual_kw: Optional[float] = None
    expected_kw: Optional[float] = None
    ghost_kw: Optional[float] = None
    cost_per_hour: float
    cost_per_hour_inr: Optional[float] = None   # alias used by frontend AdminSimulator
    co2_per_hour: float
    co2_per_hour_kg: Optional[float] = None     # alias used by frontend AdminSimulator
    fan_equivalent: float
    fan_assumption: Optional[str] = None
    bucket_equivalent: Optional[float] = None
    bucket_assumption: Optional[str] = None
    assumptions: Optional[dict] = None
    rooms: List[LiveRoomSnapshot]
    active_alerts: List[LiveAlertItem]
    accelerated_time: bool = True
    data_source: str = "simulated"


class DemoScenarioResponse(BaseModel):
    status: str
    message: str
    room_id: int
    room_code: str
    room_name: str
    equipment_kind: str
    equipment_id: Optional[int] = None
    virtual_now: str
    speed: float
    running: bool
    ghost_kw: float
    alert_status: str
    data_source: str = "simulated"

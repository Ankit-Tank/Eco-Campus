"""
GhostWatt — schemas/rooms.py
Pydantic schemas for Room and Equipment CRUD with strict input validation.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOM_TYPES = ("classroom", "lab", "seminar", "reading_room")
EQUIPMENT_KINDS = ("light", "fan", "ac", "projector", "pc", "lab_equipment")


def _check_choice(value, allowed, label):
    if value is None:
        return value
    v = str(value).strip().lower()
    if v not in allowed:
        raise ValueError(f"{label} must be one of: {', '.join(allowed)}")
    return v


# ---------------------------------------------------------------------------
# Equipment Schemas
# ---------------------------------------------------------------------------
class EquipmentCreate(BaseModel):
    kind: str = Field(..., description="Appliance kind: light, fan, ac, projector, pc, lab_equipment")
    rated_kw: float = Field(..., gt=0.0, description="Rated power in kW per unit (must be positive)")
    count: int = Field(1, ge=1, description="Number of units installed (minimum 1)")
    state: str = Field("OFF", description="Current operating state: ON or OFF")
    expected_in_class: float = Field(1.0, ge=0.0, le=1.0, description="Factor expected ON in class (0.0 to 1.0)")

    @field_validator("state")
    @classmethod
    def _state(cls, v):
        return _check_choice(v, ("on", "off"), "state").upper()


class EquipmentUpdate(BaseModel):
    rated_kw: Optional[float] = Field(None, gt=0.0, description="Rated power in kW")
    count: Optional[int] = Field(None, ge=1, description="Count of units")
    state: Optional[str] = Field(None, description="State ON or OFF")
    expected_in_class: Optional[float] = Field(None, ge=0.0, le=1.0, description="Expected in class factor")

    @field_validator("state")
    @classmethod
    def _state(cls, v):
        return None if v is None else _check_choice(v, ("on", "off"), "state").upper()


class EquipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    kind: str
    rated_kw: float
    count: int
    state: str
    expected_in_class: float
    data_source: str = "simulated"


# ---------------------------------------------------------------------------
# Room Schemas
# ---------------------------------------------------------------------------
class RoomCreate(BaseModel):
    room_code: str = Field(..., min_length=2, max_length=20, description="Unique room identifier (e.g. A-101)")
    block: str = Field(..., min_length=1, max_length=10, description="Campus block (e.g. A, B, C)")
    name: str = Field(..., min_length=2, max_length=100, description="Human readable room name")
    room_type: str = Field(..., description="Room category: classroom, lab, seminar, reading_room")
    capacity: int = Field(40, ge=1, le=500, description="Maximum student occupancy (1 to 500)")
    idle_baseline_kw: float = Field(0.1, ge=0.0, le=1000.0, description="Idle standby power in kW when empty")

    @field_validator("room_code", "block")
    @classmethod
    def _upper(cls, v):
        return v.strip().upper()


class RoomUpdate(BaseModel):
    room_code: Optional[str] = Field(None, min_length=2, max_length=20)
    block: Optional[str] = Field(None, min_length=1, max_length=10)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    room_type: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1, le=500)
    idle_baseline_kw: Optional[float] = Field(None, ge=0.0, le=1000.0)
    is_active: Optional[bool] = None

    @field_validator("room_code", "block")
    @classmethod
    def _upper(cls, v):
        return None if v is None else v.strip().upper()


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_code: str
    block: str
    name: str
    room_type: str
    capacity: int
    idle_baseline_kw: float
    is_active: bool
    equipment: List[EquipmentResponse] = []
    data_source: str = "simulated"


class RoomListResponse(BaseModel):
    items: List[RoomResponse]
    total: int
    data_source: str = "simulated"

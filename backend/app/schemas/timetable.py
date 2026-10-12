"""
GhostWatt — schemas/timetable.py
Pydantic schemas for Timetable entries with input validation.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TimetableCreate(BaseModel):
    room_id: int = Field(..., description="Foreign key to rooms.id")
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday ... 5=Saturday, 6=Sunday")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time in HH:MM format (24-hour)")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time in HH:MM format (24-hour)")
    activity: str = Field("Class", max_length=200, description="Course name or scheduled session")
    expected_students: int = Field(30, ge=0, description="Expected student attendance count")

    @field_validator("end_time")
    @classmethod
    def validate_times(cls, v: str, info) -> str:
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError(f"end_time ({v}) must be strictly after start_time ({start})")
        return v


class TimetableUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    activity: Optional[str] = Field(None, max_length=200)
    expected_students: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class TimetableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    day_of_week: int
    start_time: str
    end_time: str
    activity: str
    expected_students: int
    is_active: bool
    data_source: str = "simulated"


class TimetableListResponse(BaseModel):
    items: List[TimetableResponse]
    total: int
    data_source: str = "simulated"

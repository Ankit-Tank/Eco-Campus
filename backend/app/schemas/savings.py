"""
Eco-Campus — schemas/savings.py
Pydantic schemas for corrective actions, verified savings records, and summary metrics.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ActionSwitchOffRequest(BaseModel):
    room_id: int = Field(..., description="Target room ID")
    equipment_id: int = Field(..., description="Target equipment appliance ID")
    notes: Optional[str] = Field("", description="Optional action explanation or notes")


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    room_code: str
    room_name: str
    equipment_id: Optional[int] = None
    equipment_kind: str
    user_id: int
    user_email: str
    action_type: str
    timestamp: str
    notes: str
    verification_status: str
    status: Optional[str] = None
    claimed_reduction_kw: float
    claimed_kwh_per_interval: float
    data_source: str = "simulated"


class ActionListResponse(BaseModel):
    actions: List[ActionResponse]
    count: int
    limit: Optional[int] = None
    offset: Optional[int] = None
    total_count: Optional[int] = None
    data_source: str = "simulated"


class SavingsRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_id: int
    room_id: int
    room_code: str
    equipment: str
    interval_start: str
    pre_avg_kw: float
    post_avg_kw: float
    reduction_kw: float
    credited_kwh: float
    monetary_saving_inr: float
    emissions_kg: float
    verification_status: str
    is_simulated: bool = True
    data_source: str = "simulated"


class SavingsRecordsListResponse(BaseModel):
    records: List[SavingsRecordResponse]
    count: int
    total_credited_kwh: float
    total_monetary_saving_inr: float
    total_emissions_kg: float
    limit: Optional[int] = None
    offset: Optional[int] = None
    total_count: Optional[int] = None
    data_source: str = "simulated"


class SavingsSummaryResponse(BaseModel):
    claimed_kwh: float
    verified_kwh: float
    monetary_saving_inr: float
    emissions_co2_kg: float
    total_actions: int
    verified_actions: int
    partial_actions: int
    unverified_actions: int
    pending_actions: int
    label: str = "Simulated Verified Savings"
    data_source: str = "simulated"

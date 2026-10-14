"""
Eco-Campus — schemas/complaints.py
Pydantic schemas for student water complaints, lifecycle tracking, audit history,
and administrative notification records.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ComplaintHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    changed_by: Optional[int] = None
    changed_by_email: Optional[str] = None
    old_status: Optional[str] = None
    new_status: str
    note: str
    changed_at: str


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_code: str
    student_id: int
    student_email: Optional[str] = None
    student_username: Optional[str] = None
    building: str
    location_detail: str
    category: str
    description: str
    attachment_path: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_to_email: Optional[str] = None
    status: str
    created_at: str
    updated_at: str
    resolution_notes: str = ""
    is_overdue: bool = False
    title: Optional[str] = None
    place: Optional[str] = None
    image_url: Optional[str] = None
    history: List[ComplaintHistoryItem] = []
    data_source: str = "simulated"


class FrequentlyAffectedLocation(BaseModel):
    building: str
    location_detail: str
    count: int


class ComplaintListResponse(BaseModel):
    complaints: List[ComplaintResponse]
    count: int
    overdue_count: int
    frequently_affected_locations: List[FrequentlyAffectedLocation]
    limit: Optional[int] = None
    offset: Optional[int] = None
    total_count: Optional[int] = None
    data_source: str = "simulated"


class ComplaintPatch(BaseModel):
    status: Optional[str] = Field(
        None,
        description="Updated lifecycle status: submitted, acknowledged, assigned, in_progress, resolved, reopened",
    )
    assigned_to: Optional[int] = Field(
        None,
        description="User ID of staff/facility member assigned to the complaint",
    )
    resolution_notes: Optional[str] = Field(
        None,
        description="Resolution details or inspection findings",
    )
    notes: Optional[str] = Field(
        None,
        description="Audit note logged in complaint history",
    )


class ComplaintReopen(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Why the issue is being reopened")


class AdminNotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    notification_type: str
    reference_id: Optional[str] = None
    is_read: bool
    created_at: str
    data_source: str = "simulated"


class AdminNotificationListResponse(BaseModel):
    notifications: List[AdminNotificationItem]
    unread_count: int
    count: int
    data_source: str = "simulated"

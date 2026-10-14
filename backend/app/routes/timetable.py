"""
Eco-Campus — routes/timetable.py
Timetable schedule management CRUD endpoints.
Read operations are open to authenticated users; write operations require administrator privileges.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.timetable import (
    TimetableCreate,
    TimetableListResponse,
    TimetableResponse,
    TimetableUpdate,
)

router = APIRouter()


@router.get("", response_model=TimetableListResponse, summary="List weekly timetable slots")
def list_timetable(
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    day_of_week: Optional[int] = Query(None, ge=0, le=6, description="0=Monday ... 5=Saturday, 6=Sunday"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve recurring weekly class timetable schedule entries."""
    query = db.query(models.TimetableEntry)
    if room_id is not None:
        query = query.filter(models.TimetableEntry.room_id == room_id)
    if day_of_week is not None:
        query = query.filter(models.TimetableEntry.day_of_week == day_of_week)

    entries = query.order_by(models.TimetableEntry.day_of_week.asc(), models.TimetableEntry.start_time.asc()).all()

    items = [
        TimetableResponse(
            id=t.id,
            room_id=t.room_id,
            day_of_week=t.day_of_week,
            start_time=t.start_time,
            end_time=t.end_time,
            activity=t.activity,
            expected_students=t.expected_students,
            is_active=t.is_active,
            data_source="simulated",
        )
        for t in entries
    ]

    return TimetableListResponse(items=items, total=len(items), data_source="simulated")


@router.get("/{entry_id}", response_model=TimetableResponse, summary="Get single timetable slot")
def get_timetable_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Fetch details for a specific timetable schedule entry."""
    entry = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable entry with ID {entry_id} not found",
        )

    return TimetableResponse(
        id=entry.id,
        room_id=entry.room_id,
        day_of_week=entry.day_of_week,
        start_time=entry.start_time,
        end_time=entry.end_time,
        activity=entry.activity,
        expected_students=entry.expected_students,
        is_active=entry.is_active,
        data_source="simulated",
    )


@router.post("", response_model=TimetableResponse, status_code=status.HTTP_201_CREATED, summary="Create a timetable slot (Admin only)")
def create_timetable_entry(
    payload: TimetableCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to schedule a class or lab in a room."""
    room = db.query(models.Room).filter(models.Room.id == payload.room_id).first()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {payload.room_id} does not exist",
        )

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"end_time ({payload.end_time}) must be after start_time ({payload.start_time})",
        )

    entry = models.TimetableEntry(
        room_id=payload.room_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        activity=payload.activity,
        expected_students=payload.expected_students,
        is_active=True,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return TimetableResponse(
        id=entry.id,
        room_id=entry.room_id,
        day_of_week=entry.day_of_week,
        start_time=entry.start_time,
        end_time=entry.end_time,
        activity=entry.activity,
        expected_students=entry.expected_students,
        is_active=entry.is_active,
        data_source="simulated",
    )


@router.put("/{entry_id}", response_model=TimetableResponse, summary="Update timetable slot (Admin only)")
def update_timetable_entry(
    entry_id: int,
    payload: TimetableUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to modify scheduled times or activities."""
    entry = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable entry with ID {entry_id} not found",
        )

    new_start = payload.start_time if payload.start_time is not None else entry.start_time
    new_end = payload.end_time if payload.end_time is not None else entry.end_time

    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"end_time ({new_end}) must be after start_time ({new_start})",
        )

    if payload.day_of_week is not None:
        entry.day_of_week = payload.day_of_week
    if payload.start_time is not None:
        entry.start_time = payload.start_time
    if payload.end_time is not None:
        entry.end_time = payload.end_time
    if payload.activity is not None:
        entry.activity = payload.activity
    if payload.expected_students is not None:
        entry.expected_students = payload.expected_students
    if payload.is_active is not None:
        entry.is_active = payload.is_active

    db.commit()
    db.refresh(entry)

    return TimetableResponse(
        id=entry.id,
        room_id=entry.room_id,
        day_of_week=entry.day_of_week,
        start_time=entry.start_time,
        end_time=entry.end_time,
        activity=entry.activity,
        expected_students=entry.expected_students,
        is_active=entry.is_active,
        data_source="simulated",
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a timetable slot (Admin only)")
def delete_timetable_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to remove a timetable entry."""
    entry = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable entry with ID {entry_id} not found",
        )

    db.delete(entry)
    db.commit()
    return None

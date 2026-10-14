"""
Eco-Campus — routes/actions.py
Endpoints for corrective actions (switch-off appliances) and action history.

SPEC §8 & Prompt Requirements:
- POST /actions/switch-off: admin only, takes room_id, equipment_id, notes.
- Records action with status PENDING, claimed saving estimate, and sim timestamp.
- Sets simulated appliance to OFF effective from the next tick.
- GET /actions: returns list of actions with user info and verification status.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.savings import (
    ActionListResponse,
    ActionResponse,
    ActionSwitchOffRequest,
)
from app.services.simulator import get_or_create_sim_state, get_room_state, set_appliance

router = APIRouter()


def _format_action_response(action: models.Action, db: Session) -> ActionResponse:
    """Helper to convert an Action DB model into an ActionResponse schema."""
    eq = (
        db.query(models.Equipment)
        .filter(
            models.Equipment.room_id == action.room_id,
            func.lower(models.Equipment.kind) == func.lower(action.equipment),
        )
        .first()
    )
    claimed_kw = round(float(eq.rated_kw * eq.count), 3) if eq else 0.0
    claimed_kwh = round(claimed_kw * 0.25, 4)

    return ActionResponse(
        id=action.id,
        room_id=action.room_id,
        room_code=action.room.room_code if action.room else "",
        room_name=action.room.name if action.room else "",
        equipment_id=eq.id if eq else None,
        equipment_kind=action.equipment,
        user_id=action.user_id,
        user_email=action.user.email if action.user else "",
        action_type=action.action_type,
        timestamp=action.timestamp.isoformat() if action.timestamp else "",
        notes=action.notes or "",
        verification_status=str(action.verification_status),
        status=str(action.verification_status),
        claimed_reduction_kw=claimed_kw,
        claimed_kwh_per_interval=claimed_kwh,
        data_source="simulated",
    )


@router.post(
    "/switch-off",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Switch off simulated appliance (Admin only)",
)
def switch_off_appliance(
    payload: ActionSwitchOffRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Admin-only corrective action:
    1. Validates target room and equipment existence.
    2. Records action with status PENDING, claimed savings estimate, and virtual clock timestamp.
    3. Sets simulated appliance to OFF effective from the next simulation tick.
    """
    room = db.query(models.Room).filter(models.Room.id == payload.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {payload.room_id} not found",
        )

    equipment = (
        db.query(models.Equipment)
        .filter(
            models.Equipment.id == payload.equipment_id,
            models.Equipment.room_id == payload.room_id,
        )
        .first()
    )
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id {payload.equipment_id} not found in room {room.room_code}",
        )

    # An appliance that was already switched off cannot be "switched off" again: doing so would
    # create a second claimed saving for the same appliance.
    if get_room_state(room.room_code).get(equipment.kind.lower()) is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{equipment.kind.upper()} in {room.room_code} is already switched off.",
        )

    # Simulation timestamp from virtual clock
    sim_state = get_or_create_sim_state(db)
    action_ts = sim_state.virtual_now

    # Claimed saving estimate
    claimed_kw = round(float(equipment.rated_kw * equipment.count), 3)
    claimed_kwh = round(claimed_kw * 0.25, 4)

    # 1. Record corrective action in PENDING state
    action = models.Action(
        room_id=room.id,
        user_id=admin_user.id,
        action_type="switch_off",
        equipment=equipment.kind.upper(),
        timestamp=action_ts,
        notes=payload.notes or f"Corrective action: switched off {equipment.kind} in {room.room_code}",
        verification_status="PENDING",
    )
    db.add(action)

    # 2. Set simulated appliance to OFF effective from next tick
    equipment.state = "OFF"
    set_appliance(room.room_code, equipment.kind, False)

    db.commit()
    db.refresh(action)

    return ActionResponse(
        id=action.id,
        room_id=room.id,
        room_code=room.room_code,
        room_name=room.name,
        equipment_id=equipment.id,
        equipment_kind=equipment.kind,
        user_id=admin_user.id,
        user_email=admin_user.email,
        action_type=action.action_type,
        timestamp=action.timestamp.isoformat(),
        notes=action.notes,
        verification_status="PENDING",
        status="PENDING",
        claimed_reduction_kw=claimed_kw,
        claimed_kwh_per_interval=claimed_kwh,
        data_source="simulated",
    )


@router.get(
    "",
    response_model=ActionListResponse,
    summary="Get all corrective actions",
)
def get_actions(
    room_id: Optional[int] = Query(None, description="Optional room ID filter"),
    limit: int = Query(100, ge=1, le=500, description="Max actions to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all corrective actions recorded in the system."""
    query = db.query(models.Action).order_by(models.Action.timestamp.desc())
    if room_id is not None:
        query = query.filter(models.Action.room_id == room_id)

    total_matching = query.count()
    actions = query.offset(offset).limit(limit).all()
    action_responses = [_format_action_response(a, db) for a in actions]

    return ActionListResponse(
        actions=action_responses,
        count=len(action_responses),
        limit=limit,
        offset=offset,
        total_count=total_matching,
        data_source="simulated",
    )


@router.get(
    "/{action_id}",
    response_model=ActionResponse,
    summary="Get details of a single corrective action by ID",
)
def get_action_by_id(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve an action by ID."""
    action = db.query(models.Action).filter(models.Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID {action_id} not found",
        )
    return _format_action_response(action, db)

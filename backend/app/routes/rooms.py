"""
Eco-Campus — routes/rooms.py
Room and Equipment management CRUD endpoints.
Read operations are open to authenticated users; write operations require administrator privileges.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.rooms import (
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
    RoomCreate,
    RoomListResponse,
    RoomResponse,
    RoomUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Room CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=RoomListResponse, summary="List all campus rooms")
def list_rooms(
    block: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve all rooms with their installed equipment configuration."""
    query = db.query(models.Room)
    if block:
        query = query.filter(models.Room.block == block.upper())

    rooms = query.order_by(models.Room.room_code.asc()).all()

    items = []
    for r in rooms:
        items.append(
            RoomResponse(
                id=r.id,
                room_code=r.room_code,
                block=r.block,
                name=r.name,
                room_type=r.room_type,
                capacity=r.capacity,
                idle_baseline_kw=r.idle_baseline_kw,
                is_active=r.is_active,
                equipment=[
                    EquipmentResponse(
                        id=eq.id,
                        room_id=eq.room_id,
                        kind=eq.kind,
                        rated_kw=eq.rated_kw,
                        count=eq.count,
                        state=eq.state,
                        expected_in_class=eq.expected_in_class,
                        data_source="simulated",
                    )
                    for eq in r.equipment
                ],
                data_source="simulated",
            )
        )

    return RoomListResponse(items=items, total=len(items), data_source="simulated")


@router.get("/{room_id}", response_model=RoomResponse, summary="Get details for a single room")
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Fetch room metadata and appliance inventory by room ID."""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    return RoomResponse(
        id=room.id,
        room_code=room.room_code,
        block=room.block,
        name=room.name,
        room_type=room.room_type,
        capacity=room.capacity,
        idle_baseline_kw=room.idle_baseline_kw,
        is_active=room.is_active,
        equipment=[
            EquipmentResponse(
                id=eq.id,
                room_id=eq.room_id,
                kind=eq.kind,
                rated_kw=eq.rated_kw,
                count=eq.count,
                state=eq.state,
                expected_in_class=eq.expected_in_class,
                data_source="simulated",
            )
            for eq in room.equipment
        ],
        data_source="simulated",
    )


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED, summary="Create a new room (Admin only)")
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to register a new campus room."""
    existing = db.query(models.Room).filter(models.Room.room_code == payload.room_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room code '{payload.room_code}' already exists",
        )

    new_room = models.Room(
        room_code=payload.room_code.upper(),
        block=payload.block.upper(),
        name=payload.name,
        room_type=payload.room_type.lower(),
        capacity=payload.capacity,
        idle_baseline_kw=payload.idle_baseline_kw,
        is_active=True,
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return RoomResponse(
        id=new_room.id,
        room_code=new_room.room_code,
        block=new_room.block,
        name=new_room.name,
        room_type=new_room.room_type,
        capacity=new_room.capacity,
        idle_baseline_kw=new_room.idle_baseline_kw,
        is_active=new_room.is_active,
        equipment=[],
        data_source="simulated",
    )


@router.put("/{room_id}", response_model=RoomResponse, summary="Update an existing room (Admin only)")
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to modify room specifications or capacity."""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    if payload.room_code is not None and payload.room_code != room.room_code:
        conflict = db.query(models.Room).filter(models.Room.room_code == payload.room_code).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room code '{payload.room_code}' is already assigned to another room",
            )
        room.room_code = payload.room_code.upper()

    if payload.block is not None:
        room.block = payload.block.upper()
    if payload.name is not None:
        room.name = payload.name
    if payload.room_type is not None:
        room.room_type = payload.room_type.lower()
    if payload.capacity is not None:
        room.capacity = payload.capacity
    if payload.idle_baseline_kw is not None:
        room.idle_baseline_kw = payload.idle_baseline_kw
    if payload.is_active is not None:
        room.is_active = payload.is_active

    db.commit()
    db.refresh(room)

    return RoomResponse(
        id=room.id,
        room_code=room.room_code,
        block=room.block,
        name=room.name,
        room_type=room.room_type,
        capacity=room.capacity,
        idle_baseline_kw=room.idle_baseline_kw,
        is_active=room.is_active,
        equipment=[
            EquipmentResponse(
                id=eq.id,
                room_id=eq.room_id,
                kind=eq.kind,
                rated_kw=eq.rated_kw,
                count=eq.count,
                state=eq.state,
                expected_in_class=eq.expected_in_class,
                data_source="simulated",
            )
            for eq in room.equipment
        ],
        data_source="simulated",
    )


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a room (Admin only)")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to remove a room and associated cascade entities."""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    # A room that already has meter history or recorded actions must not be erased (it would
    # destroy the audit trail and verified savings). Deactivate it instead (PUT is_active=false).
    has_history = (
        db.query(models.MeterReading.id).filter(models.MeterReading.room_id == room_id).first() is not None
        or db.query(models.Action.id).filter(models.Action.room_id == room_id).first() is not None
    )
    if has_history:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This room has meter history or recorded actions and cannot be deleted. Deactivate it instead (is_active = false).",
        )

    db.delete(room)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Equipment CRUD
# ---------------------------------------------------------------------------

@router.get("/{room_id}/equipment", response_model=List[EquipmentResponse], summary="List equipment in a room")
def list_room_equipment(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all appliance rows for a specific room."""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    return [
        EquipmentResponse(
            id=eq.id,
            room_id=eq.room_id,
            kind=eq.kind,
            rated_kw=eq.rated_kw,
            count=eq.count,
            state=eq.state,
            expected_in_class=eq.expected_in_class,
            data_source="simulated",
        )
        for eq in room.equipment
    ]


@router.post("/{room_id}/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED, summary="Add equipment to a room (Admin only)")
def create_equipment(
    room_id: int,
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to add new appliance inventory to a room."""
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )

    valid_kinds = {"light", "fan", "ac", "projector", "pc", "lab_equipment"}
    kind_clean = payload.kind.lower()
    if kind_clean not in valid_kinds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid equipment kind '{payload.kind}'. Must be one of: {sorted(valid_kinds)}",
        )

    eq = models.Equipment(
        room_id=room.id,
        kind=kind_clean,
        rated_kw=payload.rated_kw,
        count=payload.count,
        state=payload.state.upper(),
        expected_in_class=payload.expected_in_class,
    )
    db.add(eq)
    db.commit()
    db.refresh(eq)

    return EquipmentResponse(
        id=eq.id,
        room_id=eq.room_id,
        kind=eq.kind,
        rated_kw=eq.rated_kw,
        count=eq.count,
        state=eq.state,
        expected_in_class=eq.expected_in_class,
        data_source="simulated",
    )


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse, summary="Update equipment details (Admin only)")
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to update appliance power rating or counts."""
    eq = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if eq is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found",
        )

    if payload.rated_kw is not None:
        eq.rated_kw = payload.rated_kw
    if payload.count is not None:
        eq.count = payload.count
    if payload.state is not None:
        eq.state = payload.state.upper()
    if payload.expected_in_class is not None:
        eq.expected_in_class = payload.expected_in_class

    db.commit()
    db.refresh(eq)

    return EquipmentResponse(
        id=eq.id,
        room_id=eq.room_id,
        kind=eq.kind,
        rated_kw=eq.rated_kw,
        count=eq.count,
        state=eq.state,
        expected_in_class=eq.expected_in_class,
        data_source="simulated",
    )


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete equipment (Admin only)")
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to remove an equipment record."""
    eq = db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    if eq is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with ID {equipment_id} not found",
        )

    db.delete(eq)
    db.commit()
    return None

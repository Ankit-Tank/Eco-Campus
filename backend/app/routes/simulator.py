"""
GhostWatt — routes/simulator.py
Simulation control endpoints (start, pause, speed adjustment, clock reset, state inspection).
All write and state operations are strictly restricted to Administrators.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.db import models
from app.core.dates import parse_dt
from app.schemas.simulator import (
    DemoScenarioResponse,
    SimApplianceRequest,
    SimApplianceResponse,
    SimResetRequest,
    SimSpeedRequest,
    SimStateResponse,
    SimTickRequest,
)
from app.services.simulator import (
    get_or_create_sim_state,
    reset_sim,
    set_appliance,
    set_sim_running,
    set_sim_speed,
    setup_demo_scenario,
    tick,
)

router = APIRouter()


@router.post("/start", response_model=SimStateResponse, summary="Start the virtual simulation clock (Admin only)")
def start_simulation(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to start automated virtual clock progression."""
    state = set_sim_running(db, running=True)
    return SimStateResponse(
        virtual_now=state.virtual_now.isoformat(),
        speed=state.speed,
        running=state.running,
        data_source="simulated",
    )


@router.post("/pause", response_model=SimStateResponse, summary="Pause the virtual simulation clock (Admin only)")
def pause_simulation(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to pause the virtual simulation clock."""
    state = set_sim_running(db, running=False)
    return SimStateResponse(
        virtual_now=state.virtual_now.isoformat(),
        speed=state.speed,
        running=state.running,
        data_source="simulated",
    )


@router.post("/speed", response_model=SimStateResponse, summary="Adjust simulation speed factor (Admin only)")
def set_simulation_speed(
    payload: SimSpeedRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Admin-only endpoint to adjust virtual time progression speed.
    Speed multiplier must be strictly greater than zero (> 0).
    """
    if payload.speed <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation speed multiplier must be strictly positive (> 0), got {payload.speed}",
        )

    state = set_sim_speed(db, speed=payload.speed)
    return SimStateResponse(
        virtual_now=state.virtual_now.isoformat(),
        speed=state.speed,
        running=state.running,
        data_source="simulated",
    )


@router.post("/reset", response_model=SimStateResponse, summary="Reset simulation virtual clock (Admin only)")
def reset_simulation(
    payload: Optional[SimResetRequest] = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to reset the virtual clock anchor and halt execution."""
    target_date = None
    if payload and (payload.to_date or payload.timestamp):
        # parse_dt answers HTTP 422 with a clear message for invalid values
        target_date = parse_dt(payload.to_date or payload.timestamp, "to_date")

    state = reset_sim(db, to_date=target_date)
    return SimStateResponse(
        virtual_now=state.virtual_now.isoformat(),
        speed=state.speed,
        running=state.running,
        data_source="simulated",
    )


@router.get("/state", response_model=SimStateResponse, summary="Inspect current simulation state (Admin only)")
def get_simulation_state(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to inspect current virtual time, speed, and running flag."""
    state = get_or_create_sim_state(db)
    return SimStateResponse(
        virtual_now=state.virtual_now.isoformat(),
        speed=state.speed,
        running=state.running,
        data_source="simulated",
    )


@router.post("/tick", response_model=SimStateResponse, summary="Manually trigger one 15-minute simulation tick (Admin only)")
def manual_tick(
    payload: Optional[SimTickRequest] = None,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Admin-only endpoint to step the virtual clock forward (default one 15-minute interval)."""
    minutes = payload.delta_minutes if payload else 15
    for _ in range(max(1, minutes // 15)):
        tick(db, delta_minutes=15)
    state = get_or_create_sim_state(db)
    return SimStateResponse(
        virtual_now=state.virtual_now.isoformat(),
        speed=state.speed,
        running=state.running,
        data_source="simulated",
    )


@router.post(
    "/appliance",
    response_model=SimApplianceResponse,
    summary="Force a simulated appliance ON or OFF (Admin only)",
)
def set_simulated_appliance(
    payload: SimApplianceRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """Interactive simulator control: the next simulation tick reflects the new appliance state."""
    new_state = payload.state.strip().upper()
    if new_state not in ("ON", "OFF"):
        raise HTTPException(status_code=422, detail="state must be 'ON' or 'OFF'")
    equipment = db.query(models.Equipment).filter(models.Equipment.id == payload.equipment_id).first()
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Equipment {payload.equipment_id} not found")
    room = db.query(models.Room).filter(models.Room.id == equipment.room_id).first()
    equipment.state = new_state
    set_appliance(room.room_code, equipment.kind, new_state == "ON")
    db.commit()
    return SimApplianceResponse(
        equipment_id=equipment.id, room_code=room.room_code, kind=equipment.kind, state=new_state
    )


@router.post(
    "/scenario/demo",
    response_model=DemoScenarioResponse,
    summary="Initialize interactive demo scenario: A-102 AC left on (Admin only)",
)
def run_demo_scenario(
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Admin-only endpoint to activate the end-to-end interactive demo scenario:
    - Resets virtual clock to 21:30 (evening).
    - Injects AC left ON in Classroom 102 (A-102).
    - Sets up 2 consecutive intervals above threshold so alert triggers immediately.
    - Sets fast speed (60x) and running=True so user can mark appliance switched off
      and verification completes within seconds.
    """
    res = setup_demo_scenario(db)
    return DemoScenarioResponse(**res)

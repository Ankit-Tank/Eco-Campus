"""
GhostWatt — routes/savings.py
Endpoints for Verified Savings metrics and audit records.

SPEC §8 & Prompt Requirements:
- GET /savings/summary: claimed vs verified kWh, Rs, CO2, label "Simulated Verified Savings".
- GET /savings/records: detailed list of verified savings records with financial & CO2 impacts.
- POST /savings/verify/{action_id}: optional manual verification trigger for an action.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.savings import (
    SavingsRecordResponse,
    SavingsRecordsListResponse,
    SavingsSummaryResponse,
)
from app.services.savings_verification import verify_action

router = APIRouter()


@router.get(
    "/summary",
    response_model=SavingsSummaryResponse,
    summary="Get verified savings summary",
)
def get_savings_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns aggregated metrics comparing claimed savings against verified savings:
    - Claimed kWh vs Verified credited kWh
    - Cumulative monetary savings (₹ INR) and avoided carbon emissions (kg CO2)
    - Action status breakdown (VERIFIED, PARTIAL, NOT_VERIFIED, PENDING)
    - Label: "Simulated Verified Savings"
    """
    records = db.query(models.SavingsRecord).all()
    actions = db.query(models.Action).all()

    # Verified energy, rupees, and CO2 totals
    verified_kwh = round(sum(r.credited_kwh for r in records), 4)
    monetary_inr = round(sum(r.monetary_saving_inr for r in records), 2)
    emissions_co2 = round(sum(r.emissions_kg for r in records), 4)

    # Claimed energy estimate across all actions
    all_eq = db.query(models.Equipment).all()
    eq_rating_map = {
        (e.room_id, e.kind.lower()): float(e.rated_kw * e.count)
        for e in all_eq
    }

    claimed_kwh_total = 0.0
    for act in actions:
        key = (act.room_id, act.equipment.lower())
        rated_kw = eq_rating_map.get(key, 0.0)
        claimed_kwh_total += rated_kw * 0.25

    # Status counts normalized to uppercase
    verified_count = 0
    partial_count = 0
    unverified_count = 0
    pending_count = 0

    for act in actions:
        st = str(act.verification_status).upper()
        if st == "VERIFIED":
            verified_count += 1
        elif st == "PARTIAL":
            partial_count += 1
        elif st in ("NOT_VERIFIED", "NO_REDUCTION"):
            unverified_count += 1
        elif st == "PENDING":
            pending_count += 1
        else:
            unverified_count += 1

    return SavingsSummaryResponse(
        claimed_kwh=round(claimed_kwh_total, 4),
        verified_kwh=verified_kwh,
        monetary_saving_inr=monetary_inr,
        emissions_co2_kg=emissions_co2,
        total_actions=len(actions),
        verified_actions=verified_count,
        partial_actions=partial_count,
        unverified_actions=unverified_count,
        pending_actions=pending_count,
        label="Simulated Verified Savings",
        data_source="simulated",
    )


@router.get(
    "/records",
    response_model=SavingsRecordsListResponse,
    summary="Get verified savings audit records",
)
def get_savings_records(
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List interval-by-interval verified savings audit records."""
    query = (
        db.query(models.SavingsRecord)
        .join(models.Action, models.SavingsRecord.action_id == models.Action.id)
        .order_by(models.SavingsRecord.interval_start.desc())
    )

    if room_id is not None:
        query = query.filter(models.Action.room_id == room_id)

    rows = query.limit(limit).all()

    records_out: List[SavingsRecordResponse] = []
    for r in rows:
        action = r.action
        records_out.append(
            SavingsRecordResponse(
                id=r.id,
                action_id=r.action_id,
                room_id=action.room_id if action else 0,
                room_code=action.room.room_code if action and action.room else "",
                equipment=action.equipment if action else "",
                interval_start=r.interval_start.isoformat() if r.interval_start else "",
                pre_avg_kw=r.pre_avg_kw,
                post_avg_kw=r.post_avg_kw,
                reduction_kw=r.reduction_kw,
                credited_kwh=r.credited_kwh,
                monetary_saving_inr=r.monetary_saving_inr,
                emissions_kg=r.emissions_kg,
                verification_status=str(r.verification_status),
                is_simulated=r.is_simulated,
                data_source="simulated",
            )
        )

    return SavingsRecordsListResponse(
        records=records_out,
        count=len(records_out),
        total_credited_kwh=round(sum(rec.credited_kwh for rec in records_out), 4),
        total_monetary_saving_inr=round(sum(rec.monetary_saving_inr for rec in records_out), 2),
        total_emissions_kg=round(sum(rec.emissions_kg for rec in records_out), 4),
        data_source="simulated",
    )


@router.post(
    "/verify/{action_id}",
    response_model=SavingsRecordResponse,
    summary="Trigger verification for a corrective action (Admin only)",
)
def trigger_action_verification(
    action_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Manually evaluate verification for an action.
    Returns 400 if post-window has not closed yet.
    """
    action = db.query(models.Action).filter(models.Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with id {action_id} not found",
        )

    record = verify_action(action, db, window_minutes=15)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post-action window has not completed yet or readings are unavailable.",
        )

    return SavingsRecordResponse(
        id=record.id,
        action_id=record.action_id,
        room_id=action.room_id,
        room_code=action.room.room_code if action.room else "",
        equipment=action.equipment,
        interval_start=record.interval_start.isoformat(),
        pre_avg_kw=record.pre_avg_kw,
        post_avg_kw=record.post_avg_kw,
        reduction_kw=record.reduction_kw,
        credited_kwh=record.credited_kwh,
        monetary_saving_inr=record.monetary_saving_inr,
        emissions_kg=record.emissions_kg,
        verification_status=str(record.verification_status),
        is_simulated=record.is_simulated,
        data_source="simulated",
    )

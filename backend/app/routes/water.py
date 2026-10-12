"""
GhostWatt — routes/water.py
Water consumption time-series and night-flow leak detection alert endpoints.
Read operations are open to authenticated users; alert modifications require administrator privileges.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.services.carbon_calculator import bucket_equivalents
from app.schemas.water import (
    WaterAlertPatch,
    WaterAlertResponse,
    WaterAlertsListResponse,
    WaterReadingPoint,
    WaterSeriesResponse,
)

router = APIRouter()


@router.get("/series", response_model=WaterSeriesResponse, summary="Query water consumption time-series")
def get_water_series(
    location_id: Optional[int] = Query(None, description="Filter by water monitoring location ID"),
    date_from: Optional[str] = Query(None, alias="from", description="Start datetime (ISO string)"),
    date_to: Optional[str] = Query(None, alias="to", description="End datetime (ISO string)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns hourly water flow readings (L/h and interval litres) alongside expected baselines.
    Supports filtering by specific monitoring location and time range.
    """
    query = db.query(models.WaterReading, models.WaterLocation).join(
        models.WaterLocation, models.WaterReading.location_id == models.WaterLocation.id
    )

    if location_id is not None:
        query = query.filter(models.WaterReading.location_id == location_id)

    if date_from:
        try:
            query = query.filter(models.WaterReading.timestamp >= datetime.fromisoformat(date_from))
        except ValueError:
            pass

    if date_to:
        try:
            query = query.filter(models.WaterReading.timestamp <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    results = query.order_by(models.WaterReading.timestamp.asc()).all()

    points = []
    total_litres = 0.0

    for wr, loc in results:
        total_litres += wr.interval_litres
        points.append(
            WaterReadingPoint(
                timestamp=wr.timestamp.isoformat(),
                location_id=wr.location_id,
                location_name=loc.name,
                flow_rate_lph=round(wr.flow_rate_lph, 2),
                interval_litres=round(wr.interval_litres, 2),
                baseline_lph=round(wr.expected_baseline_lph, 2),
            )
        )

    bucket_res = bucket_equivalents(total_litres, 15.0)

    return WaterSeriesResponse(
        series=points,
        count=len(points),
        total_litres=round(total_litres, 2),
        bucket_equivalents=bucket_res["value"],
        bucket_assumption=bucket_res["assumption"],
        assumptions={
            "bucket": bucket_res["assumption"],
        },
        data_source="simulated",
    )


@router.get("/alerts", response_model=WaterAlertsListResponse, summary="List water leak alerts")
def get_water_alerts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by alert status: SUSPECTED, CONFIRMED, FALSE_ALARM"),
    location_id: Optional[int] = Query(None, description="Filter by water location ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns automated night-flow leak alerts with expected, actual, and excess litres.
    Filtered by alert status and monitoring location.
    """
    query = db.query(models.WaterAlert, models.WaterLocation).join(
        models.WaterLocation, models.WaterAlert.location_id == models.WaterLocation.id
    )

    if status_filter:
        query = query.filter(models.WaterAlert.status == status_filter.upper())

    if location_id is not None:
        query = query.filter(models.WaterAlert.location_id == location_id)

    results = query.order_by(models.WaterAlert.detected_at.desc()).all()

    alerts_list = []
    for alert, loc in results:
        duration_hours = max(1.0, (alert.window_end - alert.window_start).total_seconds() / 3600.0)
        expected_litres = round(alert.baseline_lph * duration_hours, 1)
        actual_litres = round(alert.avg_flow_lph * duration_hours, 1)
        excess_litres = max(0.0, round(actual_litres - expected_litres, 1))
        resolved_str = alert.resolved_at.isoformat() if alert.resolved_at else None

        b_res = bucket_equivalents(excess_litres, 15.0)

        alerts_list.append(
            WaterAlertResponse(
                id=alert.id,
                location_id=alert.location_id,
                location_name=loc.name,
                building=loc.building,
                detected_at=alert.detected_at.isoformat(),
                window_start=alert.window_start.isoformat(),
                window_end=alert.window_end.isoformat(),
                avg_flow_lph=round(alert.avg_flow_lph, 1),
                baseline_lph=round(alert.baseline_lph, 1),
                status=alert.status,
                inspection_notes=alert.inspection_notes or "",
                resolved_at=resolved_str,
                expected_litres=expected_litres,
                actual_litres=actual_litres,
                excess_litres=excess_litres,
                bucket_equivalents=b_res["value"],
                bucket_assumption=b_res["assumption"],
                assumptions={"bucket": b_res["assumption"]},
                data_source="simulated",
            )
        )

    return WaterAlertsListResponse(
        alerts=alerts_list,
        count=len(alerts_list),
        data_source="simulated",
    )


@router.patch("/alerts/{alert_id}", response_model=WaterAlertResponse, summary="Update water alert inspection status (Admin only)")
def update_water_alert(
    alert_id: int,
    payload: WaterAlertPatch,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Admin-only endpoint to triage a suspected water leak.
    Updates status (SUSPECTED, CONFIRMED, FALSE_ALARM) and records maintenance inspection findings.
    """
    alert = db.query(models.WaterAlert).filter(models.WaterAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Water alert with ID {alert_id} not found",
        )

    if payload.status is not None:
        valid_statuses = {"SUSPECTED", "CONFIRMED", "FALSE_ALARM"}
        status_clean = payload.status.upper()
        if status_clean not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert status '{payload.status}'. Must be one of: {sorted(valid_statuses)}",
            )
        alert.status = status_clean
        if status_clean in ("CONFIRMED", "FALSE_ALARM"):
            alert.resolved_at = datetime.now()
        elif status_clean == "SUSPECTED":
            alert.resolved_at = None

    if payload.inspection_notes is not None:
        alert.inspection_notes = payload.inspection_notes

    db.commit()
    db.refresh(alert)

    duration_hours = max(1.0, (alert.window_end - alert.window_start).total_seconds() / 3600.0)
    expected_litres = round(alert.baseline_lph * duration_hours, 1)
    actual_litres = round(alert.avg_flow_lph * duration_hours, 1)
    excess_litres = max(0.0, round(actual_litres - expected_litres, 1))
    resolved_str = alert.resolved_at.isoformat() if alert.resolved_at else None

    b_res = bucket_equivalents(excess_litres, 15.0)

    return WaterAlertResponse(
        id=alert.id,
        location_id=alert.location_id,
        location_name=alert.location.name if alert.location else "Unknown",
        building=alert.location.building if alert.location else "Unknown",
        detected_at=alert.detected_at.isoformat(),
        window_start=alert.window_start.isoformat(),
        window_end=alert.window_end.isoformat(),
        avg_flow_lph=round(alert.avg_flow_lph, 1),
        baseline_lph=round(alert.baseline_lph, 1),
        status=alert.status,
        inspection_notes=alert.inspection_notes or "",
        resolved_at=resolved_str,
        expected_litres=expected_litres,
        actual_litres=actual_litres,
        excess_litres=excess_litres,
        bucket_equivalents=b_res["value"],
        bucket_assumption=b_res["assumption"],
        assumptions={"bucket": b_res["assumption"]},
        data_source="simulated",
    )

"""
GhostWatt — routes/app_settings.py
Runtime configurable system parameters (tariffs, emission factors, thresholds).
Read is available to authenticated users; update is strictly restricted to Administrators.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.db import models
from app.schemas.settings import SettingItem, SettingsResponse, SettingsUpdate

router = APIRouter()


@router.get("", response_model=SettingsResponse, summary="Get all system settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve all configurable system parameters."""
    rows = db.query(models.Setting).all()
    setting_dict = {r.key: r.value for r in rows}
    items = [
        SettingItem(key=r.key, value=r.value, description=r.description)
        for r in rows
    ]

    return SettingsResponse(
        settings=setting_dict,
        items=items,
        data_source="simulated",
    )


@router.put("", response_model=SettingsResponse, summary="Update system settings (Admin only)")
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    """
    Admin-only endpoint to update system parameters.
    Validates that numerical values (tariffs, emission factors, thresholds) are strictly positive.
    """
    updates = payload.settings
    numeric_keys = {
        "electricity_price_per_kwh",
        "emissions_factor_kg_per_kwh",
        "fan_watt_equivalent",
        "bucket_litres",
        "water_night_threshold_lph",
        "water_low_flow_baseline_lph",
    }

    for key, val in updates.items():
        if key in numeric_keys:
            try:
                num = float(val)
                if num <= 0 or num != num or num in (float("inf"), float("-inf")):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Setting '{key}' must be a strictly positive number (> 0), got {num}",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Setting '{key}' must be a valid float value",
                )

        existing = db.query(models.Setting).filter(models.Setting.key == key).first()
        if existing:
            existing.value = str(val)
        else:
            db.add(models.Setting(key=key, value=str(val), description="User configured"))

    db.commit()

    rows = db.query(models.Setting).all()
    setting_dict = {r.key: r.value for r in rows}
    items = [
        SettingItem(key=r.key, value=r.value, description=r.description)
        for r in rows
    ]

    return SettingsResponse(
        settings=setting_dict,
        items=items,
        data_source="simulated",
    )

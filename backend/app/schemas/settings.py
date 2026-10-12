"""
GhostWatt — schemas/settings.py
Pydantic schemas for runtime system settings with strict positive value validation.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator


class SettingItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class SettingsResponse(BaseModel):
    settings: Dict[str, str]
    items: List[SettingItem]
    data_source: str = "simulated"


class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

    @field_validator("settings")
    @classmethod
    def validate_positive_values(cls, v: Dict[str, str]) -> Dict[str, str]:
        # Validate that numerical config keys are strictly positive numbers
        numeric_keys = {
            "electricity_price_per_kwh",
            "emissions_factor_kg_per_kwh",
            "fan_watt_equivalent",
            "bucket_litres",
            "water_night_threshold_lph",
            "water_low_flow_baseline_lph",
        }
        for key, val in v.items():
            if key in numeric_keys:
                try:
                    num_val = float(val)
                    if num_val <= 0:
                        raise ValueError(f"Setting '{key}' must be a strictly positive number (> 0), got {num_val}")
                except ValueError as err:
                    if "strictly positive" in str(err):
                        raise
                    raise ValueError(f"Setting '{key}' must be a valid numerical value, got '{val}'")
        return v

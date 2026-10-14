"""
GhostWatt - schemas/settings.py
Pydantic schemas for runtime system settings with strict, finite, bounded value validation.
"""
import math
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


# (min exclusive, max inclusive) sanity bounds for each numeric calculation parameter
NUMERIC_BOUNDS = {
    "electricity_price_per_kwh": (0.0, 1000.0),
    "emissions_factor_kg_per_kwh": (0.0, 10.0),
    "fan_watt_equivalent": (0.0, 2000.0),
    "bucket_litres": (0.0, 1000.0),
    "water_night_threshold_lph": (0.0, 100000.0),
    "water_low_flow_baseline_lph": (0.0, 100000.0),
}


class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

    @field_validator("settings")
    @classmethod
    def validate_values(cls, v: Dict[str, str]) -> Dict[str, str]:
        if len(v) > 50:
            raise ValueError("Too many settings in one request")
        for key, val in v.items():
            if len(key) > 100 or len(str(val)) > 500:
                raise ValueError(f"Setting '{key}' is too long")
            if key in NUMERIC_BOUNDS:
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    raise ValueError(f"Setting '{key}' must be a valid numerical value, got '{val}'")
                if not math.isfinite(num):
                    raise ValueError(f"Setting '{key}' must be a finite number, got '{val}'")
                lo, hi = NUMERIC_BOUNDS[key]
                if num <= lo:
                    raise ValueError(f"Setting '{key}' must be a strictly positive number (> 0), got {num}")
                if num > hi:
                    raise ValueError(f"Setting '{key}' must be at most {hi:g}, got {num}")
        return v

"""
GhostWatt — schemas/leaderboard.py
Pydantic schemas for the campus block sustainability leaderboard.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BlockLeaderboardItem(BaseModel):
    rank: int = Field(..., description="Leaderboard position (1=most sustainable)")
    block: str = Field(..., description="Campus block identifier, e.g. 'A' or 'Block A'")
    name: str = Field(..., description="Block department / building name")
    actual_kwh: float = Field(..., description="Total actual energy consumed (kWh)")
    expected_kwh: float = Field(..., description="Expected baseline energy required (kWh)")
    ghost_kwh: float = Field(..., description="Estimated excess ghost load energy (kWh)")
    waste_percentage: float = Field(..., description="Percentage of consumed power that was ghost waste")
    waste_pct: Optional[float] = None  # alias for frontend
    sustainability_score: float = Field(..., description="Campus efficiency score from 0 to 100 (higher is better)")
    score: Optional[float] = None  # alias for frontend
    grade: str = Field(..., description="Letter grade: A+, A, B, C, D")
    cost_inr: float = Field(..., description="Financial waste cost in INR")
    co2_kg: float = Field(..., description="Avoidable carbon emissions in kg CO2")
    emissions_kg: Optional[float] = None  # alias for frontend
    fan_equivalents: float = Field(..., description="Waste expressed as equivalent ceiling fans")
    fan_assumption: Optional[str] = None


class BlockLeaderboardResponse(BaseModel):
    period: str = Field(..., description="Time window, e.g. '7d' or 'all'")
    blocks: List[BlockLeaderboardItem]
    leaderboard: Optional[List[BlockLeaderboardItem]] = None  # alias for frontend
    total_ghost_kwh: float = 0.0
    total_cost_inr: float = 0.0
    total_co2_kg: float = 0.0
    best_block: str
    worst_block: str
    assumptions: Dict[str, str]
    data_source: str = "simulated"


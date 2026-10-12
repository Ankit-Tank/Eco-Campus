"""
GhostWatt — schemas/assistant.py
Pydantic schemas for the AI Sustainability Assistant (/assistant/ask).
"""
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class AssistantAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="User question or query")


class AssistantAskResponse(BaseModel):
    answer: str = Field(..., description="Grounded natural language answer or fallback explanation")
    data_used: Dict[str, Any] = Field(default_factory=dict, description="Structured tool data used to form the answer")
    source: Literal["groq", "fallback"] = Field(..., description="Response generator: groq or fallback")
    data_source: str = Field(default="simulated", description="Data provenance label")

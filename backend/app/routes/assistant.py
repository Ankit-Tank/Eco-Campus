"""
Eco-Campus — routes/assistant.py
Endpoint for AI Sustainability Assistant (POST /assistant/ask).
SPEC §11:
- Whitelisted tool-calling with authenticated user context and role enforcement.
- Model produces natural language narration grounded in tool output.
- Number guard rejects hallucinated numbers and invokes template fallback.
- On timeout, rate limit, invalid key, or unsupported queries, invokes fallback.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.db import models
from app.schemas.assistant import AssistantAskRequest, AssistantAskResponse
from app.services import groq_assistant

router = APIRouter()


@router.post(
    "/ask",
    response_model=AssistantAskResponse,
    summary="Ask AI Sustainability Assistant",
    description=(
        "Query campus sustainability data using Groq function calling. "
        "Returns grounded natural language answer with data_used and provenance."
    ),
)
def ask_assistant(
    payload: AssistantAskRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes grounded AI Assistant pipeline:
    1. Model selects whitelisted backend query tool.
    2. Backend executes tool enforcing role constraints.
    3. Model narrate results, guarded by number validation.
    4. Deterministic fallback kicks in on errors, rate limits, or hallucinations.
    """
    result = groq_assistant.ask(
        question=payload.question,
        user=current_user,
        db=db,
    )

    return AssistantAskResponse(
        answer=result.get("answer", ""),
        data_used=result.get("data_used", {}),
        source=result.get("source", "fallback"),
        data_source="simulated",
    )

"""
GhostWatt — services/assistant_tools.py
Approved data-fetch functions for the Groq assistant.
Groq only calls these — it never invents numbers. SPEC §11.
NO FastAPI imports.
"""
from sqlalchemy.orm import Session


def get_top_ghost_load_rooms(db: Session, limit: int = 5) -> list:
    """Returns rooms ranked by cumulative ghost load. Phase 6 will implement."""
    return []


def get_unresolved_complaints(db: Session) -> list:
    """Returns open water complaints. Phase 6 will implement."""
    return []


def get_verified_savings_summary(db: Session) -> dict:
    """Returns cumulative verified savings. Phase 6 will implement."""
    return {"credited_kwh": 0, "monetary_inr": 0, "emissions_kg": 0}

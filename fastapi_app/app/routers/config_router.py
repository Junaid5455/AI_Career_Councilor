"""
routers/config_router.py
========================
Exports all dropdown/choice constants from config.py as a single JSON endpoint.
The Next.js frontend calls this once on load to populate all select inputs
without ever hardcoding option lists client-side.

GET /config/options
"""

from fastapi import APIRouter

from app.schemas import ConfigResponse
from config import (
    GENDER_OPTIONS, SECONDARY_SYSTEM_OPTIONS, HIGHER_SYSTEM_OPTIONS,
    FINANCIAL_STATUS_OPTIONS, LEARNING_STYLE_OPTIONS, LIFESTYLE_OPTIONS,
    PERSONALITY_TYPES, SUBJECT_TYPE_OPTIONS, COMMUNICATION_SKILLS,
    INTEREST_FIELDS,
)

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/options", response_model=ConfigResponse)
def get_config_options():
    """
    Returns all static choice lists used by the interview form.
    Frontend should fetch this once and cache it for the session.
    """
    return ConfigResponse(
        gender_options=GENDER_OPTIONS,
        secondary_system_options=SECONDARY_SYSTEM_OPTIONS,
        higher_system_options=HIGHER_SYSTEM_OPTIONS,
        financial_status_options=FINANCIAL_STATUS_OPTIONS,
        learning_style_options=LEARNING_STYLE_OPTIONS,
        lifestyle_options=LIFESTYLE_OPTIONS,
        personality_types=PERSONALITY_TYPES,
        subject_type_options=SUBJECT_TYPE_OPTIONS,
        communication_skills=COMMUNICATION_SKILLS,
        interest_fields=INTEREST_FIELDS,
    )

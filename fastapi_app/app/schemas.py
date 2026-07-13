"""
schemas.py
==========
Pydantic v2 request/response models for all API endpoints.
These are the contracts between the Next.js frontend and the FastAPI backend.
No business logic lives here — only shape definitions and validation rules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# SHARED / REUSED MODELS
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """Generic success envelope returned when no data payload is needed."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    detail: str
    success: bool = False


# ---------------------------------------------------------------------------
# SESSION
# ---------------------------------------------------------------------------

class SessionCreateResponse(BaseModel):
    """Returned when a new counselling session is created."""
    session_id: str
    message: str


class SessionStateResponse(BaseModel):
    """Full session state — returned for resume/status requests."""
    session_id: str
    current_step: int
    steps_completed: List[int]
    collection_complete: bool
    report_generated: bool
    session_start_time: str
    student_profile: Dict[str, Any]


# ---------------------------------------------------------------------------
# PROFILE / STEP SUBMISSION
# ---------------------------------------------------------------------------

class PersonalInfoRequest(BaseModel):
    """Step 2 — Personal Information."""
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=10, le=60)
    gender: str
    country: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    native_language: str = Field(..., min_length=1)
    education_language: str = Field(..., min_length=1)


class SecondaryEducationRequest(BaseModel):
    """Step 3 — Secondary Education."""
    secondary_system: str
    secondary_year: Optional[int] = None
    secondary_subjects: List[str] = []
    secondary_marks: Optional[float] = Field(None, ge=0, le=100)
    secondary_grade: Optional[str] = None
    secondary_completed: bool = True


class HigherEducationRequest(BaseModel):
    """Step 4 — Higher / Intermediate Education."""
    higher_system: str
    higher_year: Optional[int] = None
    higher_subjects: List[str] = []
    higher_subject_marks: Dict[str, Any] = {}
    higher_completed: bool = True


class SubjectPerformanceEntry(BaseModel):
    marks: Optional[float] = Field(None, ge=0, le=100)
    interest: int = Field(..., ge=1, le=10)
    difficulty: int = Field(..., ge=1, le=10)
    confidence: int = Field(..., ge=1, le=10)
    hours_per_week: float = Field(..., ge=0)


class SubjectPerformanceRequest(BaseModel):
    """Step 5 — Subject-wise Performance."""
    subject_performance: Dict[str, SubjectPerformanceEntry]


class FavouriteSubjectRequest(BaseModel):
    """Step 6 — Favourite Subject & Topics."""
    favourite_subject: str = Field(..., min_length=1)
    favourite_topics: List[str] = []


class CareerDecisionRequest(BaseModel):
    """Step 7 — Current Degree Plan."""
    current_degree_plan: str = Field(..., min_length=1)


class PreferredCountriesRequest(BaseModel):
    """Step 8 — Study & Work Country Preferences."""
    study_country: str = Field(..., min_length=1)
    work_country: str = Field(..., min_length=1)


class InterestRatingsRequest(BaseModel):
    """Step 9 — Interest field ratings (1-10)."""
    interest_ratings: Dict[str, int]

    @field_validator("interest_ratings")
    @classmethod
    def check_rating_range(cls, v: Dict[str, int]) -> Dict[str, int]:
        for field, score in v.items():
            if not (1 <= score <= 10):
                raise ValueError(f"Rating for '{field}' must be between 1 and 10.")
        return v


class ProgrammingAssessmentRequest(BaseModel):
    """Step 10 — Programming Assessment."""
    has_programmed: bool
    programming_languages: List[str] = []
    programming_interest: int = Field(..., ge=1, le=10)
    programming_experience: int = Field(..., ge=0)   # months


class MathAssessmentRequest(BaseModel):
    """Step 11 — Mathematics Assessment."""
    math_is_favourite: bool
    math_daily_ok: bool
    math_career_ok: bool


class CommunicationSkillsRequest(BaseModel):
    """Step 12 — Communication Skills (each rated 1-10)."""
    communication_skills: Dict[str, int]

    @field_validator("communication_skills")
    @classmethod
    def check_skill_range(cls, v: Dict[str, int]) -> Dict[str, int]:
        for skill, score in v.items():
            if not (1 <= score <= 10):
                raise ValueError(f"Score for '{skill}' must be 1-10.")
        return v


class PersonalityRequest(BaseModel):
    """Step 13 — Personality Type & Subject Preferences."""
    personality_type: str
    subject_type_preference: List[str] = []


class LearningStyleRequest(BaseModel):
    """Step 14 — Learning Style Preferences."""
    learning_styles: List[str] = []


class HobbiesRequest(BaseModel):
    """Step 15 — Hobbies."""
    hobbies: List[str] = []


class FavouriteGamesRequest(BaseModel):
    """Step 16 — Favourite Games."""
    favourite_games: List[str] = []


class FinancialBackgroundRequest(BaseModel):
    """Step 17 — Financial Background."""
    financial_status: str
    education_budget: str = Field(..., min_length=1)


class FamilyBackgroundRequest(BaseModel):
    """Step 18 — Family Background."""
    parent_occupations: str = Field(..., min_length=1)
    family_education: str = Field(..., min_length=1)
    family_expectations: str = Field(..., min_length=1)
    family_business: str = ""


class CareerGoalsRequest(BaseModel):
    """Step 19 — Career Goals."""
    goals_5yr: str = Field(..., min_length=1)
    goals_10yr: str = Field(..., min_length=1)
    goals_20yr: str = Field(..., min_length=1)


class LifestylePreferencesRequest(BaseModel):
    """Step 20 — Lifestyle Preferences."""
    lifestyle_preferences: List[str] = []


class AdditionalNotesRequest(BaseModel):
    """Step 21 — Additional Notes."""
    additional_notes: str = ""


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

class ReportGenerateRequest(BaseModel):
    """Trigger report generation for a completed session."""
    session_id: str


class ReportResponse(BaseModel):
    """Returned after a successful report generation."""
    session_id: str
    report_text: str
    pdf_path: Optional[str] = None
    message: str = "Report generated successfully."


# ---------------------------------------------------------------------------
# FIELD SCOPE & COMPARISON
# ---------------------------------------------------------------------------

class FieldScopeRequest(BaseModel):
    """Request body for the Field Scope Explorer (Menu 2)."""
    field_name: str = Field(..., min_length=1)


class FieldScopeResponse(BaseModel):
    """Full field-scope report as plain text."""
    field_name: str
    report_text: str
    pdf_path: Optional[str] = None


class FieldComparisonRequest(BaseModel):
    """Request body for the Field Comparison Explorer (Menu 3)."""
    field_names: List[str] = Field(..., min_items=2)

    @field_validator("field_names")
    @classmethod
    def at_least_two(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("At least two field names are required for comparison.")
        return v


class FieldComparisonResponse(BaseModel):
    """Full field-comparison report as plain text."""
    field_names: List[str]
    report_text: str
    pdf_path: Optional[str] = None


# ---------------------------------------------------------------------------
# CONFIG / METADATA  (for populating frontend dropdowns)
# ---------------------------------------------------------------------------

class ConfigResponse(BaseModel):
    """All dropdown/choice lists exported from config.py."""
    gender_options: List[str]
    secondary_system_options: List[str]
    higher_system_options: List[str]
    financial_status_options: List[str]
    learning_style_options: List[str]
    lifestyle_options: List[str]
    personality_types: List[str]
    subject_type_options: List[str]
    communication_skills: List[str]
    interest_fields: List[str]

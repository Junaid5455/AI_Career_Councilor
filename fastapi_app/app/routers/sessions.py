"""
routers/sessions.py
===================
Endpoints for managing the 21-step interview session lifecycle.

POST /sessions/                 → create a new session
GET  /sessions/{session_id}     → get current session state
DELETE /sessions/{session_id}   → discard a session

POST /sessions/{session_id}/steps/personal-info         (Step 2)
POST /sessions/{session_id}/steps/secondary-education   (Step 3)
POST /sessions/{session_id}/steps/higher-education      (Step 4)
POST /sessions/{session_id}/steps/subject-performance   (Step 5)
POST /sessions/{session_id}/steps/favourite-subject     (Step 6)
POST /sessions/{session_id}/steps/career-decision       (Step 7)
POST /sessions/{session_id}/steps/preferred-countries   (Step 8)
POST /sessions/{session_id}/steps/interest-ratings      (Step 9)
POST /sessions/{session_id}/steps/programming           (Step 10)
POST /sessions/{session_id}/steps/math                  (Step 11)
POST /sessions/{session_id}/steps/communication         (Step 12)
POST /sessions/{session_id}/steps/personality           (Step 13)
POST /sessions/{session_id}/steps/learning-style        (Step 14)
POST /sessions/{session_id}/steps/hobbies               (Step 15)
POST /sessions/{session_id}/steps/games                 (Step 16)
POST /sessions/{session_id}/steps/financial             (Step 17)
POST /sessions/{session_id}/steps/family                (Step 18)
POST /sessions/{session_id}/steps/career-goals          (Step 19)
POST /sessions/{session_id}/steps/lifestyle             (Step 20)
POST /sessions/{session_id}/steps/additional-notes      (Step 21)
"""

from fastapi import APIRouter, HTTPException

from app.session_store import (
    create_session, get_session,
    save_session_in_memory, delete_session,
)
from app.schemas import (
    SessionCreateResponse, SessionStateResponse, MessageResponse,
    PersonalInfoRequest, SecondaryEducationRequest, HigherEducationRequest,
    SubjectPerformanceRequest, FavouriteSubjectRequest, CareerDecisionRequest,
    PreferredCountriesRequest, InterestRatingsRequest,
    ProgrammingAssessmentRequest, MathAssessmentRequest,
    CommunicationSkillsRequest, PersonalityRequest, LearningStyleRequest,
    HobbiesRequest, FavouriteGamesRequest, FinancialBackgroundRequest,
    FamilyBackgroundRequest, CareerGoalsRequest,
    LifestylePreferencesRequest, AdditionalNotesRequest,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _require_session(session_id: str):
    """Fetches a session or raises 404."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session


def _apply_step(session, step_number: int, data: dict) -> dict:
    """Merges step data into profile, marks step complete, and persists."""
    profile = session["student_profile"]
    profile.update(data)
    if step_number not in session["steps_completed"]:
        session["steps_completed"].append(step_number)
    session["current_step"] = step_number + 1
    save_session_in_memory(session)
    return profile


def _session_state_response(session) -> SessionStateResponse:
    profile = session["student_profile"]
    return SessionStateResponse(
        session_id=profile["session_id"],
        current_step=session["current_step"],
        steps_completed=session["steps_completed"],
        collection_complete=profile.get("collection_complete", False),
        report_generated=profile.get("report_generated", False),
        session_start_time=session["session_start_time"],
        student_profile=profile,
    )


# ---------------------------------------------------------------------------
# SESSION LIFECYCLE
# ---------------------------------------------------------------------------

@router.post("/", response_model=SessionCreateResponse, status_code=201)
def create_new_session():
    """Start a brand-new 21-step counselling session."""
    session = create_session()
    sid = session["student_profile"]["session_id"]
    return SessionCreateResponse(
        session_id=sid,
        message=f"New session created. Begin with POST /sessions/{sid}/steps/personal-info",
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
def get_session_state(session_id: str):
    """Fetch the current state of a session (for resume/status display)."""
    session = _require_session(session_id)
    return _session_state_response(session)


@router.delete("/{session_id}", response_model=MessageResponse)
def discard_session(session_id: str):
    """Permanently delete a session (e.g. user starts over)."""
    existed = delete_session(session_id)
    if not existed:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return MessageResponse(message=f"Session '{session_id}' deleted.")


# ---------------------------------------------------------------------------
# STEP ENDPOINTS  (2 – 21)
# ---------------------------------------------------------------------------

@router.post("/{session_id}/steps/personal-info", response_model=SessionStateResponse)
def submit_personal_info(session_id: str, body: PersonalInfoRequest):
    """Step 2 — Personal Information."""
    session = _require_session(session_id)
    _apply_step(session, 2, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/secondary-education", response_model=SessionStateResponse)
def submit_secondary_education(session_id: str, body: SecondaryEducationRequest):
    """Step 3 — Secondary Education."""
    session = _require_session(session_id)
    _apply_step(session, 3, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/higher-education", response_model=SessionStateResponse)
def submit_higher_education(session_id: str, body: HigherEducationRequest):
    """Step 4 — Higher / Intermediate Education."""
    session = _require_session(session_id)
    _apply_step(session, 4, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/subject-performance", response_model=SessionStateResponse)
def submit_subject_performance(session_id: str, body: SubjectPerformanceRequest):
    """Step 5 — Subject-wise Performance."""
    session = _require_session(session_id)
    # Convert Pydantic models to plain dicts so storage stays JSON-serialisable
    perf = {subj: entry.model_dump() for subj, entry in body.subject_performance.items()}
    _apply_step(session, 5, {"subject_performance": perf})
    return _session_state_response(session)


@router.post("/{session_id}/steps/favourite-subject", response_model=SessionStateResponse)
def submit_favourite_subject(session_id: str, body: FavouriteSubjectRequest):
    """Step 6 — Favourite Subject & Topics."""
    session = _require_session(session_id)
    _apply_step(session, 6, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/career-decision", response_model=SessionStateResponse)
def submit_career_decision(session_id: str, body: CareerDecisionRequest):
    """Step 7 — Current Degree Plan."""
    session = _require_session(session_id)
    _apply_step(session, 7, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/preferred-countries", response_model=SessionStateResponse)
def submit_preferred_countries(session_id: str, body: PreferredCountriesRequest):
    """Step 8 — Study & Work Country Preferences."""
    session = _require_session(session_id)
    _apply_step(session, 8, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/interest-ratings", response_model=SessionStateResponse)
def submit_interest_ratings(session_id: str, body: InterestRatingsRequest):
    """Step 9 — Interest Field Ratings."""
    session = _require_session(session_id)
    _apply_step(session, 9, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/programming", response_model=SessionStateResponse)
def submit_programming(session_id: str, body: ProgrammingAssessmentRequest):
    """Step 10 — Programming Assessment."""
    session = _require_session(session_id)
    _apply_step(session, 10, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/math", response_model=SessionStateResponse)
def submit_math(session_id: str, body: MathAssessmentRequest):
    """Step 11 — Mathematics Assessment."""
    session = _require_session(session_id)
    _apply_step(session, 11, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/communication", response_model=SessionStateResponse)
def submit_communication(session_id: str, body: CommunicationSkillsRequest):
    """Step 12 — Communication Skills."""
    session = _require_session(session_id)
    _apply_step(session, 12, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/personality", response_model=SessionStateResponse)
def submit_personality(session_id: str, body: PersonalityRequest):
    """Step 13 — Personality."""
    session = _require_session(session_id)
    _apply_step(session, 13, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/learning-style", response_model=SessionStateResponse)
def submit_learning_style(session_id: str, body: LearningStyleRequest):
    """Step 14 — Learning Style."""
    session = _require_session(session_id)
    _apply_step(session, 14, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/hobbies", response_model=SessionStateResponse)
def submit_hobbies(session_id: str, body: HobbiesRequest):
    """Step 15 — Hobbies."""
    session = _require_session(session_id)
    _apply_step(session, 15, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/games", response_model=SessionStateResponse)
def submit_games(session_id: str, body: FavouriteGamesRequest):
    """Step 16 — Favourite Games."""
    session = _require_session(session_id)
    _apply_step(session, 16, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/financial", response_model=SessionStateResponse)
def submit_financial(session_id: str, body: FinancialBackgroundRequest):
    """Step 17 — Financial Background."""
    session = _require_session(session_id)
    _apply_step(session, 17, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/family", response_model=SessionStateResponse)
def submit_family(session_id: str, body: FamilyBackgroundRequest):
    """Step 18 — Family Background."""
    session = _require_session(session_id)
    _apply_step(session, 18, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/career-goals", response_model=SessionStateResponse)
def submit_career_goals(session_id: str, body: CareerGoalsRequest):
    """Step 19 — Career Goals."""
    session = _require_session(session_id)
    _apply_step(session, 19, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/lifestyle", response_model=SessionStateResponse)
def submit_lifestyle(session_id: str, body: LifestylePreferencesRequest):
    """Step 20 — Lifestyle Preferences."""
    session = _require_session(session_id)
    _apply_step(session, 20, body.model_dump())
    return _session_state_response(session)


@router.post("/{session_id}/steps/additional-notes", response_model=SessionStateResponse)
def submit_additional_notes(session_id: str, body: AdditionalNotesRequest):
    """Step 21 — Additional Notes. Marks collection as complete."""
    session = _require_session(session_id)
    _apply_step(session, 21, body.model_dump())
    # Mark interview complete after final step
    session["student_profile"]["collection_complete"] = True
    save_session_in_memory(session)
    return _session_state_response(session)

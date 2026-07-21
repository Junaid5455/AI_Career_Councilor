"""
app/repositories/session_repository.py
========================================
Database CRUD operations for Session and StudentProfile.

CONTRACT — this module must stay 100% compatible with the dict shape that
routers/sessions.py and routers/reports.py already consume.  Every public
function that returns a session returns the same nested dict that the old
in-memory store returned, so NO router or schema file needs to change.

The dict shape (matching storage.create_session_state / create_empty_profile):

{
    "current_step":      int,          # 1-22
    "steps_completed":   list[int],
    "session_start_time": str,         # "YYYY-MM-DD HH:MM:SS"
    "ai_report_text":    str,
    "report_file_path":  str,
    "total_sessions":    int,
    "student_profile": {
        "session_id":          str,    # "SES001"
        "collection_complete": bool,
        "report_generated":    bool,
        # ... all 40+ profile fields from create_empty_profile()
    }
}

How it integrates with session_store.py:
    session_store.py calls the functions here instead of its in-memory dict
    and sessions.json.  The public API of session_store.py is UNCHANGED.

Design rules:
  - Every function accepts a SQLAlchemy Session as its first argument.
  - All functions are synchronous (matching existing sync FastAPI routes).
  - Serialisation (ORM → dict) is handled here; callers never touch ORM objects.
  - Child table rows (SubjectPerformance, InterestRating, CommunicationSkill)
    are written atomically with the profile update inside a single transaction.
  - The session_code sequence (SES001, SES002 …) is owned by a PostgreSQL
    sequence, replacing the old in-memory counter that reset on restart.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, text
from sqlalchemy.orm import Session as DBSession

from app.models import (
    Session as SessionModel,
    StudentProfile,
    SubjectPerformance,
    InterestRating,
    CommunicationSkill,
)


# ---------------------------------------------------------------------------
# SEQUENCE — replaces storage.generate_session_id()
#
# The sequence is created once at module import using a dedicated AUTOCOMMIT
# connection that is completely outside any transaction block.
#
# Why AUTOCOMMIT is required:
#   PostgreSQL aborts the entire transaction on any error, including
#   "relation does not exist".  If we call nextval() inside a normal
#   session transaction and the sequence is missing, the transaction is
#   marked as aborted and every subsequent statement — including the
#   CREATE SEQUENCE fallback — is rejected with "InFailedSqlTransaction".
#   An AUTOCOMMIT connection has no transaction to abort, so CREATE SEQUENCE
#   runs cleanly and the normal session can nextval() immediately after.
# ---------------------------------------------------------------------------

_NEXT_CODE_SQL = text("SELECT nextval('session_code_seq')")


def _ensure_sequence_exists() -> None:
    """
    Creates session_code_seq if it does not already exist.
    Uses a raw AUTOCOMMIT connection so no transaction is involved.
    Called once at module import — safe to call multiple times (IF NOT EXISTS).
    """
    from app.database import engine
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text("CREATE SEQUENCE IF NOT EXISTS session_code_seq START 1 INCREMENT 1")
        )


# Create the sequence immediately when this module is first imported.
# This runs before any request arrives, so the first POST /sessions/ call
# will always find the sequence already in place.
_ensure_sequence_exists()


def _next_session_code(db: DBSession) -> str:
    """
    Returns the next SES### code (e.g. 'SES001') from the PostgreSQL sequence.
    The sequence is guaranteed to exist because _ensure_sequence_exists()
    ran at import time.
    """
    n = db.scalar(_NEXT_CODE_SQL)
    return f"SES{int(n):03d}"


# ---------------------------------------------------------------------------
# SERIALISATION — ORM objects → dict shape expected by routers
# ---------------------------------------------------------------------------

def _profile_to_dict(profile: Optional[StudentProfile]) -> Dict[str, Any]:
    """
    Converts a StudentProfile ORM row into the flat dict that was previously
    returned by storage.create_empty_profile() / create_session_state().

    The three child-table fields (subject_performance, interest_ratings,
    communication_skills) are re-assembled from their normalised rows into
    the nested dict/dict format the routers pass to report_generator.py.
    """
    if profile is None:
        from storage import create_empty_profile
        return create_empty_profile()

    # ── Re-assemble child-table fields ──────────────────────────────────────
    subject_performance: Dict[str, Any] = {}
    for sp in (profile.subject_performances or []):
        subject_performance[sp.subject_name] = {
            "marks":         float(sp.marks) if sp.marks is not None else None,
            "interest":      sp.interest,
            "difficulty":    sp.difficulty,
            "confidence":    sp.confidence,
            "hours_per_week": float(sp.hours_per_week),
        }

    interest_ratings: Dict[str, int] = {
        ir.field_name: ir.rating
        for ir in (profile.interest_ratings or [])
    }

    communication_skills: Dict[str, int] = {
        cs.skill_name: cs.score
        for cs in (profile.communication_skills or [])
    }

    return {
        # ── Identity (kept in profile dict for router compat) ────────────────
        "session_id":          profile.session.session_code if profile.session else None,
        "collection_complete": profile.session.collection_complete if profile.session else False,
        "report_generated":    profile.session.report_generated if profile.session else False,

        # ── Step 2: Personal Information ─────────────────────────────────────
        "name":               profile.name,
        "age":                profile.age,
        "gender":             profile.gender,
        "country":            profile.country,
        "city":               profile.city,
        "native_language":    profile.native_language,
        "education_language": profile.education_language,

        # ── Step 3: Secondary Education ───────────────────────────────────────
        "secondary_system":    profile.secondary_system,
        "secondary_year":      profile.secondary_year,
        "secondary_subjects":  profile.secondary_subjects or [],
        "secondary_marks":     float(profile.secondary_marks) if profile.secondary_marks is not None else None,
        "secondary_grade":     profile.secondary_grade,
        "secondary_completed": profile.secondary_completed,

        # ── Step 4: Higher Education ──────────────────────────────────────────
        "higher_system":       profile.higher_system,
        "higher_year":         profile.higher_year,
        "higher_subjects":     profile.higher_subjects or [],
        "higher_subject_marks": profile.higher_subject_marks or {},
        "higher_completed":    profile.higher_completed,

        # ── Step 5: Subject Performance (re-assembled from child rows) ────────
        "subject_performance": subject_performance,

        # ── Step 6: Favourite Subject ─────────────────────────────────────────
        "favourite_subject": profile.favourite_subject,
        "favourite_topics":  profile.favourite_topics or [],

        # ── Step 7: Career Decision ───────────────────────────────────────────
        "current_degree_plan": profile.current_degree_plan,

        # ── Step 8: Preferred Countries ───────────────────────────────────────
        "study_country": profile.study_country,
        "work_country":  profile.work_country,

        # ── Step 9: Interest Ratings (re-assembled from child rows) ───────────
        "interest_ratings": interest_ratings,

        # ── Step 10: Programming Assessment ──────────────────────────────────
        "has_programmed":          profile.has_programmed,
        "programming_languages":   profile.programming_languages or [],
        "programming_interest":    profile.programming_interest,
        "programming_experience":  profile.programming_experience,

        # ── Step 11: Mathematics Assessment ──────────────────────────────────
        "math_is_favourite": profile.math_is_favourite,
        "math_daily_ok":     profile.math_daily_ok,
        "math_career_ok":    profile.math_career_ok,

        # ── Step 12: Communication Skills (re-assembled from child rows) ──────
        "communication_skills": communication_skills,

        # ── Step 13: Personality ──────────────────────────────────────────────
        "personality_type":        profile.personality_type,
        "subject_type_preference": profile.subject_type_preference or [],

        # ── Step 14: Learning Style ───────────────────────────────────────────
        "learning_styles": profile.learning_styles or [],

        # ── Step 15: Hobbies ──────────────────────────────────────────────────
        "hobbies": profile.hobbies or [],

        # ── Step 16: Games ────────────────────────────────────────────────────
        "favourite_games": profile.favourite_games or [],

        # ── Step 17: Financial Background ─────────────────────────────────────
        "financial_status":  profile.financial_status,
        "education_budget":  profile.education_budget,

        # ── Step 18: Family Background ────────────────────────────────────────
        "parent_occupations":  profile.parent_occupations,
        "family_education":    profile.family_education,
        "family_expectations": profile.family_expectations,
        "family_business":     profile.family_business,

        # ── Step 19: Career Goals ─────────────────────────────────────────────
        "goals_5yr":  profile.goals_5yr,
        "goals_10yr": profile.goals_10yr,
        "goals_20yr": profile.goals_20yr,

        # ── Step 20: Lifestyle Preferences ────────────────────────────────────
        "lifestyle_preferences": profile.lifestyle_preferences or [],

        # ── Step 21: Additional Notes ─────────────────────────────────────────
        "additional_notes": profile.additional_notes,
    }


def _session_to_dict(
    session: SessionModel,
    ai_report_text: str = "",
    report_file_path: str = "",
) -> Dict[str, Any]:
    """
    Converts a Session ORM row (with its eagerly-loaded profile) into the
    exact nested dict shape the existing routers expect.

    Matches storage.create_session_state() return value precisely.
    """
    return {
        "current_step":      session.current_step,
        "steps_completed":   list(session.steps_completed or []),
        "session_start_time": session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "ai_report_text":    ai_report_text,
        "report_file_path":  report_file_path,
        "total_sessions":    0,   # legacy field — retained for compat
        "student_profile":   _profile_to_dict(session.profile),
    }


# ---------------------------------------------------------------------------
# PRIVATE HELPERS — child table writers
# ---------------------------------------------------------------------------

def _upsert_subject_performances(
    db: DBSession,
    profile: StudentProfile,
    subject_performance: Dict[str, Any],
) -> None:
    """
    Replaces all SubjectPerformance rows for this profile with the new data.
    Uses delete-then-insert (simpler than true upsert for this data shape).
    """
    # Delete existing rows for this profile
    for existing in list(profile.subject_performances):
        db.delete(existing)
    db.flush()   # execute DELETEs before INSERTs within same transaction

    for subject_name, perf in subject_performance.items():
        row = SubjectPerformance(
            profile_id=profile.id,
            subject_name=subject_name,
            marks=perf.get("marks"),
            interest=int(perf["interest"]),
            difficulty=int(perf["difficulty"]),
            confidence=int(perf["confidence"]),
            hours_per_week=float(perf["hours_per_week"]),
        )
        db.add(row)


def _upsert_interest_ratings(
    db: DBSession,
    profile: StudentProfile,
    interest_ratings: Dict[str, int],
) -> None:
    """
    Replaces all InterestRating rows for this profile with the new data.
    """
    for existing in list(profile.interest_ratings):
        db.delete(existing)
    db.flush()

    for field_name, rating in interest_ratings.items():
        row = InterestRating(
            profile_id=profile.id,
            field_name=field_name,
            rating=int(rating),
        )
        db.add(row)


def _upsert_communication_skills(
    db: DBSession,
    profile: StudentProfile,
    communication_skills: Dict[str, int],
) -> None:
    """
    Replaces all CommunicationSkill rows for this profile with the new data.
    """
    for existing in list(profile.communication_skills):
        db.delete(existing)
    db.flush()

    for skill_name, score in communication_skills.items():
        row = CommunicationSkill(
            profile_id=profile.id,
            skill_name=skill_name,
            score=int(score),
        )
        db.add(row)


def _apply_profile_fields(
    profile: StudentProfile,
    data: Dict[str, Any],
) -> None:
    """
    Maps the flat profile dict fields coming from a step submission onto the
    StudentProfile ORM object.

    The three child-table fields (subject_performance, interest_ratings,
    communication_skills) are excluded here — they are handled separately
    by _upsert_* helpers because they live in child tables.

    All other fields map 1-to-1 between the dict key and the ORM column name.
    """
    # Fields that live in child tables — handled separately
    CHILD_TABLE_FIELDS = {
        "subject_performance",
        "interest_ratings",
        "communication_skills",
    }

    # Fields that live on Session, not StudentProfile
    SESSION_LEVEL_FIELDS = {
        "session_id",
        "collection_complete",
        "report_generated",
    }

    # All valid StudentProfile column names
    PROFILE_COLUMNS = {
        "name", "age", "gender", "country", "city",
        "native_language", "education_language",
        "secondary_system", "secondary_year", "secondary_subjects",
        "secondary_marks", "secondary_grade", "secondary_completed",
        "higher_system", "higher_year", "higher_subjects",
        "higher_subject_marks", "higher_completed",
        "favourite_subject", "favourite_topics",
        "current_degree_plan", "study_country", "work_country",
        "has_programmed", "programming_languages",
        "programming_interest", "programming_experience",
        "math_is_favourite", "math_daily_ok", "math_career_ok",
        "personality_type", "subject_type_preference",
        "learning_styles", "hobbies", "favourite_games",
        "financial_status", "education_budget",
        "parent_occupations", "family_education",
        "family_expectations", "family_business",
        "goals_5yr", "goals_10yr", "goals_20yr",
        "lifestyle_preferences", "additional_notes",
    }

    for key, value in data.items():
        if key in CHILD_TABLE_FIELDS or key in SESSION_LEVEL_FIELDS:
            continue
        if key in PROFILE_COLUMNS:
            setattr(profile, key, value)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def create_session(db: DBSession) -> Dict[str, Any]:
    """
    Creates a new Session row + an empty StudentProfile row in one transaction.
    Returns the session dict (same shape as storage.create_session_state()).

    Replaces: session_store.create_session()
    """
    session_code = _next_session_code(db)

    session = SessionModel(
        session_code=session_code,
        current_step=1,
        steps_completed=[],
        collection_complete=False,
        report_generated=False,
        status="active",
    )
    db.add(session)
    db.flush()   # get session.id without committing, so profile can FK to it

    profile = StudentProfile(
        session_id=session.id,
        user_id=None,
    )
    db.add(profile)
    db.commit()

    # Reload with relationships populated
    db.refresh(session)
    db.refresh(profile)

    return _session_to_dict(session)


def get_session(db: DBSession, session_code: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a Session by its human-readable code (e.g. "SES001").
    Returns the session dict or None if not found.

    Replaces: session_store.get_session()
    """
    stmt = (
        select(SessionModel)
        .where(SessionModel.session_code == session_code)
    )
    session = db.scalars(stmt).first()
    if session is None:
        return None

    # Eagerly load child rows so _profile_to_dict can access them
    _load_profile_children(db, session.profile)

    # Fetch report text and pdf path from the most recent career report if any
    ai_report_text, report_file_path = _get_latest_report_content(db, session)

    return _session_to_dict(session, ai_report_text, report_file_path)


def save_session(
    db: DBSession,
    session_dict: Dict[str, Any],
) -> None:
    """
    Persists all changes from a session dict back to PostgreSQL.
    Handles the Session row, StudentProfile row, and all three child tables
    in a single atomic transaction.

    Replaces: session_store.save_session_in_memory()

    Parameters
    ----------
    db           : active SQLAlchemy session
    session_dict : the same nested dict the routers pass around, which may
                   have been mutated by _apply_step() in sessions.py
    """
    profile_dict = session_dict.get("student_profile", {})
    session_code = profile_dict.get("session_id")   # e.g. "SES001"

    if not session_code:
        raise ValueError("session_dict is missing student_profile.session_id")

    # Fetch the Session row — use joinedload so session.profile is populated
    # within this transaction without relying on lazy loading, which can return
    # None when passive_deletes=True is set on the relationship.
    from sqlalchemy.orm import joinedload
    stmt = (
        select(SessionModel)
        .options(joinedload(SessionModel.profile))
        .where(SessionModel.session_code == session_code)
    )
    session = db.scalars(stmt).first()
    if session is None:
        raise LookupError(f"Session '{session_code}' not found in database.")

    # ── Update Session-level fields ──────────────────────────────────────────
    session.current_step        = session_dict.get("current_step", session.current_step)
    session.steps_completed     = session_dict.get("steps_completed", session.steps_completed)
    session.collection_complete = profile_dict.get("collection_complete", session.collection_complete)
    session.report_generated    = profile_dict.get("report_generated", session.report_generated)

    # Mark completed once all steps done
    if session.collection_complete and session.status == "active":
        session.status = "completed"

    # ── Fetch StudentProfile directly by FK — never rely on lazy relationship ─
    # Fetching via session.profile with passive_deletes=True can return None
    # even when the profile exists, because SQLAlchemy skips the SELECT.
    # A direct query guarantees we always get the real row.
    profile_stmt = select(StudentProfile).where(StudentProfile.session_id == session.id)
    profile = db.scalars(profile_stmt).first()
    if profile is None:
        # Guard: should never happen — profile is created atomically with session
        profile = StudentProfile(session_id=session.id)
        db.add(profile)
        db.flush()

    _apply_profile_fields(profile, profile_dict)

    # ── Update child table rows ───────────────────────────────────────────────
    # Load existing child rows explicitly before upsert so the delete step
    # inside each _upsert_* helper has the full current list to work with.
    _load_profile_children(db, profile)

    subject_perf = profile_dict.get("subject_performance")
    if subject_perf:
        _upsert_subject_performances(db, profile, subject_perf)

    interest_ratings = profile_dict.get("interest_ratings")
    if interest_ratings:
        _upsert_interest_ratings(db, profile, interest_ratings)

    comm_skills = profile_dict.get("communication_skills")
    if comm_skills:
        _upsert_communication_skills(db, profile, comm_skills)

    db.commit()


def delete_session(db: DBSession, session_code: str) -> bool:
    """
    Permanently deletes a Session row.
    PostgreSQL CASCADE removes the StudentProfile and all child rows.
    Returns True if a row was deleted, False if not found.

    Replaces: session_store.delete_session()
    """
    stmt = select(SessionModel).where(SessionModel.session_code == session_code)
    session = db.scalars(stmt).first()
    if session is None:
        return False
    db.delete(session)
    db.commit()
    return True


def list_active_sessions(db: DBSession) -> List[str]:
    """
    Returns all session_code values for sessions with status='active'.
    Replaces: session_store.list_session_ids()
    """
    stmt = select(SessionModel.session_code).where(
        SessionModel.status == "active"
    )
    return list(db.scalars(stmt).all())


# ---------------------------------------------------------------------------
# STARTUP LOADER  — replaces session_store.load_all_sessions_from_disk()
# ---------------------------------------------------------------------------

def warm_cache_from_db(db: DBSession) -> None:
    """
    Called once from main.py lifespan() instead of load_all_sessions_from_disk().

    Unlike the old file-based loader, there is nothing to load into memory —
    PostgreSQL is the source of truth and is queried on every request.
    This function validates the DB connection and logs active session count,
    replacing the startup print from the old JSON loader.
    """
    stmt = select(func.count()).select_from(SessionModel).where(
        SessionModel.status == "active"
    )
    active_count = db.scalar(stmt) or 0
    print(f"  >> PostgreSQL session store ready. Active sessions: {active_count}")


# ---------------------------------------------------------------------------
# PRIVATE HELPERS — lazy child loading and report content lookup
# ---------------------------------------------------------------------------

def _load_profile_children(db: DBSession, profile: Optional[StudentProfile]) -> None:
    """
    Forces the three child-table relationship collections to load if they
    haven't been fetched yet.  Called before serialising a profile to dict.

    SQLAlchemy lazy-loads these by default; this helper makes the loading
    explicit so we control when the extra queries fire.
    """
    if profile is None:
        return
    # Accessing the attribute triggers a SELECT if not already loaded
    _ = profile.subject_performances
    _ = profile.interest_ratings
    _ = profile.communication_skills


def _get_latest_report_content(
    db: DBSession,
    session: SessionModel,
) -> tuple[str, str]:
    """
    Returns (ai_report_text, report_file_path) from the most recent career
    Report row for this session, or ("", "") if none exists yet.

    These two fields live in the Report table in the new design but were
    stored directly on the session dict in the old design.  This helper
    bridges that gap so _session_to_dict() can populate them without the
    routers needing to know where they come from.
    """
    from app.models import Report
    stmt = (
        select(Report)
        .where(
            Report.session_id == session.id,
            Report.report_type == "career",
            Report.status == "complete",
        )
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    report = db.scalars(stmt).first()
    if report is None:
        return ("", "")
    return (report.report_text or "", report.pdf_path or "")
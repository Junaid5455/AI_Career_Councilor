"""
storage.py
==========
Data storage design: student profile schema, session state,
save/load to disk, profile completeness check.
No user-input or API logic here.
"""

import os
import json
import copy
from datetime import datetime

from config import SESSIONS_FILE, REPORT_DIR, INTEREST_FIELDS


# ---------------------------------------------------------------------------
# SESSION ID COUNTER
# ---------------------------------------------------------------------------

_session_counter = 0


def generate_session_id():
    """Returns next session ID: SES001, SES002, ..."""
    global _session_counter
    _session_counter += 1
    return f"SES{_session_counter:03d}"


# ---------------------------------------------------------------------------
# PROFILE SCHEMA
# ---------------------------------------------------------------------------

def create_empty_profile():
    """Returns a new student profile dict with all keys set to None/[]/empty."""
    return {
        "name": None,
        "age": None,
        "gender": None,
        "country": None,
        "city": None,
        "native_language": None,
        "education_language": None,

        "secondary_system": None,
        "secondary_year": None,
        "secondary_subjects": [],
        "secondary_marks": None,
        "secondary_grade": None,
        "secondary_completed": True,        # False if student chose "Continue"

        "higher_system": None,
        "higher_year": None,
        "higher_subjects": [],
        "higher_subject_marks": {},         # A-Level / FSc / Other named subject marks
        "higher_completed": True,           # False if student chose "Continue"

        "subject_performance": {},

        "favourite_subject": None,
        "favourite_topics": [],

        "current_degree_plan": None,

        "study_country": None,
        "work_country": None,

        "interest_ratings": {},

        "has_programmed": None,
        "programming_languages": [],
        "programming_interest": None,
        "programming_experience": None,

        "math_is_favourite": None,
        "math_daily_ok": None,
        "math_career_ok": None,

        "communication_skills": {},

        "personality_type": None,
        "subject_type_preference": [],

        "learning_styles": [],
        "hobbies": [],
        "favourite_games": [],

        "financial_status": None,
        "education_budget": None,

        "parent_occupations": None,
        "family_education": None,
        "family_expectations": None,
        "family_business": None,

        "goals_5yr": None,
        "goals_10yr": None,
        "goals_20yr": None,

        "lifestyle_preferences": [],
        "additional_notes": None,

        "session_id": None,
        "collection_complete": False,
        "report_generated": False,
    }


def update_profile(profile, key, value):
    """Safely updates one field of the profile dict."""
    profile[key] = value
    return profile


# Required sections that must be filled for the profile to be "complete"
_REQUIRED_SECTIONS = [
    "name", "age", "gender", "country", "secondary_system",
    "higher_system", "favourite_subject", "study_country",
    "interest_ratings", "has_programmed", "communication_skills",
    "personality_type", "learning_styles", "hobbies",
    "financial_status", "parent_occupations", "goals_5yr",
    "lifestyle_preferences",
]


def is_profile_complete(profile):
    """Returns True if all required sections have been collected."""
    for key in _REQUIRED_SECTIONS:
        value = profile.get(key)
        if value is None:
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
    return True


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------

def create_session_state():
    """Returns a brand-new session state dictionary."""
    session = {
        "current_step": 1,
        "steps_completed": [],
        "student_profile": create_empty_profile(),
        "ai_report_text": "",
        "report_file_path": "",
        "session_start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_sessions": 0,
    }
    session["student_profile"]["session_id"] = generate_session_id()
    return session


# ---------------------------------------------------------------------------
# SAVE / LOAD
# ---------------------------------------------------------------------------

def save_session(session):
    """Saves session dict to sessions.json (for recovery)."""
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, default=str)
        return True
    except (IOError, OSError) as e:
        print(f"  >> Warning: could not save session ({e}).")
        return False


def load_last_session():
    """Loads the most recent incomplete session (resume feature)."""
    if not os.path.exists(SESSIONS_FILE):
        return None
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            session = json.load(f)
    except (IOError, OSError, json.JSONDecodeError):
        return None
    profile = session.get("student_profile", {})
    if profile and not profile.get("collection_complete", False):
        return session
    return None


# ---------------------------------------------------------------------------
# REPORTS FOLDER
# ---------------------------------------------------------------------------

def ensure_reports_dir():
    """Create the reports/ folder automatically if it does not exist."""
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)


# ---------------------------------------------------------------------------
# TEST DATA  (pre-loaded profile used by tests.py)
# ---------------------------------------------------------------------------

def _build_test_profile():
    """Builds and returns a complete test student profile."""
    profile = create_empty_profile()
    profile.update({
        "name": "Test Student",
        "age": 18,
        "gender": "Male",
        "country": "Pakistan",
        "city": "Lahore",
        "native_language": "Urdu",
        "education_language": "English",

        "secondary_system": "Matric",
        "secondary_year": 2022,
        "secondary_subjects": ["Math", "Physics", "Chemistry"],
        "secondary_marks": 85.5,
        "secondary_grade": "A",
        "secondary_completed": True,

        "higher_system": "FSc",
        "higher_year": 2024,
        "higher_subjects": ["Computer Science", "Mathematics", "Physics"],
        "higher_subject_marks": {
            "Computer Science": "95%",
            "Mathematics": "90%",
            "Physics": "78%",
        },
        "higher_completed": True,

        "subject_performance": {
            "Math": {"marks": 90, "interest": 9, "difficulty": 5,
                     "confidence": 8, "hours_per_week": 10},
            "Physics": {"marks": 78, "interest": 6, "difficulty": 7,
                        "confidence": 6, "hours_per_week": 6},
            "Computer Science": {"marks": 95, "interest": 10, "difficulty": 4,
                                 "confidence": 9, "hours_per_week": 14},
        },

        "favourite_subject": "Computer Science",
        "favourite_topics": ["Algorithms", "Web Development"],

        "current_degree_plan": "Bachelor's in Computer Science",

        "study_country": "UK",
        "work_country": "USA",

        "interest_ratings": {field: 4 for field in INTEREST_FIELDS},

        "has_programmed": True,
        "programming_languages": ["Python", "JavaScript"],
        "programming_interest": 9,
        "programming_experience": 24,

        "math_is_favourite": True,
        "math_daily_ok": True,
        "math_career_ok": True,

        "communication_skills": {
            "speaking": 8, "writing": 7, "listening": 7, "leadership": 9,
            "teamwork": 8, "public_speaking": 7, "negotiation": 6,
            "presentation": 8,
        },

        "personality_type": "Ambivert",
        "subject_type_preference": ["Science", "Technological", "Practical"],

        "learning_styles": ["Videos", "Practical Work"],
        "hobbies": ["Coding", "Gaming", "Reading"],
        "favourite_games": ["Chess", "FIFA", "Valorant"],

        "financial_status": "Need Scholarship",
        "education_budget": "PKR 500,000 total",

        "parent_occupations": "Father: Engineer, Mother: Teacher",
        "family_education": "Father: BSc Engineering",
        "family_expectations": "Become an Engineer or Doctor",
        "family_business": "None",

        "goals_5yr": "Software Engineer at Google",
        "goals_10yr": "Team Lead or own startup",
        "goals_20yr": "Founder of a tech company",

        "lifestyle_preferences": ["Remote Work", "Freelancing"],
        "additional_notes": "I have a passion for building useful software products.",

        "session_id": "SES999",
        "collection_complete": True,
        "report_generated": False,
    })
    # Boost a few interests so the AI strongly recommends STEM
    profile["interest_ratings"]["Engineering"] = 9
    profile["interest_ratings"]["Mathematics"] = 8
    return profile


TEST_PROFILE = _build_test_profile()


def get_test_profile():
    """Returns a fresh deep-copy of the test profile (callers may mutate freely)."""
    return copy.deepcopy(TEST_PROFILE)


def get_empty_profile_for_test():
    """Returns an empty profile, useful for is_profile_complete() tests."""
    return create_empty_profile()

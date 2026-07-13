"""
tests/test_api.py
=================
Automated tests for the EduPath AI FastAPI layer.
Uses FastAPI's built-in TestClient (wraps httpx) — no running server needed.

Run with:
    pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def session_id():
    """Creates a fresh session and returns its ID."""
    resp = client.post("/sessions/")
    assert resp.status_code == 201
    return resp.json()["session_id"]


@pytest.fixture
def completed_session_id(session_id):
    """Runs a session through all 21 steps and returns session_id."""
    sid = session_id

    client.post(f"/sessions/{sid}/steps/personal-info", json={
        "name": "Test Student", "age": 18, "gender": "Male",
        "country": "Pakistan", "city": "Lahore",
        "native_language": "Urdu", "education_language": "English",
    })
    client.post(f"/sessions/{sid}/steps/secondary-education", json={
        "secondary_system": "Matric", "secondary_year": 2022,
        "secondary_subjects": ["Math", "Physics", "Chemistry"],
        "secondary_marks": 85.5, "secondary_grade": "A",
        "secondary_completed": True,
    })
    client.post(f"/sessions/{sid}/steps/higher-education", json={
        "higher_system": "FSc", "higher_year": 2024,
        "higher_subjects": ["Math", "Physics", "Computer Science"],
        "higher_subject_marks": {}, "higher_completed": True,
    })
    client.post(f"/sessions/{sid}/steps/subject-performance", json={
        "subject_performance": {
            "Math": {"marks": 90, "interest": 9, "difficulty": 5,
                     "confidence": 8, "hours_per_week": 10},
        }
    })
    client.post(f"/sessions/{sid}/steps/favourite-subject", json={
        "favourite_subject": "Computer Science",
        "favourite_topics": ["Algorithms", "Web Dev"],
    })
    client.post(f"/sessions/{sid}/steps/career-decision", json={
        "current_degree_plan": "Bachelor's in CS"
    })
    client.post(f"/sessions/{sid}/steps/preferred-countries", json={
        "study_country": "UK", "work_country": "USA"
    })
    client.post(f"/sessions/{sid}/steps/interest-ratings", json={
        "interest_ratings": {"Mathematics": 8, "Engineering": 9}
    })
    client.post(f"/sessions/{sid}/steps/programming", json={
        "has_programmed": True,
        "programming_languages": ["Python"],
        "programming_interest": 9,
        "programming_experience": 24,
    })
    client.post(f"/sessions/{sid}/steps/math", json={
        "math_is_favourite": True, "math_daily_ok": True, "math_career_ok": True
    })
    client.post(f"/sessions/{sid}/steps/communication", json={
        "communication_skills": {"speaking": 8, "writing": 7}
    })
    client.post(f"/sessions/{sid}/steps/personality", json={
        "personality_type": "Ambivert",
        "subject_type_preference": ["Science", "Technological"],
    })
    client.post(f"/sessions/{sid}/steps/learning-style", json={
        "learning_styles": ["Videos", "Practical Work"]
    })
    client.post(f"/sessions/{sid}/steps/hobbies", json={
        "hobbies": ["Coding", "Reading"]
    })
    client.post(f"/sessions/{sid}/steps/games", json={
        "favourite_games": ["Chess"]
    })
    client.post(f"/sessions/{sid}/steps/financial", json={
        "financial_status": "Need Scholarship",
        "education_budget": "PKR 500,000",
    })
    client.post(f"/sessions/{sid}/steps/family", json={
        "parent_occupations": "Father: Engineer",
        "family_education": "BSc Engineering",
        "family_expectations": "Engineer or Doctor",
        "family_business": "None",
    })
    client.post(f"/sessions/{sid}/steps/career-goals", json={
        "goals_5yr": "Software Engineer",
        "goals_10yr": "Tech Lead",
        "goals_20yr": "Startup Founder",
    })
    client.post(f"/sessions/{sid}/steps/lifestyle", json={
        "lifestyle_preferences": ["Remote Work"]
    })
    client.post(f"/sessions/{sid}/steps/additional-notes", json={
        "additional_notes": "Passionate about software."
    })
    return sid


# ---------------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

def test_get_config_options():
    resp = client.get("/config/options")
    assert resp.status_code == 200
    data = resp.json()
    assert "gender_options" in data
    assert "interest_fields" in data
    assert len(data["gender_options"]) > 0


# ---------------------------------------------------------------------------
# SESSION LIFECYCLE
# ---------------------------------------------------------------------------

def test_create_session():
    resp = client.post("/sessions/")
    assert resp.status_code == 201
    body = resp.json()
    assert "session_id" in body
    assert body["session_id"].startswith("SES")


def test_get_session_state(session_id):
    resp = client.get(f"/sessions/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["current_step"] == 1
    assert body["collection_complete"] is False


def test_get_unknown_session():
    resp = client.get("/sessions/SESXXX")
    assert resp.status_code == 404


def test_delete_session(session_id):
    resp = client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 200
    # Confirm it's gone
    resp2 = client.get(f"/sessions/{session_id}")
    assert resp2.status_code == 404


# ---------------------------------------------------------------------------
# STEP SUBMISSIONS
# ---------------------------------------------------------------------------

def test_step2_personal_info(session_id):
    resp = client.post(f"/sessions/{session_id}/steps/personal-info", json={
        "name": "Ali Khan", "age": 18, "gender": "Male",
        "country": "Pakistan", "city": "Karachi",
        "native_language": "Urdu", "education_language": "English",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert 2 in body["steps_completed"]
    assert body["student_profile"]["name"] == "Ali Khan"


def test_step2_invalid_age(session_id):
    resp = client.post(f"/sessions/{session_id}/steps/personal-info", json={
        "name": "Ali Khan", "age": 5,   # below min=10
        "gender": "Male", "country": "Pakistan", "city": "Karachi",
        "native_language": "Urdu", "education_language": "English",
    })
    assert resp.status_code == 422   # Pydantic validation error


def test_step9_invalid_rating(session_id):
    resp = client.post(f"/sessions/{session_id}/steps/interest-ratings", json={
        "interest_ratings": {"Mathematics": 15}   # above max=10
    })
    assert resp.status_code == 422


def test_full_interview_marks_complete(completed_session_id):
    resp = client.get(f"/sessions/{completed_session_id}")
    assert resp.status_code == 200
    assert resp.json()["collection_complete"] is True


# ---------------------------------------------------------------------------
# REPORT GENERATION — guarded so it doesn't call real DeepSeek in CI
# ---------------------------------------------------------------------------

def test_generate_career_report_incomplete_session(session_id):
    """Attempting to generate a report before completing all steps → 400."""
    resp = client.post("/reports/career", json={"session_id": session_id})
    assert resp.status_code == 400


def test_generate_career_report_unknown_session():
    resp = client.post("/reports/career", json={"session_id": "SESXXX"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# FIELD SCOPE / COMPARISON VALIDATION
# ---------------------------------------------------------------------------

def test_field_comparison_requires_two_fields():
    resp = client.post("/reports/field-comparison", json={"field_names": ["Medicine"]})
    assert resp.status_code == 422

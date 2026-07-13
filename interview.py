"""
interview.py
============
The 21-step interactive interview that collects a student's full profile.
Each collect_* function handles one step, returns a dict of key→value pairs
that run_full_interview() merges into the session profile.
"""

from datetime import datetime

from config import (
    GENDER_OPTIONS, SECONDARY_SYSTEM_OPTIONS, HIGHER_SYSTEM_OPTIONS,
    FINANCIAL_STATUS_OPTIONS, LEARNING_STYLE_OPTIONS, LIFESTYLE_OPTIONS,
    PERSONALITY_TYPES, SUBJECT_TYPE_OPTIONS, COMMUNICATION_SKILLS,
    INTEREST_FIELDS,
)
from validators import (
    get_valid_int, get_valid_float, get_valid_choice,
    get_text, get_yes_no, get_rating, get_multiselect,
)
from storage import update_profile, save_session
from utils import display_separator


# ---------------------------------------------------------------------------
# STEP 2 — Personal Information
# ---------------------------------------------------------------------------

def collect_personal_info():
    display_separator("STEP 2: PERSONAL INFORMATION")
    return {
        "name":               get_text("Full Name: "),
        "age":                get_valid_int("Age: ", 10, 60),
        "gender":             get_valid_choice("Select Gender:", GENDER_OPTIONS),
        "country":            get_text("Country: "),
        "city":               get_text("City: "),
        "native_language":    get_text("Native Language: "),
        "education_language": get_text("Language of Education: "),
    }


# ---------------------------------------------------------------------------
# STEP 3 — Secondary Education
# ---------------------------------------------------------------------------

def collect_secondary_education():
    display_separator("STEP 3: SECONDARY EDUCATION")
    secondary_system = get_valid_choice("Select Secondary System:", SECONDARY_SYSTEM_OPTIONS)
    current_year = datetime.now().year

    # 1. Subjects first
    subjects_raw = get_text("List subjects studied (comma-separated): ")
    secondary_subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]

    # 2. Year of Completion — with a "Continue" option for students still studying
    year_options = (
        [str(y) for y in range(1990, current_year + 1)]
        + ["Continue (Still Studying)"]
    )
    print("\n  Year of Completion:")
    print("  (Select a year if completed, or choose 'Continue' if still studying)\n")
    year_choice = get_valid_choice("Select Year of Completion:", year_options)

    secondary_completed = (year_choice != "Continue (Still Studying)")
    secondary_year      = int(year_choice) if secondary_completed else None

    # 3. Percentage and Grade — only if already completed
    secondary_marks = None
    secondary_grade = None
    if secondary_completed:
        secondary_marks = get_valid_float("Overall Percentage/Marks (0-100): ", 0, 100)
        secondary_grade = get_text("Overall Grade (e.g. A+, A, B): ")

    return {
        "secondary_system":    secondary_system,
        "secondary_year":      secondary_year,
        "secondary_subjects":  secondary_subjects,
        "secondary_marks":     secondary_marks,
        "secondary_grade":     secondary_grade,
        "secondary_completed": secondary_completed,
    }


# ---------------------------------------------------------------------------
# STEP 4 — Higher / Intermediate Education
# ---------------------------------------------------------------------------

def _collect_subjects_and_completion(system_label, current_year):
    """Shared helper for FSc and A-Level branches.

    1. Asks the student to enter their subject names.
    2. Asks Year of Completion with a 'Continue (Still Studying)' option.
    3. If completed, asks marks/grade for each subject.
    Returns (higher_subjects, higher_subject_marks, higher_year, higher_completed).
    """
    # Step 1 — subject names
    subjects_raw = get_text(
        f"Write down your {system_label} subjects (comma-separated): ")
    higher_subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]

    # Step 2 — year with Continue option
    print("\n  Year of Completion:")
    print("  (Select a year if completed, or choose 'Continue' if still studying)\n")
    year_options = (
        [str(y) for y in range(1990, current_year + 1)]
        + ["Continue (Still Studying)"]
    )
    year_choice      = get_valid_choice("Select Year of Completion:", year_options)
    higher_completed = (year_choice != "Continue (Still Studying)")
    higher_year      = int(year_choice) if higher_completed else None

    # Marks/grades are collected in Step 5 (Subject-wise Performance),
    # so we do NOT ask for them here to avoid asking the user twice.
    higher_subject_marks = {}

    return higher_subjects, higher_subject_marks, higher_year, higher_completed


def collect_higher_education():
    display_separator("STEP 4: HIGHER / INTERMEDIATE EDUCATION")
    higher_system = get_valid_choice("Select Higher Education System:", HIGHER_SYSTEM_OPTIONS)
    current_year  = datetime.now().year

    # ── FSc: identical workflow to A-Level — student enters own subjects ──────
    if higher_system == "FSc":
        subjs, marks, year, completed = _collect_subjects_and_completion("FSc", current_year)
        return {
            "higher_system":        higher_system,
            "higher_year":          year,
            "higher_subjects":      subjs,
            "higher_subject_marks": marks,
            "higher_completed":     completed,
        }

    # ── A-Level: student enters own subjects ──────────────────────────────────
    if higher_system == "A-Level":
        subjs, marks, year, completed = _collect_subjects_and_completion("A-Level", current_year)
        return {
            "higher_system":        higher_system,
            "higher_year":          year,
            "higher_subjects":      subjs,
            "higher_subject_marks": marks,
            "higher_completed":     completed,
        }

    # ── Other: student names each subject individually and provides marks ─────
    print("\n  Enter the name and marks for each of your subjects:")
    higher_subjects      = []
    higher_subject_marks = {}
    for i in range(1, 4):
        subj_name  = get_text(f"  Name of Subject {i}: ")
        subj_marks = get_valid_float(
            f"  Marks/Percentage in {subj_name} (0-100): ", 0, 100)
        higher_subjects.append(subj_name)
        higher_subject_marks[subj_name] = subj_marks

    higher_year = get_valid_int(
        f"Year of Completion/Expected (1990-{current_year + 5}): ",
        1990, current_year + 5)

    return {
        "higher_system":        higher_system,
        "higher_year":          higher_year,
        "higher_subjects":      higher_subjects,
        "higher_subject_marks": higher_subject_marks,
        "higher_completed":     True,
    }


# ---------------------------------------------------------------------------
# STEP 5 — Subject Performance (per subject)
# ---------------------------------------------------------------------------

def collect_subject_performance(subjects, existing_marks=None):
    """Collects performance data for each higher-education subject.

    Marks entered in Step 4 are passed in via existing_marks so the user
    is never asked to re-enter them here.  Only interest, difficulty,
    confidence, and hours/week are prompted in this step.
    """
    display_separator("STEP 5: SUBJECT-WISE PERFORMANCE")
    if existing_marks is None:
        existing_marks = {}
    subject_performance = {}
    for subject in subjects:
        print(f"\n--- {subject} ---")
        # Re-use the mark already recorded in Step 4 when available;
        # only ask if it is genuinely missing.
        if subject in existing_marks:
            try:
                marks = float(str(existing_marks[subject]).replace("%", "").strip())
                print(f"  Marks/Percentage in {subject}: {marks} (from Step 4)")
            except (ValueError, TypeError):
                marks = get_valid_float(
                    f"  Marks/Percentage in {subject} (0-100): ", 0, 100)
        else:
            marks = get_valid_float(
                f"  Marks/Percentage in {subject} (0-100): ", 0, 100)
        subject_performance[subject] = {
            "marks":          marks,
            "interest":       get_rating("  Interest level", subject),
            "difficulty":     get_rating("  Difficulty level", subject),
            "confidence":     get_rating("  Confidence level", subject),
            "hours_per_week": get_valid_float(
                f"  Hours/week spent on {subject}: ", 0, 80),
        }
    return {"subject_performance": subject_performance}


# ---------------------------------------------------------------------------
# STEP 6 — Favourite Subject
# ---------------------------------------------------------------------------

def collect_favourite_subject():
    display_separator("STEP 6: FAVOURITE SUBJECT")
    favourite_subject = get_text(
        "Favourite Subject (you can enter multiple subjects, separated by commas): ")
    topics_raw = get_text("Favourite topics within it (comma-separated): ")
    return {
        "favourite_subject": favourite_subject,
        "favourite_topics":  [t.strip() for t in topics_raw.split(",") if t.strip()],
    }


# ---------------------------------------------------------------------------
# STEP 7 — Career / Degree Decision
# ---------------------------------------------------------------------------

def collect_career_decision():
    display_separator("STEP 7: CAREER / DEGREE DECISION")
    plan = get_text("Current degree plan / field of interest (or 'None'): ", allow_blank=True)
    return {"current_degree_plan": plan if plan else "None"}


# ---------------------------------------------------------------------------
# STEP 8 — Preferred Countries
# ---------------------------------------------------------------------------

def collect_preferred_countries():
    display_separator("STEP 8: PREFERRED STUDY / WORK COUNTRIES")
    return {
        "study_country": get_text("Preferred country to study in: "),
        "work_country":  get_text("Preferred country to work in: "),
    }


# ---------------------------------------------------------------------------
# STEP 9 — Interest Ratings
# ---------------------------------------------------------------------------

def collect_interest_ratings():
    display_separator("STEP 9: INTEREST RATINGS (1-10)")
    # "Mathematics" is excluded here — it is assessed separately in
    # Step 11 (Mathematics Assessment) to avoid asking twice.
    _SKIP = {"Mathematics"}
    interest_ratings = {}
    for field in INTEREST_FIELDS:
        if field in _SKIP:
            continue
        interest_ratings[field] = get_rating("Rate your interest", field)
    return {"interest_ratings": interest_ratings}


# ---------------------------------------------------------------------------
# STEP 10 — Programming Assessment
# ---------------------------------------------------------------------------

def collect_programming_assessment():
    display_separator("STEP 10: PROGRAMMING ASSESSMENT")
    has_programmed       = get_yes_no("Have you ever written computer programs before?")
    programming_languages = []
    programming_interest  = 0
    programming_experience = 0
    if has_programmed:
        programming_interest   = get_rating("Rate your interest in programming")
        langs_raw              = get_text("Which languages have you used? (comma-separated): ")
        programming_languages  = [l.strip() for l in langs_raw.split(",") if l.strip()]
        programming_experience = get_valid_int("Months of programming experience: ", 0, 600)
    return {
        "has_programmed":         has_programmed,
        "programming_languages":  programming_languages,
        "programming_interest":   programming_interest,
        "programming_experience": programming_experience,
    }


# ---------------------------------------------------------------------------
# STEP 11 — Mathematics Assessment
# ---------------------------------------------------------------------------

def collect_math_assessment():
    display_separator("STEP 11: MATHEMATICS ASSESSMENT")
    return {
        "math_is_favourite": get_yes_no("Is Mathematics one of your favourite subjects?"),
        "math_daily_ok":     get_yes_no("Are you comfortable doing maths daily?"),
        "math_career_ok":    get_yes_no("Would you be okay with a maths-heavy career?"),
    }


# ---------------------------------------------------------------------------
# STEP 12 — Communication Skills
# ---------------------------------------------------------------------------

def collect_communication_skills():
    display_separator("STEP 12: COMMUNICATION SKILLS (1-10)")
    communication_skills = {}
    for skill in COMMUNICATION_SKILLS:
        communication_skills[skill] = get_rating("Rate your", skill.replace("_", " "))
    return {"communication_skills": communication_skills}


# ---------------------------------------------------------------------------
# STEP 13 — Personality
# ---------------------------------------------------------------------------

def collect_personality():
    display_separator("STEP 13: PERSONALITY")
    return {
        "personality_type":        get_valid_choice("Select Personality Type:", PERSONALITY_TYPES),
        "subject_type_preference": get_multiselect(
            "What type of subjects do you like? (select all that apply):",
            SUBJECT_TYPE_OPTIONS),
    }


# ---------------------------------------------------------------------------
# STEP 14 — Learning Style
# ---------------------------------------------------------------------------

def collect_learning_style():
    display_separator("STEP 14: LEARNING STYLE PREFERENCES")
    return {"learning_styles": get_multiselect(
        "Select your preferred learning styles:", LEARNING_STYLE_OPTIONS)}


# ---------------------------------------------------------------------------
# STEP 15 — Hobbies
# ---------------------------------------------------------------------------

def collect_hobbies():
    display_separator("STEP 15: HOBBIES")
    raw = get_text("List your hobbies (comma-separated): ")
    return {"hobbies": [h.strip() for h in raw.split(",") if h.strip()]}


# ---------------------------------------------------------------------------
# STEP 16 — Favourite Games
# ---------------------------------------------------------------------------

def collect_favourite_games():
    display_separator("STEP 16: FAVOURITE GAMES")
    raw = get_text("Top 3 favourite games (comma-separated): ")
    return {"favourite_games": [g.strip() for g in raw.split(",") if g.strip()][:3]}


# ---------------------------------------------------------------------------
# STEP 17 — Financial Background
# ---------------------------------------------------------------------------

def collect_financial_background():
    display_separator("STEP 17: FINANCIAL BACKGROUND")
    return {
        "financial_status":  get_valid_choice("Select Financial Status:", FINANCIAL_STATUS_OPTIONS),
        "education_budget/year":  get_text(
            "Education budget/year in your currency (e.g. '$ 5000'): "),
    }


# ---------------------------------------------------------------------------
# STEP 18 — Family Background
# ---------------------------------------------------------------------------

def collect_family_background():
    display_separator("STEP 18: FAMILY BACKGROUND")
    family_business = get_text("Family Business (or 'None'): ", allow_blank=True)
    return {
        "parent_occupations": get_text("Parents' Occupations (e.g. 'Father: Engineer, Mother: Teacher'): "),
        "family_education":   get_text("Family Education Background: "),
        "family_expectations": get_text("Family's Career Expectations: "),
        "family_business":    family_business if family_business else "None",
    }


# ---------------------------------------------------------------------------
# STEP 19 — Career Goals
# ---------------------------------------------------------------------------

def collect_career_goals():
    display_separator("STEP 19: CAREER GOALS")
    return {
        "goals_5yr":  get_text("Where do you see yourself in 5 years? "),
        "goals_10yr": get_text("Where do you see yourself in 10 years? "),
        "goals_20yr": get_text("Where do you see yourself in 20 years? "),
    }


# ---------------------------------------------------------------------------
# STEP 20 — Lifestyle Preferences
# ---------------------------------------------------------------------------

def collect_lifestyle_preferences():
    display_separator("STEP 20: LIFESTYLE PREFERENCES")
    return {"lifestyle_preferences": get_multiselect(
        "Select your lifestyle preferences:", LIFESTYLE_OPTIONS)}


# ---------------------------------------------------------------------------
# STEP 21 — Additional Notes
# ---------------------------------------------------------------------------

def collect_additional_notes():
    display_separator("STEP 21: ADDITIONAL NOTES")
    return {"additional_notes": get_text(
        "Anything else you'd like to share? (free text): ", allow_blank=True)}


# ---------------------------------------------------------------------------
# MASTER INTERVIEW RUNNER
# ---------------------------------------------------------------------------

def run_full_interview(session):
    """Calls all collect_* functions in order and merges results into the profile.

    Supports resume (skips already-completed steps) and skip logic:
    - Steps 4 & 5 are skipped entirely if secondary education is not yet complete.

    NOTE: Resume detection (loading a saved session) is intentionally NOT done
    here. It is handled exclusively by handle_resume_session() in ui.py, so
    that starting a NEW session (Menu option 1) never triggers a resume prompt,
    and the Resume option (Menu option 4) never double-prompts.
    """
    profile = session["student_profile"]

    steps = [
        (2,  collect_personal_info,          None),
        (3,  collect_secondary_education,    None),
        (4,  collect_higher_education,       None),
        (5,  collect_subject_performance,    "higher_subjects", "higher_subject_marks"),
        (6,  collect_favourite_subject,      None),
        (7,  collect_career_decision,        None),
        (8,  collect_preferred_countries,    None),
        (9,  collect_interest_ratings,       None),
        (10, collect_programming_assessment, None),
        (11, collect_math_assessment,        None),
        (12, collect_communication_skills,   None),
        (13, collect_personality,            None),
        (14, collect_learning_style,         None),
        (15, collect_hobbies,                None),
        (16, collect_favourite_games,        None),
        (17, collect_financial_background,   None),
        (18, collect_family_background,      None),
        (19, collect_career_goals,           None),
        (20, collect_lifestyle_preferences,  None),
        (21, collect_additional_notes,       None),
    ]

    try:
        for step_entry in steps:
            step_num      = step_entry[0]
            func          = step_entry[1]
            arg_key       = step_entry[2] if len(step_entry) > 2 else None
            extra_arg_key = step_entry[3] if len(step_entry) > 3 else None

            if step_num in session["steps_completed"]:
                continue  # already collected (resume case)

            # Skip Higher Education (4) and Subject Performance (5) if
            # the student has not yet completed secondary education.
            if step_num in (4, 5) and not profile.get("secondary_completed", True):
                print(
                    f"\n  >> Step {step_num} skipped — "
                    f"Higher Education is not applicable until "
                    f"Secondary Education is completed."
                )
                session["steps_completed"].append(step_num)
                continue

            session["current_step"] = step_num
            if arg_key and extra_arg_key:
                result = func(profile.get(arg_key, []), profile.get(extra_arg_key, {}))
            elif arg_key:
                result = func(profile.get(arg_key, []))
            else:
                result = func()
            for key, value in result.items():
                update_profile(profile, key, value)
            session["steps_completed"].append(step_num)
            save_session(session)

    finally:
        save_session(session)

    # All steps have now run — mark complete unconditionally.
    # is_profile_complete() is NOT used here because students who chose
    # "Continue (Still Studying)" have legitimately empty fields that would
    # cause it to return False, keeping the session forever resumable.
    profile["collection_complete"] = True
    save_session(session)
    return profile
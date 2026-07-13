"""
prompts.py
==========
System prompt loading (three independent prompts) and user-prompt
construction from a collected student profile.
No API calls live here — this module only builds the text that gets sent.
"""

import os

from config import (
    PROMPT_FILE_PATH,
    FIELD_SCOPE_PROMPT_FILE_PATH,
    FIELD_COMPARISON_PROMPT_FILE_PATH,
)


# ---------------------------------------------------------------------------
# SYSTEM PROMPT LOADERS  (three fully independent prompts, never merged)
# ---------------------------------------------------------------------------

def build_system_prompt():
    """Loads the main EduPath AI counselling system prompt.

    Used only for personalised student reports (Menu option 1).
    Raises FileNotFoundError / ValueError if the file is missing or empty.
    """
    return _load_prompt_file(PROMPT_FILE_PATH, "Main counselling")


def build_field_scope_system_prompt():
    """Loads the INDEPENDENT Field Scope Explorer system prompt.

    Used only for general field-scope lookups (Menu option 2).
    Never merged with the main counselling or comparison prompts.
    """
    return _load_prompt_file(FIELD_SCOPE_PROMPT_FILE_PATH, "Field Scope")


def build_field_comparison_system_prompt():
    """Loads the INDEPENDENT Field Comparison Explorer system prompt.

    Used only for side-by-side field comparisons (Menu option 3).
    Never merged with the other two prompts.
    """
    return _load_prompt_file(FIELD_COMPARISON_PROMPT_FILE_PATH, "Field Comparison")


def _load_prompt_file(filepath, label):
    """Internal helper: loads and validates a prompt text file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"{label} system prompt file not found: '{filepath}'. "
            f"Create this file in the same folder as main.py and paste "
            f"the {label} system prompt into it."
        )
    with open(filepath, "r", encoding="utf-8") as f:
        prompt = f.read().strip()
    if not prompt:
        raise ValueError(
            f"'{filepath}' exists but is empty. "
            f"Please paste the {label} system prompt into it."
        )
    return prompt


# ---------------------------------------------------------------------------
# PROFILE FORMATTERS  (used by build_user_prompt)
# ---------------------------------------------------------------------------

def format_academic_section(profile):
    lines = [
        f"Secondary System: {profile.get('secondary_system')}",
        f"Secondary Marks: {profile.get('secondary_marks')}",
        f"Secondary Grade: {profile.get('secondary_grade')}",
        f"Secondary Subjects: {', '.join(profile.get('secondary_subjects') or [])}",
        f"Higher System: {profile.get('higher_system')}",
        f"Higher Subjects: {', '.join(profile.get('higher_subjects') or [])}",
        f"Favourite Subject: {profile.get('favourite_subject')}",
        f"Favourite Topics: {', '.join(profile.get('favourite_topics') or [])}",
    ]
    return "\n".join(lines)


def format_subject_performance(profile):
    perf = profile.get("subject_performance") or {}
    if not perf:
        return "No subject-wise performance data provided."
    lines = ["Subject | Marks | Interest | Difficulty | Confidence | Hrs/Week"]
    for subject, data in perf.items():
        lines.append(
            f"{subject} | {data.get('marks', 'NA')} | {data.get('interest', 'NA')} | "
            f"{data.get('difficulty', 'NA')} | {data.get('confidence', 'NA')} | "
            f"{data.get('hours_per_week', 'NA')}"
        )
    return "\n".join(lines)


def format_interest_ratings(profile):
    ratings = profile.get("interest_ratings") or {}
    if not ratings:
        return "No interest ratings provided."
    return "\n".join(f"{field}: {score}/10" for field, score in ratings.items())


def format_communication_skills(profile):
    skills = profile.get("communication_skills") or {}
    if not skills:
        return "No communication skill data provided."
    return "\n".join(
        f"{skill.replace('_', ' ').title()}: {score}/10"
        for skill, score in skills.items()
    )


def format_financial_section(profile):
    return (
        f"Financial Status: {profile.get('financial_status')}\n"
        f"Education Budget: {profile.get('education_budget')}"
    )


def format_goals_section(profile):
    return (
        f"5-Year Goal: {profile.get('goals_5yr')}\n"
        f"10-Year Goal: {profile.get('goals_10yr')}\n"
        f"20-Year Goal: {profile.get('goals_20yr')}"
    )


# ---------------------------------------------------------------------------
# MASTER USER PROMPT BUILDER
# ---------------------------------------------------------------------------

def build_user_prompt(profile):
    """Calls all format_* functions and assembles the complete user message."""
    sections = []

    sections.append("=== PERSONAL INFORMATION ===")
    sections.append(f"Name: {profile.get('name')}")
    sections.append(f"Age: {profile.get('age')}")
    sections.append(f"Gender: {profile.get('gender')}")
    sections.append(f"Country/City: {profile.get('country')}, {profile.get('city')}")
    sections.append(f"Native Language: {profile.get('native_language')}")
    sections.append(f"Education Language: {profile.get('education_language')}")

    sections.append("\n=== ACADEMIC BACKGROUND ===")
    sections.append(format_academic_section(profile))

    sections.append("\n=== SUBJECT-WISE PERFORMANCE ===")
    sections.append(format_subject_performance(profile))

    sections.append("\n=== CAREER & COUNTRY PREFERENCES ===")
    sections.append(f"Current Degree Plan: {profile.get('current_degree_plan')}")
    sections.append(f"Study Country: {profile.get('study_country')}")
    sections.append(f"Work Country: {profile.get('work_country')}")

    sections.append("\n=== INTEREST RATINGS (1-10) ===")
    sections.append(format_interest_ratings(profile))

    sections.append("\n=== PROGRAMMING ASSESSMENT ===")
    sections.append(f"Has Programmed Before: {profile.get('has_programmed')}")
    sections.append(f"Languages: {', '.join(profile.get('programming_languages') or [])}")
    sections.append(f"Programming Interest: {profile.get('programming_interest')}/10")
    sections.append(f"Programming Experience (months): {profile.get('programming_experience')}")

    sections.append("\n=== MATHEMATICS ASSESSMENT ===")
    sections.append(f"Maths is Favourite: {profile.get('math_is_favourite')}")
    sections.append(f"Comfortable with Daily Maths: {profile.get('math_daily_ok')}")
    sections.append(f"OK with Maths-Heavy Career: {profile.get('math_career_ok')}")

    sections.append("\n=== COMMUNICATION SKILLS ===")
    sections.append(format_communication_skills(profile))

    sections.append("\n=== PERSONALITY ===")
    sections.append(f"Type: {profile.get('personality_type')}")
    sections.append(
        f"Preferred Subject Types: "
        f"{', '.join(profile.get('subject_type_preference') or [])}"
    )

    sections.append("\n=== LEARNING STYLE & HOBBIES ===")
    sections.append(f"Learning Styles: {', '.join(profile.get('learning_styles') or [])}")
    sections.append(f"Hobbies: {', '.join(profile.get('hobbies') or [])}")
    sections.append(f"Favourite Games: {', '.join(profile.get('favourite_games') or [])}")

    sections.append("\n=== FINANCIAL BACKGROUND ===")
    sections.append(format_financial_section(profile))

    sections.append("\n=== FAMILY BACKGROUND ===")
    sections.append(f"Parent Occupations: {profile.get('parent_occupations')}")
    sections.append(f"Family Education: {profile.get('family_education')}")
    sections.append(f"Family Expectations: {profile.get('family_expectations')}")
    sections.append(f"Family Business: {profile.get('family_business')}")

    sections.append("\n=== CAREER GOALS ===")
    sections.append(format_goals_section(profile))

    sections.append("\n=== LIFESTYLE PREFERENCES ===")
    sections.append(f"{', '.join(profile.get('lifestyle_preferences') or [])}")

    sections.append("\n=== ADDITIONAL NOTES ===")
    sections.append(f"{profile.get('additional_notes')}")

    return "\n".join(sections)


def get_full_messages(profile):
    """Returns the messages list ready for the API: [{role:system,...},{role:user,...}]."""
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user",   "content": build_user_prompt(profile)},
    ]

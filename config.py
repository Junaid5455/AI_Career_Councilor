"""
config.py
=========
All project-wide constants and configuration values.
No logic here — import this module everywhere you need a constant.
"""

# ---------------------------------------------------------------------------
# API CONFIGURATION
# ---------------------------------------------------------------------------
API_BASE_URL   = "https://api.deepseek.com/chat/completions"
MODEL_NAME     = "deepseek-v4-pro"   # pinned model — change here to affect whole app
MAX_TOKENS     = 100000
MAX_RETRIES    = 6
API_TIMEOUT    = 600                 # seconds

# ---------------------------------------------------------------------------
# PROMPT FILE PATHS  (place these files next to main.py)
# ---------------------------------------------------------------------------
PROMPT_FILE_PATH            = "new_prompt_(e)_Claud-prompt.txt"
FIELD_SCOPE_PROMPT_FILE_PATH    = "new_prompt_(e)2_Claud-prompt.txt"
FIELD_COMPARISON_PROMPT_FILE_PATH = "new_prompt_(e)3_Claud-prompt.txt"

# ---------------------------------------------------------------------------
# STORAGE
# ---------------------------------------------------------------------------
REPORT_DIR    = "reports/"
SESSIONS_FILE = "sessions.json"

# ---------------------------------------------------------------------------
# MISC
# ---------------------------------------------------------------------------
FINE_PER_DAY = 10   # Rs. 10 (retained from original LMS concept)
GENRES       = ["Fiction", "Non-Fiction", "Science", "History", "Technology"]

# ---------------------------------------------------------------------------
# INTEREST FIELDS  (Step 9 ratings)
# Physics / Chemistry / Biology / Medicine removed — collected in Step 4/5.
# Programming / AI removed — collected in Step 10.
# Music / Sports removed per spec.
# ---------------------------------------------------------------------------
INTEREST_FIELDS = [
    "Mathematics", "Engineering", "Business",
    "Economics", "Finance", "Accounting", "Marketing", "Law",
    "Psychology", "Sociology", "Education", "Journalism", "Mass Communication",
    "Design", "Architecture", "Fine Arts",
    "Agriculture", "Environmental Science", "Aviation", "Military / Defence",
]

# ---------------------------------------------------------------------------
# DROPDOWN / CHOICE LISTS
# ---------------------------------------------------------------------------
GENDER_OPTIONS          = ["Male", "Female", "Prefer not to say"]
SECONDARY_SYSTEM_OPTIONS = ["Matric", "O-Level", "Other"]
HIGHER_SYSTEM_OPTIONS   = ["FSc", "A-Level", "Other"]
FINANCIAL_STATUS_OPTIONS = ["Comfortable", "Manageable",
                             "Need Scholarship", "Tight Budget"]
LEARNING_STYLE_OPTIONS  = ["Videos", "Reading", "Practical Work",
                            "Group Discussion", "One-on-One Mentoring"]
LIFESTYLE_OPTIONS       = ["Remote Work", "Freelancing", "Corporate 9-5",
                            "Travel Frequently", "Stay Close to Family",
                            "Entrepreneurship"]
PERSONALITY_TYPES       = ["Introvert", "Extrovert", "Ambivert"]

SUBJECT_TYPE_OPTIONS = [
    "Science",
    "Arts",
    "Technological",
    "Theoretical",
    "Practical",
    "Commerce / Business",
    "Humanities / Social Sciences",
    "Creative / Design",
]

COMMUNICATION_SKILLS = [
    "speaking", "writing", "listening", "leadership",
    "teamwork", "public_speaking", "negotiation", "presentation",
]

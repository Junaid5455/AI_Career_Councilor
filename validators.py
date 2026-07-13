"""
validators.py
=============
All user-input validation helpers and interactive prompt wrappers.
No business logic, no API calls, no file I/O — pure input/output with the user.
"""

from config import MAX_RETRIES


# ---------------------------------------------------------------------------
# NUMERIC INPUT
# ---------------------------------------------------------------------------

def get_valid_int(prompt, min_val, max_val):
    """Loops until user enters an integer within [min_val, max_val]."""
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  >> Invalid input. Please enter a whole number.")
            continue
        if value < min_val or value > max_val:
            print(f"  >> Please enter a number between {min_val} and {max_val}.")
            continue
        return value


def get_valid_float(prompt, min_v, max_v):
    """Loops until user enters a float within [min_v, max_v]."""
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("  >> Invalid input. Please enter a number.")
            continue
        if value < min_v or value > max_v:
            print(f"  >> Please enter a value between {min_v} and {max_v}.")
            continue
        return value


def get_rating(prompt, subject=''):
    """Gets an integer 1-10 with a friendly prompt."""
    label = f" for {subject}" if subject else ""
    return get_valid_int(f"{prompt}{label} (1-10): ", 1, 10)


# ---------------------------------------------------------------------------
# TEXT AND YES/NO
# ---------------------------------------------------------------------------

def get_text(prompt, allow_blank=False):
    """Gets a free-text input; re-prompts if blank is not allowed."""
    while True:
        raw = input(prompt).strip()
        if raw == "" and not allow_blank:
            print("  >> This field cannot be blank.")
            continue
        return raw


def get_yes_no(prompt):
    """Returns True for yes, False for no. Accepts y/n/yes/no (any case)."""
    while True:
        raw = input(f"{prompt} (yes/no): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  >> Please answer yes or no.")


# ---------------------------------------------------------------------------
# CHOICE AND MULTI-SELECT
# ---------------------------------------------------------------------------

def get_valid_choice(prompt, options):
    """Loops until the user picks a valid option from a numbered list."""
    while True:
        print(prompt)
        for idx, opt in enumerate(options, start=1):
            print(f"   {idx}. {opt}")
        raw = input("Enter choice number: ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print("  >> Invalid choice. Try again.\n")
            continue
        if choice < 1 or choice > len(options):
            print("  >> Invalid choice. Try again.\n")
            continue
        return options[choice - 1]


def get_multiselect(prompt, options):
    """Lets user select multiple items by comma-separated numbers."""
    while True:
        print(prompt)
        for idx, opt in enumerate(options, start=1):
            print(f"   {idx}. {opt}")
        raw = input("Enter numbers separated by commas (e.g. 1,3,4): ").strip()
        parts = [p.strip() for p in raw.split(",") if p.strip() != ""]
        if not parts:
            print("  >> Please select at least one option.\n")
            continue
        valid = True
        selected = []
        for p in parts:
            if not p.isdigit():
                valid = False
                break
            num = int(p)
            if num < 1 or num > len(options):
                valid = False
                break
            if options[num - 1] not in selected:
                selected.append(options[num - 1])
        if not valid:
            print("  >> Invalid selection. Try again.\n")
            continue
        return selected


def confirm_action(message):
    """Prints message, asks (yes/no), returns bool."""
    return get_yes_no(message)


# ---------------------------------------------------------------------------
# PHONE VALIDATION
# ---------------------------------------------------------------------------

def validate_phone(phone_str):
    """Returns True if phone_str is exactly 11 digits, all numeric."""
    if phone_str is None:
        return False
    phone_str = phone_str.strip()
    return len(phone_str) == 11 and phone_str.isdigit()


def get_phone_with_retries(max_retries=3):
    """Wraps validate_phone, giving the user max_retries attempts."""
    attempts = 0
    while attempts < max_retries:
        phone = input("Enter phone number (11 digits): ").strip()
        if validate_phone(phone):
            return phone
        attempts += 1
        remaining = max_retries - attempts
        if remaining > 0:
            print(f"  >> Invalid phone number. {remaining} attempt(s) left.")
        else:
            print("  >> Maximum attempts reached. Phone number left blank.")
    return None

"""
utils.py
========
General-purpose utility functions that don't belong to any single module:
display helpers, formatters, screen control, pagination.
"""

import os


# ---------------------------------------------------------------------------
# DISPLAY / SEPARATOR
# ---------------------------------------------------------------------------

def display_separator(title='', char='='):
    """Prints a formatted section separator line."""
    width = 70
    if title:
        print(char * width)
        print(title.center(width))
        print(char * width)
    else:
        print(char * width)


def clear_screen():
    """Clears terminal (works on Windows & Linux/macOS)."""
    os.system('cls' if os.name == 'nt' else 'clear')


def paginate_output(text, lines_per_page=25):
    """Pauses output every N lines — press Enter to continue."""
    if not text:
        return
    lines = text.split("\n")
    for i in range(0, len(lines), lines_per_page):
        chunk = lines[i:i + lines_per_page]
        print("\n".join(chunk))
        if i + lines_per_page < len(lines):
            input("\n-- Press Enter to continue --\n")


# ---------------------------------------------------------------------------
# FORMATTING
# ---------------------------------------------------------------------------

def format_currency(amount):
    """Returns 'Rs. 1,250' formatted string."""
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return "Rs. 0"
    return f"Rs. {amount:,.0f}"

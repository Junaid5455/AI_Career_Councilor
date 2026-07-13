"""
api_client.py
=============
All communication with the DeepSeek API.
Handles authentication, HTTP calls, retry logic, error classification,
and response parsing.  No prompt-building or report logic lives here.
"""

import os
import time
import json
import requests
from dotenv import load_dotenv

from config import API_BASE_URL, MODEL_NAME, MAX_TOKENS, MAX_RETRIES, API_TIMEOUT

load_dotenv()


# ---------------------------------------------------------------------------
# KEY LOADING
# ---------------------------------------------------------------------------

def load_api_key():
    """Reads DEEPSEEK_API_KEY from environment / .env file."""
    return os.getenv("DEEPSEEK_API_KEY")


# ---------------------------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------------------------

def handle_api_error(error):
    """Classifies errors and returns a human-friendly message string."""
    if isinstance(error, requests.exceptions.ConnectionError):
        return "No internet connection — check your network."
    if isinstance(error, requests.exceptions.Timeout):
        return "The request timed out. Please try again."
    if isinstance(error, requests.exceptions.HTTPError):
        status = getattr(error.response, "status_code", None)
        if status == 401:
            return "API key error — check your .env file."
        if status == 429:
            return "Rate limited by the API. Waiting and retrying..."
        if status and status >= 500:
            return "AI server error. Retrying..."
        return f"HTTP error {status} occurred."
    if isinstance(error, json.JSONDecodeError):
        return "The API response was not valid JSON."
    if isinstance(error, KeyError):
        return "Unexpected API response structure."
    return f"Unexpected error: {error}"


# ---------------------------------------------------------------------------
# CORE HTTP CALL
# ---------------------------------------------------------------------------

def call_deepseek_api(messages, max_tokens=None):
    """Makes the POST request to the DeepSeek API. Returns the raw response dict."""
    api_key = load_api_key()
    if not api_key:
        raise RuntimeError("API key error — DEEPSEEK_API_KEY missing from .env file.")

    if max_tokens is None:
        max_tokens = MAX_TOKENS

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "model": MODEL_NAME,
        "max_tokens": max_tokens,
        "messages": messages,
    }

    response = requests.post(
        API_BASE_URL,
        headers=headers,
        json=body,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# RESPONSE PARSING
# ---------------------------------------------------------------------------

def extract_response_text(api_response):
    """Pulls the text content out of the API response object.

    Supports both DeepSeek-style (choices[0].message.content)
    and Anthropic-style (content[0].text) responses.
    """
    if not api_response:
        return ""
    try:
        if "choices" in api_response:
            return api_response["choices"][0]["message"]["content"]
        if "content" in api_response:
            content = api_response["content"]
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return "\n".join(text_parts)
            return str(content)
    except (KeyError, IndexError, TypeError) as e:
        raise KeyError(f"Unexpected response structure: {e}")
    return ""


# ---------------------------------------------------------------------------
# RETRY WRAPPER
# ---------------------------------------------------------------------------

def call_with_retry(messages, retries=None):
    """Wraps call_deepseek_api with exponential-back-off retry logic."""
    if retries is None:
        retries = MAX_RETRIES

    attempt = 0
    last_error = None
    while attempt < retries:
        try:
            return call_deepseek_api(messages)
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            print(f"  >> {handle_api_error(e)}")
            last_error = e
            if status == 429:
                time.sleep(10)
            elif status and status >= 500:
                time.sleep(5)
            else:
                break   # 401 etc. — retrying won't help
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            print(f"  >> {handle_api_error(e)}")
            last_error = e
            time.sleep(5)
        except Exception as e:
            print(f"  >> {handle_api_error(e)}")
            last_error = e
            break
        attempt += 1

    raise RuntimeError(f"API call failed after {attempt} attempt(s): {last_error}")


# ---------------------------------------------------------------------------
# SECTION-LEVEL CALL HELPER
# ---------------------------------------------------------------------------

def call_api_for_section(system_prompt, user_profile_text, section_instruction, step_label):
    """Calls the API for one focused section/recommendation.

    Returns the raw text from the model, or an error-placeholder on failure.
    Each call targets a single output block so token limits are never hit.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"{user_profile_text}\n\n"
                f"--- GENERATION INSTRUCTION ---\n"
                f"{section_instruction}"
            ),
        },
    ]
    print(f"  >> Generating: {step_label} ...", flush=True)
    try:
        response = call_with_retry(messages, retries=MAX_RETRIES)
        return extract_response_text(response)
    except (RuntimeError, KeyError) as e:
        print(f"  >> Warning: could not generate {step_label}: {e}")
        return f"\n[Generation failed for {step_label}. Please re-run.]\n"


# ---------------------------------------------------------------------------
# TOKEN ESTIMATION UTILITY
# ---------------------------------------------------------------------------

def estimate_tokens(text):
    """Rough estimate of token count (len(text) // 4)."""
    if not text:
        return 0
    return len(text) // 4

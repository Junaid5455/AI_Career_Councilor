"""
session_store.py
================
Thread-safe session registry backed by sessions.json via storage.py.

IMPORTANT: _load_all_sessions_from_disk() is NOT called at import time.
It is called explicitly from main.py's lifespan() AFTER config paths are
patched. This guarantees the correct sessions.json path is used.
"""

import json
import os
import threading
from typing import Optional, Dict, Any

from storage import create_session_state, save_session
from config import SESSIONS_FILE


# ---------------------------------------------------------------------------
# INTERNAL STORE
# ---------------------------------------------------------------------------

_lock: threading.Lock = threading.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# STARTUP LOADER  (called explicitly from main.py lifespan — NOT at import)
# ---------------------------------------------------------------------------

def load_all_sessions_from_disk() -> None:
    """
    Reads sessions.json and loads the stored session into memory.
    Must be called AFTER config paths are patched in main.py.
    """
    sessions_file = SESSIONS_FILE   # read at call time, after patch
    if not os.path.exists(sessions_file):
        print(f"  >> No sessions.json found at {sessions_file} — starting fresh.")
        return
    try:
        with open(sessions_file, "r", encoding="utf-8") as f:
            session = json.load(f)
        profile = session.get("student_profile", {})
        sid = profile.get("session_id")
        if sid:
            with _lock:
                _sessions[sid] = session
            print(f"  >> Loaded session '{sid}' from {sessions_file}")
        else:
            print(f"  >> sessions.json found but contains no session_id — skipped.")
    except (IOError, OSError, json.JSONDecodeError) as e:
        print(f"  >> Warning: could not load sessions from disk: {e}")


# ---------------------------------------------------------------------------
# INTERNAL DISK WRITER
# ---------------------------------------------------------------------------

def _persist(session: Dict[str, Any]) -> None:
    save_session(session)   # storage.py — UNCHANGED


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def create_session() -> Dict[str, Any]:
    session = create_session_state()
    sid = session["student_profile"]["session_id"]
    with _lock:
        _sessions[sid] = session
    _persist(session)
    return session


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        if session_id in _sessions:
            return _sessions[session_id]

    # Fallback: try reading from disk (handles post-restart case)
    sessions_file = SESSIONS_FILE
    if not os.path.exists(sessions_file):
        return None
    try:
        with open(sessions_file, "r", encoding="utf-8") as f:
            session = json.load(f)
        profile = session.get("student_profile", {})
        if profile.get("session_id") == session_id:
            with _lock:
                _sessions[session_id] = session
            return session
    except (IOError, OSError, json.JSONDecodeError):
        pass
    return None


def save_session_in_memory(session: Dict[str, Any]) -> None:
    sid = session["student_profile"]["session_id"]
    with _lock:
        _sessions[sid] = session
    _persist(session)


def delete_session(session_id: str) -> bool:
    with _lock:
        return _sessions.pop(session_id, None) is not None


def list_session_ids() -> list:
    with _lock:
        return list(_sessions.keys())
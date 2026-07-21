"""
app/session_store.py
====================
Public session API consumed by routers/sessions.py and routers/reports.py.

This module's PUBLIC FUNCTION SIGNATURES ARE UNCHANGED — every router that
previously called create_session(), get_session(), save_session_in_memory(),
delete_session(), and list_session_ids() continues to call them exactly as
before.  No router file needs to be modified.

What changed (internals only):
  BEFORE: in-memory dict + sessions.json via storage.py
  AFTER:  PostgreSQL via app/repositories/session_repository.py

The DB session is obtained from SessionLocal directly here (not via
Depends(get_db)) because these functions are called from sync router helpers
that do not participate in FastAPI's dependency injection chain.  Each call
opens a session, does its work, and closes it — equivalent to the old
per-call file read/write pattern.

load_all_sessions_from_disk() is retained with its original name so main.py
does not need to change, but now calls warm_cache_from_db() instead of
reading sessions.json.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.database import SessionLocal
from app.repositories import session_repository as repo


# ---------------------------------------------------------------------------
# INTERNAL DB SESSION FACTORY
#
# Opens a fresh SQLAlchemy session, yields it to the caller, then closes it.
# Used as a context manager so the session is always closed even on error.
# ---------------------------------------------------------------------------

from contextlib import contextmanager
from sqlalchemy.orm import Session as DBSession


@contextmanager
def _db():
    """Provide a transactional SQLAlchemy session, closed on exit."""
    db: DBSession = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# STARTUP LOADER
# Called explicitly from main.py lifespan() — signature unchanged.
# ---------------------------------------------------------------------------

def load_all_sessions_from_disk() -> None:
    """
    Previously read sessions.json into the in-memory dict.
    Now validates the DB connection and logs active session count.
    Name is kept unchanged so main.py requires no modification.
    """
    with _db() as db:
        repo.warm_cache_from_db(db)


# ---------------------------------------------------------------------------
# PUBLIC API  (signatures identical to the old implementation)
# ---------------------------------------------------------------------------

def create_session() -> Dict[str, Any]:
    """
    Creates a new Session + empty StudentProfile in PostgreSQL.
    Returns the session dict (same shape as before).
    """
    with _db() as db:
        return repo.create_session(db)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a session by its code (e.g. "SES001") from PostgreSQL.
    Returns the session dict or None if not found.
    """
    with _db() as db:
        return repo.get_session(db, session_id)


def save_session_in_memory(session: Dict[str, Any]) -> None:
    """
    Persists all changes from a session dict back to PostgreSQL.
    Name is kept unchanged so all callers in routers require no modification.
    """
    with _db() as db:
        repo.save_session(db, session)


def delete_session(session_id: str) -> bool:
    """
    Permanently deletes a session from PostgreSQL.
    Returns True if deleted, False if not found.
    """
    with _db() as db:
        return repo.delete_session(db, session_id)


def list_session_ids() -> List[str]:
    """
    Returns all active session codes from PostgreSQL.
    """
    with _db() as db:
        return repo.list_active_sessions(db)
"""
app/database.py
===============
SQLAlchemy 2.x database engine, session factory, and Base for EduPath AI.

Responsibilities:
  - Load DATABASE_URL from the project .env file
  - Create the SQLAlchemy Engine with production-grade connection-pool settings
  - Expose SessionLocal for direct session creation (e.g. background tasks)
  - Expose Base (declarative_base) for all ORM model classes to inherit from
  - Provide get_db() as a FastAPI dependency that yields a scoped session
    and guarantees cleanup on every request — success or failure

Nothing else lives here.  No models, no migrations, no business logic.
Import from this module:
  from app.database import Base, get_db, engine
"""

from __future__ import annotations

import os
import logging
from collections.abc import Generator
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ENVIRONMENT — load .env from the project root (two levels above this file)
#
# File tree:
#   <project_root>/.env
#   <project_root>/fastapi_app/app/database.py   ← this file
#
# Path(__file__).resolve().parents[2] walks up:
#   parents[0] = fastapi_app/app/
#   parents[1] = fastapi_app/
#   parents[2] = <project_root>/
# ---------------------------------------------------------------------------

from pathlib import Path

_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
_DOTENV_PATH:  Path = _PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=_DOTENV_PATH)

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set.  "
        f"Add it to your .env file at {_DOTENV_PATH}.  "
        "Expected format: "
        "postgresql+psycopg://user:password@host:port/dbname"
        " (psycopg v3)  or  "
        "postgresql://user:password@host:port/dbname"
        " (psycopg2)"
    )


# ---------------------------------------------------------------------------
# ENGINE
#
# Connection-pool settings tuned for a FastAPI / Uvicorn deployment:
#
#   pool_size        — number of persistent connections kept open.
#                      20 is safe for a single-server deployment;
#                      lower to 5-10 if PostgreSQL max_connections is tight.
#
#   max_overflow     — extra connections allowed above pool_size during spikes.
#                      These are closed as soon as they are returned.
#
#   pool_timeout     — seconds to wait for a connection before raising.
#                      Keeps slow requests from piling up indefinitely.
#
#   pool_recycle     — seconds before a connection is recycled.
#                      Prevents "server closed connection unexpectedly" errors
#                      caused by PostgreSQL's idle_in_transaction_session_timeout
#                      or network firewalls dropping idle TCP connections.
#
#   pool_pre_ping    — SQLAlchemy issues a lightweight "SELECT 1" before each
#                      checkout to detect stale connections and transparently
#                      reconnect.  Essential in production.
#
#   echo             — set to True temporarily during development to log every
#                      SQL statement.  Never True in production.
# ---------------------------------------------------------------------------

engine: Engine = create_engine(
    DATABASE_URL,
    # --- Pool configuration -------------------------------------------------
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,         # seconds
    pool_recycle=1800,       # 30 minutes
    pool_pre_ping=True,
    # --- Debugging ----------------------------------------------------------
    echo=False,
    echo_pool=False,
    # --- Query execution ----------------------------------------------------
    # Ensures RETURNING works correctly with INSERT … RETURNING on PostgreSQL
    execution_options={"isolation_level": "READ COMMITTED"},
)


# ---------------------------------------------------------------------------
# POOL EVENT — log pool checkouts at DEBUG level for connection diagnostics
# ---------------------------------------------------------------------------

@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection: Any, connection_record: Any) -> None:
    """
    Fires once per new physical connection.
    Sets the PostgreSQL application_name so pg_stat_activity is readable.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("SET application_name = 'edupath_ai_api'")
    cursor.close()


# ---------------------------------------------------------------------------
# SESSION FACTORY
#
#   autocommit=False  — transactions must be committed explicitly.
#                       Prevents accidental partial writes.
#
#   autoflush=False   — SQLAlchemy will NOT auto-flush pending changes to the
#                       DB before every query.  We control flush/commit timing
#                       explicitly in route handlers and service functions.
#
#   expire_on_commit=False — after a db.commit(), ORM objects remain usable
#                       without triggering a new SELECT.  Critical for FastAPI
#                       routes that return Pydantic models built from ORM objects
#                       after the session has already committed.
# ---------------------------------------------------------------------------

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# DECLARATIVE BASE
#
# All ORM model classes (in models.py) must inherit from Base:
#
#   from app.database import Base
#
#   class User(Base):
#       __tablename__ = "users"
#       ...
#
# Base.metadata holds the registry of all mapped tables.  Alembic reads it
# to auto-generate migration scripts.
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    Inheriting from SQLAlchemy 2.x's DeclarativeBase (rather than calling
    declarative_base()) gives full type-checker support and is the
    recommended pattern from SQLAlchemy 2.0 onwards.
    """
    pass


# ---------------------------------------------------------------------------
# FASTAPI DEPENDENCY — get_db()
#
# Usage in a route:
#
#   from fastapi import Depends
#   from sqlalchemy.orm import Session
#   from app.database import get_db
#
#   @router.get("/items/{item_id}")
#   def read_item(item_id: str, db: Session = Depends(get_db)):
#       return db.query(Item).filter(Item.id == item_id).first()
#
# The try / finally block guarantees the session is always closed —
# even if an unhandled exception propagates out of the route handler.
# SQLAlchemy rolls back any open transaction automatically on session.close().
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session for the duration of
    a single HTTP request, then closes it unconditionally.

    Yields
    ------
    Session
        A SQLAlchemy ORM session bound to the configured engine.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        # Roll back any uncommitted transaction before re-raising,
        # so the connection is returned to the pool in a clean state.
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# HEALTH-CHECK UTILITY
#
# Called from the FastAPI lifespan to verify the database is reachable
# before the API starts accepting traffic.
# ---------------------------------------------------------------------------

def verify_database_connection() -> None:
    """
    Executes a trivial query to confirm the engine can reach PostgreSQL.
    Raises RuntimeError on failure so the app fails fast at startup.

    Call this inside the FastAPI lifespan function in main.py:

        from app.database import verify_database_connection
        verify_database_connection()
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅  Database connection verified: %s", DATABASE_URL.split("@")[-1])
    except Exception as exc:
        raise RuntimeError(
            f"❌  Cannot reach PostgreSQL at {DATABASE_URL.split('@')[-1]}: {exc}"
        ) from exc
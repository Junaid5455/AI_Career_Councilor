"""
app/alembic/env.py
==================
Alembic migration environment for EduPath AI.

Configured for:
  - SQLAlchemy 2.x
  - DATABASE_URL loaded from the project .env file (never hardcoded)
  - All 8 ORM models imported explicitly so autogenerate detects every table
  - Both offline mode (--sql, generates a .sql script) and online mode
    (applies migrations directly against the live database)

File tree (for path calculation reference):
  <project_root>/
  ├── .env
  └── fastapi_app/
      └── app/
          ├── database.py      ← Base, engine defined here
          ├── models.py        ← all 8 ORM model classes
          └── alembic/
              └── env.py       ← THIS FILE
                               parents[0] = fastapi_app/app/alembic/
                               parents[1] = fastapi_app/app/
                               parents[2] = fastapi_app/
                               parents[3] = <project_root>/
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool


# ---------------------------------------------------------------------------
# PATH SETUP
#
# env.py sits at:  fastapi_app/app/alembic/env.py
# We need two directories on sys.path:
#
#   1. fastapi_app/  — so that "from app.database import Base" and
#                      "from app.models import ..." both resolve, because
#                      "app" is a package *inside* fastapi_app/.
#
#   2. <project_root>/  — so that the original project modules
#                         (config, storage, api_client, etc.) remain importable
#                         if any model or database module transitively imports
#                         them.  Also matches the sys.path patch already applied
#                         by main.py at runtime.
#
# Both paths are inserted only if not already present, so running this file
# multiple times (e.g. alembic check) is idempotent.
# ---------------------------------------------------------------------------

_HERE:         Path = Path(__file__).resolve()          # …/fastapi_app/app/alembic/env.py
_APP_DIR:      Path = _HERE.parents[1]                  # …/fastapi_app/app/
_FASTAPI_ROOT: Path = _HERE.parents[2]                  # …/fastapi_app/
_PROJECT_ROOT: Path = _HERE.parents[3]                  # …/<project_root>/

for _path in (_FASTAPI_ROOT, _PROJECT_ROOT):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)


# ---------------------------------------------------------------------------
# LOAD DATABASE_URL FROM .env
#
# The .env file lives at <project_root>/.env — the same location that
# database.py already reads from at runtime.  We load it here so that
# Alembic CLI commands (which run outside of Uvicorn) also pick up the
# correct DATABASE_URL without it ever being hardcoded in alembic.ini.
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

_DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if not _DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        f"Add it to {_PROJECT_ROOT / '.env'} before running Alembic commands.\n"
        "Expected format: postgresql://user:password@host:port/dbname"
    )


# ---------------------------------------------------------------------------
# ALEMBIC CONFIG OBJECT
# ---------------------------------------------------------------------------

config = context.config

# Inject the URL at runtime, overriding the intentionally blank value in
# alembic.ini.  This is the single source of truth for the connection URL.
config.set_main_option("sqlalchemy.url", _DATABASE_URL)

# Wire up Python logging from the [loggers] / [handlers] / [formatters]
# sections already present in the generated alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ---------------------------------------------------------------------------
# MODEL IMPORTS — required for autogenerate
#
# Alembic's --autogenerate flag compares target_metadata (the set of tables
# known to SQLAlchemy) against the live database schema.  It can only see a
# table if the corresponding model class has been imported into this process
# before target_metadata is read.
#
# We import Base first (which also initialises the engine and session factory
# inside database.py), then import every model class explicitly.  Explicit
# imports are safer than a wildcard or module-level __all__ because:
#
#   • They are visible to static analysis tools and IDEs.
#   • Adding a new model file in the future requires a deliberate line here,
#     preventing silent omissions from autogenerate output.
#   • The import order matches the FK dependency order, which avoids any
#     risk of forward-reference errors during metadata construction.
#
# Import order (parent tables before child tables):
#   User  →  Session  →  StudentProfile
#                      →  SubjectPerformance
#                      →  InterestRating
#                      →  CommunicationSkill
#         →  Report   →  ReportSection
# ---------------------------------------------------------------------------

from app.database import Base  # noqa: E402  (must come after sys.path setup)

from app.models import (        # noqa: E402  (must come after sys.path setup)
    CommunicationSkill,
    InterestRating,
    Report,
    ReportSection,
    Session,
    StudentProfile,
    SubjectPerformance,
    User,
)

# target_metadata tells Alembic which tables / columns / constraints / indexes
# exist in the ORM layer.  All 8 model classes are now registered against
# Base.metadata because their class bodies ran during the imports above.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# OFFLINE MODE
#
# Generates a SQL script that can be reviewed and applied manually, without
# Alembic ever opening a database connection.
#
# Usage:
#   alembic upgrade head --sql > migration.sql
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    context.configure(
        url=_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Wrap each migration in its own BEGIN / COMMIT block.
        transaction_per_migration=True,
        # Detect column TYPE changes during autogenerate
        # (e.g. VARCHAR(50) → VARCHAR(100)).
        compare_type=True,
        # Detect changes to server-side DEFAULT expressions.
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# ONLINE MODE
#
# Connects to the live database and applies pending migrations directly.
#
# Usage:
#   alembic upgrade head
#   alembic downgrade -1
#
# NullPool is used intentionally: Alembic is a CLI tool that opens one
# connection, runs migrations, and exits.  Connection pooling adds no value
# here and would keep a stale connection object alive after the process ends.
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the live database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect column TYPE changes during autogenerate.
            compare_type=True,
            # Detect changes to server-side DEFAULT expressions.
            compare_server_default=True,
            # Include schema-level objects (sequences, etc.) in comparisons.
            include_schemas=False,
        )
        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
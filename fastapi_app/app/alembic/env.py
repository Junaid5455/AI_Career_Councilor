"""
app/alembic/env.py
==================
Alembic migration environment for EduPath AI.

Configured for:
  - SQLAlchemy 2.x
  - DATABASE_URL loaded from the project .env file (never hardcoded)
  - Base imported from app.database so autogenerate can detect model changes
  - Both offline mode (generate SQL script) and online mode (run against live DB)
"""

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
# env.py lives at:  fastapi_app/app/alembic/env.py
# Project root is:  fastapi_app/../../  (three levels up)
# fastapi_app/ is:  fastapi_app/../../fastapi_app/  (two levels up)
#
# We add the project root to sys.path so that:
#   - "from app.database import Base" resolves (app/ is inside fastapi_app/)
#   - All original modules (config, storage, etc.) are importable
# ---------------------------------------------------------------------------

_HERE         = Path(__file__).resolve()           # fastapi_app/app/alembic/env.py
_FASTAPI_ROOT = _HERE.parents[2]                   # fastapi_app/
_PROJECT_ROOT = _HERE.parents[3]                   # your-project/

for _p in (_FASTAPI_ROOT, _PROJECT_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ---------------------------------------------------------------------------
# LOAD DATABASE_URL FROM .env
#
# .env sits at the project root, same place database.py reads it from.
# We load it here so Alembic CLI commands (run outside Uvicorn) also
# pick up the correct URL.
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

_DATABASE_URL = os.getenv("DATABASE_URL")
if not _DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        f"Add it to {_PROJECT_ROOT / '.env'} before running Alembic."
    )

# ---------------------------------------------------------------------------
# ALEMBIC CONFIG OBJECT
# ---------------------------------------------------------------------------

config = context.config

# Inject the URL at runtime — overrides the blank value in alembic.ini
config.set_main_option("sqlalchemy.url", _DATABASE_URL)

# Wire up Python logging from alembic.ini's [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# TARGET METADATA
#
# Importing Base pulls in all models that have been registered against it.
# Once models.py exists and its classes inherit from Base, Alembic will
# detect schema changes automatically via --autogenerate.
#
# For now (no models yet) this is None — autogenerate will produce empty
# migrations, which is correct and expected.
# ---------------------------------------------------------------------------

from app.database import Base          # noqa: E402  (import after sys.path setup)
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# OFFLINE MODE  — generates a .sql script without connecting to the database
#
# Usage:  alembic upgrade head --sql
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    context.configure(
        url=_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Emit BEGIN/COMMIT around each migration
        transaction_per_migration=True,
        # Detect column type changes during autogenerate
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# ONLINE MODE  — connects to the live database and applies migrations directly
#
# Usage:  alembic upgrade head
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool: Alembic creates a single connection, runs migrations,
        # and closes it. No pool needed for a CLI tool.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect column type changes during autogenerate
            compare_type=True,
            # Detect server-side default changes
            compare_server_default=True,
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
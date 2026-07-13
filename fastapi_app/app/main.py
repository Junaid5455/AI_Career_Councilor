"""
app/main.py
===========
FastAPI application factory for EduPath AI Career Counsellor.

Architecture:
  app/main.py              ← You are here (app factory + CORS + health check)
  app/schemas.py           ← Pydantic request/response models
  app/session_store.py     ← In-memory + disk-backed session registry
  app/routers/
      sessions.py          ← /sessions/* — 21-step interview
      reports.py           ← /reports/* — AI generation + PDF download
      config_router.py     ← /config/* — dropdown option lists

All original modules (api_client, config, interview, prompts,
report_generator, storage, utils, validators) are UNCHANGED.
"""

import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# STEP 1 — Resolve the project root (folder that contains config.py, prompts.py, etc.)
# app/main.py lives at:  <project_root>/fastapi_app/app/main.py
# So project root is two levels up from this file.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# STEP 2 — Patch config.py prompt paths to absolute BEFORE any other import.
#
# config.py defines the three prompt file paths as bare filenames, e.g.:
#   PROMPT_FILE_PATH = "new_prompt_(e)_Claud-prompt.txt"
#
# When uvicorn runs from inside fastapi_app/, os.path.exists("new_prompt_...")
# looks in fastapi_app/ and finds nothing.  We replace them with absolute
# paths anchored to the project root so they work from ANY working directory.
#
# We do this by importing config first, then overwriting the three attributes
# on the live module object.  prompts.py imports these names FROM config at
# call time (not at module load), so the patched values are always used.
# Original config.py is NOT modified.
# ---------------------------------------------------------------------------
import config as _config

_config.PROMPT_FILE_PATH = str(
    _PROJECT_ROOT / "new_prompt_(e)_Claud-prompt.txt"
)
_config.FIELD_SCOPE_PROMPT_FILE_PATH = str(
    _PROJECT_ROOT / "new_prompt_(e)2_Claud-prompt.txt"
)
_config.FIELD_COMPARISON_PROMPT_FILE_PATH = str(
    _PROJECT_ROOT / "new_prompt_(e)3_Claud-prompt.txt"
)

# _FASTAPI_ROOT is the fastapi_app/ folder — one level up from app/
# sessions.json lives here (confirmed by user).
# reports/ is placed at the project root alongside the original modules.
_FASTAPI_ROOT = Path(__file__).resolve().parent.parent
_config.SESSIONS_FILE = str(_FASTAPI_ROOT / "sessions.json")
_config.REPORT_DIR    = str(_PROJECT_ROOT / "reports" / "")

# ---------------------------------------------------------------------------
# STEP 3 — All other imports come AFTER the patch above.
# ---------------------------------------------------------------------------
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from storage import ensure_reports_dir                       # UNCHANGED utility
from app.session_store import load_all_sessions_from_disk    # explicit loader
from app.routers import sessions, reports, config_router


# ---------------------------------------------------------------------------
# LIFESPAN  (startup / shutdown logic)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_reports_dir()
    load_all_sessions_from_disk()   # runs AFTER config paths are patched above
    print(f"✅  EduPath AI API ready.  Project root: {_PROJECT_ROOT}")
    yield
    print("👋  EduPath AI API shutting down.")


# ---------------------------------------------------------------------------
# APP FACTORY
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="EduPath AI — Career Counsellor API",
        description=(
            "REST API for the EduPath AI career counselling platform. "
            "Provides a 21-step student interview, AI-powered career report "
            "generation (DeepSeek), field scope explorer, and field comparison."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions.router)
    app.include_router(reports.router)
    app.include_router(config_router.router)

    @app.get("/health", tags=["Health"])
    def health():
        """Liveness probe — returns 200 if the server is up."""
        return {"status": "ok", "service": "EduPath AI API"}

    return app


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
app = create_app()
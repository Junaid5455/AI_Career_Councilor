"""
routers/reports.py
==================
Endpoints for AI report generation and PDF download.

POST /reports/career                        → generate personalised career report
GET  /reports/career/{session_id}/download  → download the PDF

POST /reports/field-scope                   → generate a Field Scope report
GET  /reports/field-scope/download          → download Field Scope PDF

POST /reports/field-comparison              → generate a Field Comparison report
GET  /reports/field-comparison/download     → download Field Comparison PDF

All AI calls are delegated to the UNCHANGED report_generator.py.
"""

import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.session_store import get_session, save_session_in_memory
from app.schemas import (
    ReportGenerateRequest, ReportResponse,
    FieldScopeRequest, FieldScopeResponse,
    FieldComparisonRequest, FieldComparisonResponse,
)

# Importing the existing, UNCHANGED business logic modules
from report_generator import (
    generate_career_report, save_report,
    generate_field_scope_report, save_field_scope_report,
    generate_field_comparison_report, save_field_comparison_report,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _require_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session


def _require_pdf(path: str, label: str) -> str:
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"{label} PDF not found. Generate the report first.",
        )
    return path


# ---------------------------------------------------------------------------
# CAREER REPORT  (personalised, multi-call pipeline)
# ---------------------------------------------------------------------------

@router.post("/career", response_model=ReportResponse)
def generate_career(body: ReportGenerateRequest):
    """
    Triggers the full multi-call AI career report for a completed session.
    The session must have collection_complete == True.
    This call can take 60–300 seconds depending on AI response time.
    For production, move this to a background task / job queue.
    """
    session = _require_session(body.session_id)
    profile = session["student_profile"]

    if not profile.get("collection_complete", False):
        raise HTTPException(
            status_code=400,
            detail="Interview is not yet complete. Finish all 21 steps first.",
        )

    try:
        report_text = generate_career_report(profile)   # UNCHANGED function
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    pdf_path = save_report(report_text, profile)         # UNCHANGED function
    profile["report_generated"] = True
    session["ai_report_text"] = report_text
    session["report_file_path"] = pdf_path or ""
    save_session_in_memory(session)

    return ReportResponse(
        session_id=body.session_id,
        report_text=report_text,
        pdf_path=pdf_path,
    )


@router.get("/career/{session_id}/download")
def download_career_pdf(session_id: str):
    """Streams the generated PDF to the client."""
    session = _require_session(session_id)
    path = session.get("report_file_path", "")
    _require_pdf(path, "Career report")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=os.path.basename(path),
    )


# ---------------------------------------------------------------------------
# FIELD SCOPE REPORT  (single field, no student profile needed)
# ---------------------------------------------------------------------------

@router.post("/field-scope", response_model=FieldScopeResponse)
def generate_scope(body: FieldScopeRequest):
    """
    Generates a standalone Field Scope report for any named field.
    No session or student profile is required.
    """
    try:
        report_text = generate_field_scope_report(body.field_name)   # UNCHANGED
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    pdf_path = save_field_scope_report(report_text, body.field_name)  # UNCHANGED

    return FieldScopeResponse(
        field_name=body.field_name,
        report_text=report_text,
        pdf_path=pdf_path,
    )


@router.get("/field-scope/download")
def download_scope_pdf(pdf_path: str):
    """
    Streams the Field Scope PDF.
    Pass the pdf_path returned by POST /reports/field-scope as a query param.
    """
    _require_pdf(pdf_path, "Field scope")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
    )


# ---------------------------------------------------------------------------
# FIELD COMPARISON REPORT  (two or more fields, no student profile needed)
# ---------------------------------------------------------------------------

@router.post("/field-comparison", response_model=FieldComparisonResponse)
def generate_comparison(body: FieldComparisonRequest):
    """
    Generates a side-by-side Field Comparison report.
    No session or student profile is required.
    """
    try:
        report_text = generate_field_comparison_report(body.field_names)  # UNCHANGED
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}")

    pdf_path = save_field_comparison_report(report_text, body.field_names)  # UNCHANGED

    return FieldComparisonResponse(
        field_names=body.field_names,
        report_text=report_text,
        pdf_path=pdf_path,
    )


@router.get("/field-comparison/download")
def download_comparison_pdf(pdf_path: str):
    """
    Streams the Field Comparison PDF.
    Pass the pdf_path returned by POST /reports/field-comparison as a query param.
    """
    _require_pdf(pdf_path, "Field comparison")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
    )

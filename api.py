"""
API entrypoint, built with FastAPI.

Two sets of endpoints:

LEGACY (backward-compatible)
  POST /redact          → returns a ZIP with redacted file + report

NEW (for the React frontend)
  POST /api/redact      → returns JSON with job_id + detection report
  GET  /api/preview/original/{job_id}/{page}  → PNG of original page
  GET  /api/preview/redacted/{job_id}/{page}  → PNG of redacted page
  GET  /api/download/{job_id}                 → redacted file download

HOW JOBS WORK
-------------
Each upload creates a "job" with a UUID.  The original file, redacted
file, rendered PNGs, and report JSON are stored in a temporary directory
keyed by job_id.  A background task cleans up jobs older than 30 minutes.

CORS
----
CORS is enabled for the React dev server (localhost:5173) and for
production builds (same origin).  This is required for the React
frontend to talk to the API.
"""

import os
import json
import shutil
import tempfile
import time
import uuid
import zipfile
import threading
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

from core.pipeline import process_document
from core.renderer import render_document_pages

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PII Redaction Tool",
    description=(
        "Upload a document (.txt, .docx, .pdf, .xlsx, or image) and receive a zip "
        "containing the redacted document and a structured JSON report.  "
        "Use the optional **include** / **exclude** fields to control which "
        "PII entity types are detected.\n\n"
        "**Valid category names:** "
        "EMAIL, PAN_NUMBER, PHONE_NUMBER, DATE_OF_BIRTH, IP_ADDRESS, "
        "AADHAAR_NUMBER, CREDIT_CARD, PINCODE, BANK_ACCOUNT_NUMBER, "
        "IFSC_CODE, GSTIN, PERSON_NAME, LOCATION, ORGANIZATION"
    ),
    version="2.0.0",
)

# CORS — allow React dev server and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Job storage (in-memory, with TTL cleanup)
# ---------------------------------------------------------------------------

_jobs: dict[str, dict] = {}
_JOB_TTL_SECONDS = 1800  # 30 minutes


def _cleanup_old_jobs():
    """Remove jobs older than _JOB_TTL_SECONDS."""
    now = time.time()
    expired = [
        jid for jid, jdata in _jobs.items()
        if now - jdata["created_at"] > _JOB_TTL_SECONDS
    ]
    for jid in expired:
        job = _jobs.pop(jid, None)
        if job and os.path.exists(job["work_dir"]):
            shutil.rmtree(job["work_dir"], ignore_errors=True)


def _start_cleanup_timer():
    """Periodically clean up expired jobs every 5 minutes."""
    _cleanup_old_jobs()
    timer = threading.Timer(300, _start_cleanup_timer)
    timer.daemon = True
    timer.start()


# Start cleanup on app load.
_start_cleanup_timer()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_csv(value: Optional[str]) -> Optional[list[str]]:
    """Split a comma-separated string into a trimmed list of uppercase names.

    Returns None (= no filter) when:
      - value is None or empty
      - value is the literal word 'string' (Swagger UI's default placeholder)
    """
    if not value:
        return None
    if value.strip().lower() == "string":
        return None
    items = [item.strip().upper() for item in value.split(",") if item.strip()]
    return items if items else None


# =========================================================================
# LEGACY ENDPOINT (backward-compatible)
# =========================================================================

@app.post(
    "/redact",
    summary="Redact PII from an uploaded document (returns ZIP)",
    response_description=(
        "A ZIP archive containing the redacted document and JSON report."
    ),
)
async def redact_document(
    file: UploadFile = File(
        ..., description="The document to redact (.txt, .docx, .pdf, .xlsx, or image)"
    ),
    include: Optional[str] = Form(
        default=None,
        description=(
            "Comma-separated PII types to detect (all others skipped). "
            "Leave empty to detect ALL types. "
            "Example: EMAIL,PHONE_NUMBER"
        ),
        example=None,
    ),
    exclude: Optional[str] = Form(
        default=None,
        description=(
            "Comma-separated PII types to skip (ignored when 'include' is set). "
            "Leave empty to skip nothing. "
            "Example: PINCODE,LOCATION"
        ),
        example=None,
    ),
):
    """
    Accept an uploaded document, run the PII pipeline, and return a zip
    file containing the redacted document + JSON report.
    """
    with tempfile.TemporaryDirectory() as work_dir:
        input_path = os.path.join(work_dir, file.filename)
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        output_dir = os.path.join(work_dir, "output")
        redacted_path, report_path = process_document(
            input_path,
            output_dir,
            include=_parse_csv(include),
            exclude=_parse_csv(exclude),
        )

        zip_path = os.path.join(work_dir, "result.zip")
        with zipfile.ZipFile(zip_path, "w") as zip_file:
            zip_file.write(redacted_path, os.path.basename(redacted_path))
            zip_file.write(report_path,   os.path.basename(report_path))

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

    stem = os.path.splitext(file.filename)[0]
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename={stem}_redaction_result.zip"
            )
        },
    )


# =========================================================================
# NEW ENDPOINTS (for React frontend)
# =========================================================================

@app.post(
    "/api/redact",
    summary="Redact PII and get a job ID for preview",
)
async def api_redact(
    file: UploadFile = File(
        ..., description="The document to redact (.txt, .docx, .pdf, .xlsx, or image)"
    ),
    include: Optional[str] = Form(default=None),
    exclude: Optional[str] = Form(default=None),
):
    """
    Upload a file, run the PII pipeline, render both original and
    redacted documents to page images, and return a job_id that can
    be used to fetch previews and download the result.
    """
    _cleanup_old_jobs()

    job_id = str(uuid.uuid4())
    work_dir = tempfile.mkdtemp(prefix=f"pii_{job_id[:8]}_")

    # Save uploaded file
    input_path = os.path.join(work_dir, file.filename)
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run pipeline
    output_dir = os.path.join(work_dir, "output")
    try:
        redacted_path, report_path = process_document(
            input_path,
            output_dir,
            include=_parse_csv(include),
            exclude=_parse_csv(exclude),
        )
    except ValueError as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))

    # Read report
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # Render original and redacted pages to PNGs
    try:
        original_render = render_document_pages(input_path)
        redacted_render = render_document_pages(redacted_path)
    except Exception as e:
        # LibreOffice not installed or other rendering issue
        original_render = {"type": "error", "message": str(e), "total_pages": 0}
        redacted_render = {"type": "error", "message": str(e), "total_pages": 0}

    # Store rendered pages as files for the preview endpoints
    preview_dir = os.path.join(work_dir, "preview")
    os.makedirs(preview_dir, exist_ok=True)

    original_page_count = 0
    redacted_page_count = 0
    original_text = None
    redacted_text = None

    if original_render.get("type") == "image":
        for i, page_bytes in enumerate(original_render["pages"]):
            with open(os.path.join(preview_dir, f"original_{i}.png"), "wb") as f:
                f.write(page_bytes)
        original_page_count = original_render["total_pages"]

    elif original_render.get("type") == "text":
        original_text = original_render.get("text", "")
        original_page_count = 1

    if redacted_render.get("type") == "image":
        for i, page_bytes in enumerate(redacted_render["pages"]):
            with open(os.path.join(preview_dir, f"redacted_{i}.png"), "wb") as f:
                f.write(page_bytes)
        redacted_page_count = redacted_render["total_pages"]

    elif redacted_render.get("type") == "text":
        redacted_text = redacted_render.get("text", "")
        redacted_page_count = 1

    # Store job metadata
    _jobs[job_id] = {
        "created_at": time.time(),
        "work_dir": work_dir,
        "input_path": input_path,
        "redacted_path": redacted_path,
        "report_path": report_path,
        "preview_dir": preview_dir,
        "filename": file.filename,
        "render_type": original_render.get("type", "error"),
        "original_page_count": original_page_count,
        "redacted_page_count": redacted_page_count,
        "original_text": original_text,
        "redacted_text": redacted_text,
    }

    return JSONResponse({
        "job_id": job_id,
        "filename": file.filename,
        "render_type": original_render.get("type", "error"),
        "original_pages": original_page_count,
        "redacted_pages": redacted_page_count,
        "original_text": original_text,
        "redacted_text": redacted_text,
        "report": report,
    })


@app.get(
    "/api/preview/original/{job_id}/{page}",
    summary="Get PNG preview of an original document page",
)
async def get_original_preview(job_id: str, page: int):
    """Return a PNG image of the specified page from the original document."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    png_path = os.path.join(job["preview_dir"], f"original_{page}.png")
    if not os.path.exists(png_path):
        raise HTTPException(status_code=404, detail=f"Page {page} not found")

    with open(png_path, "rb") as f:
        png_bytes = f.read()

    return Response(content=png_bytes, media_type="image/png")


@app.get(
    "/api/preview/redacted/{job_id}/{page}",
    summary="Get PNG preview of a redacted document page",
)
async def get_redacted_preview(job_id: str, page: int):
    """Return a PNG image of the specified page from the redacted document."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    png_path = os.path.join(job["preview_dir"], f"redacted_{page}.png")
    if not os.path.exists(png_path):
        raise HTTPException(status_code=404, detail=f"Page {page} not found")

    with open(png_path, "rb") as f:
        png_bytes = f.read()

    return Response(content=png_bytes, media_type="image/png")


@app.get(
    "/api/download/{job_id}",
    summary="Download the redacted document",
)
async def download_redacted(job_id: str):
    """Download the redacted document file."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    redacted_path = job["redacted_path"]
    if not os.path.exists(redacted_path):
        raise HTTPException(status_code=404, detail="Redacted file not found")

    with open(redacted_path, "rb") as f:
        file_bytes = f.read()

    filename = os.path.basename(redacted_path)
    return Response(
        content=file_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@app.get(
    "/api/download-report/{job_id}",
    summary="Download the JSON report",
)
async def download_report(job_id: str):
    """Download the detection report JSON."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    report_path = job["report_path"]
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    return JSONResponse(report)

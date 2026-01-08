from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.repos.redis_jobs import get_job_repo
from app.workers.ingest_task import ingest_document
from app.schemas.ingest import IngestRequest
import os
from uuid import uuid4

USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

router = APIRouter(prefix="/v1")
jobs = get_job_repo()


# --------------------------------------------------
# Ingest PDF or Website (URL-based)
# --------------------------------------------------
@router.post("/ingest", status_code=202)
def ingest(req: IngestRequest):
    # Create job (no convId)
    job = jobs.create(sourceId=req.userId)

    source = req.source.strip()

    if not source:
        raise HTTPException(
            status_code=400,
            detail="source must be a non-empty string"
        )

    # Dispatch ingestion
    if USE_CELERY:
        ingest_document.delay(
            jobId=job["jobId"],
            userId=req.userId,
            source=source,
        )
    else:
        ingest_document(
            jobId=job["jobId"],
            userId=req.userId,
            source=source,
        )

    return {
        "jobId": job["jobId"],
        "status": "queued",
    }


# --------------------------------------------------
# Ingest PDF (Direct Upload)
# --------------------------------------------------
@router.post("/ingest/pdf", status_code=202)
async def ingest_pdf(
    file: UploadFile = File(...),
    userId: str = Form(...)
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    job = jobs.create(userId)

    pdf_bytes = await file.read()

    # ALWAYS use keyword arguments
    if USE_CELERY:
        ingest_document.delay(
            jobId=job["jobId"],
            userId=userId,
            source=pdf_bytes,  # BYTES
        )
    else:
        ingest_document(
            jobId=job["jobId"],
            userId=userId,
            source=pdf_bytes,  # BYTES
        )

    return {
        "jobId": job["jobId"],
        "status": "queued",
    }


# --------------------------------------------------
# Job Status
# --------------------------------------------------
@router.get("/jobs/{jobId}")
def job_status(jobId: str):
    data = jobs.get(jobId)

    if data["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    return data
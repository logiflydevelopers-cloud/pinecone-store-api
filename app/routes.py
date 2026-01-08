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
    job = jobs.create(req.convId)

    source = req.fileUrl or req.prompt

    if not source or not isinstance(source, str) or not source.strip():
        raise HTTPException(
            status_code=400,
            detail="Either fileUrl or prompt must be provided as a non-empty string"
        )

    source = source.strip()

    # ✅ ALWAYS use keyword arguments
    if USE_CELERY:
        ingest_document.delay(
            jobId=job["jobId"],
            userId=req.userId,
            convId=req.convId,
            source=source,
        )
    else:
        ingest_document(
            jobId=job["jobId"],
            userId=req.userId,
            convId=req.convId,
            source=source,
        )

    return {
        "jobId": job["jobId"],
        "convId": req.convId,
        "status": "queued",
    }


# --------------------------------------------------
# Ingest PDF (Direct Upload)
# --------------------------------------------------
@router.post("/ingest/pdf", status_code=202)
async def ingest_pdf(
    file: UploadFile = File(...),
    userId: str = Form(...),
    convId: str = Form(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    job = jobs.create(convId)

    pdf_bytes = await file.read()

    # ✅ ALWAYS use keyword arguments
    if USE_CELERY:
        ingest_document.delay(
            jobId=job["jobId"],
            userId=userId,
            convId=convId,
            source=pdf_bytes,  # 🔥 BYTES
        )
    else:
        ingest_document(
            jobId=job["jobId"],
            userId=userId,
            convId=convId,
            source=pdf_bytes,  # 🔥 BYTES
        )

    return {
        "jobId": job["jobId"],
        "convId": convId,
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
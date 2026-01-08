from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """
    Ingestion request for WEB URL only.

    Used by:
    - POST /ingest

    NOTE:
    - PDF ingestion is handled via /ingest/pdf (multipart upload)
    - No convId
    - No fileUrl
    - No prompt
    """

    userId: str = Field(
        ...,
        description="Authenticated user ID (used as Pinecone namespace)"
    )

    source: str = Field(
        ...,
        description="Website URL to scrape and ingest"
    )


class IngestResponse(BaseModel):
    """
    Response returned after job is accepted.
    """

    jobId: str
    status: str

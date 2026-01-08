from app.workers.celery import celery

from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages

from app.crawlers.smart_crawler import smart_crawl

from app.services.embeddings import build_embeddings
from app.repos.redis_jobs import get_job_repo


# --------------------------------------------------
# Helper: robust PDF detection
# --------------------------------------------------
def detect_pdf(url: str, content_type: str) -> bool:
    if content_type and "application/pdf" in content_type:
        return True

    clean_url = (url or "").lower().split("?")[0]
    return clean_url.endswith(".pdf")


# --------------------------------------------------
# Core ingestion logic
# --------------------------------------------------
def _ingest_logic(
    jobId: str,
    userId: str,
    convId: str,
    source,
):
    print("\n🚀 INGEST STARTED")
    print("jobId:", jobId)
    print("userId:", userId)
    print("convId:", convId)
    print("source type:", type(source))

    jobs = get_job_repo()

    try:
        # -------------------------
        # START JOB
        # -------------------------
        jobs.update(
            jobId,
            status="processing",
            stage="fetch",
            progress=5,
            convId=convId,
        )
        print("📌 Job marked as processing")

        # -------------------------
        # Validate source
        # -------------------------
        if source is None:
            raise ValueError("source is required")

        is_bytes = isinstance(source, (bytes, bytearray))
        is_url = isinstance(source, str) and source.strip()

        if not is_bytes and not is_url:
            raise ValueError("source must be either a URL string or PDF bytes")

        url = source.strip() if is_url else None

        # -------------------------
        # FETCH SOURCE
        # -------------------------
        if is_bytes:
            print("📄 Using uploaded PDF bytes")
            content = source
            content_type = "application/pdf"
        else:
            print("🌐 Fetching URL:", url)
            content, content_type = fetch_source(url)

        print("content_type:", content_type)

        is_pdf = detect_pdf(url, content_type)
        print("is_pdf:", is_pdf)

        # ==================================================
        # PDF INGESTION
        # ==================================================
        if is_pdf:
            print("📄 START PDF EXTRACTION")
            jobs.update(jobId, stage="extract", progress=25)

            texts, pages, total_words, ocr_pages = extract_pages(content)

            print(
                f"📄 PDF extracted → pages={pages}, "
                f"words={total_words}, ocr_pages={ocr_pages}"
            )

            if not texts:
                raise ValueError("No text extracted from PDF")

            print("🧠 START EMBEDDINGS (PDF)")
            jobs.update(jobId, stage="embed", progress=60)

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=texts,
                sourceType="pdf",
                pages=list(range(1, pages + 1)),
            )

            print("✅ EMBEDDINGS DONE (PDF)")

        # ==================================================
        # WEB INGESTION (SMART CRAWLER)
        # ==================================================
        else:
            print("🌐 START SMART WEB CRAWL")
            jobs.update(jobId, stage="crawl", progress=25)

            pages = smart_crawl(
                url,
                max_pages=100,
                max_depth=5,
            )

            if not pages:
                raise ValueError("No usable web content extracted")

            print(f"🌐 Pages crawled: {len(pages)}")

            print("🧠 START EMBEDDINGS (WEB)")
            jobs.update(jobId, stage="embed", progress=60)

            for idx, page in enumerate(pages):
                print(f"🔹 Embedding page {idx + 1}/{len(pages)} → {page['url']}")

                build_embeddings(
                    userId=userId,
                    convId=convId,
                    texts=[page["text"]],
                    sourceType="web",
                    url=page["url"],
                    chunkId=f"web-{idx}",
                )

            print("✅ EMBEDDINGS DONE (WEB)")

        # -------------------------
        # COMPLETE JOB
        # -------------------------
        jobs.complete(jobId)
        print("🎉 JOB COMPLETED")

    except Exception as e:
        print("❌ INGEST FAILED:", str(e))
        jobs.fail(jobId, str(e))
        raise


# --------------------------------------------------
# Celery / Local Task Wrapper
# --------------------------------------------------
@celery.task(bind=True, name="ingest_document")
def ingest_document(self=None, *args, **kwargs):
    """
    Works for BOTH:
    - Celery async execution
    - Local synchronous execution
    """

    if kwargs:
        return _ingest_logic(
            kwargs["jobId"],
            kwargs["userId"],
            kwargs["convId"],
            kwargs["source"],
        )

    if len(args) == 4:
        jobId, userId, convId, source = args
        return _ingest_logic(jobId, userId, convId, source)

    raise RuntimeError("Invalid arguments passed to ingest_document")

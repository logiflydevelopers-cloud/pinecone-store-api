from celery import Celery
import os

USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"

# -------------------------------------------------
# LOCAL MODE (NO REDIS, NO WORKER)
# -------------------------------------------------
if not USE_CELERY:
    celery = Celery("pinecone_local")

    celery.conf.update(
        task_always_eager=True,        
        task_eager_propagates=True,    
    )

# -------------------------------------------------
# PRODUCTION MODE (REDIS + WORKER)
# -------------------------------------------------
else:
    REDIS_URL = os.environ.get("REDIS_URL")
    if not REDIS_URL:
        raise RuntimeError("REDIS_URL environment variable is required")

    celery = Celery(
        "pinecone_worker",        # unique app name
        broker=REDIS_URL,
        backend=REDIS_URL,
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_default_queue="pinecone_queue",
    )

# -------------------------------------------------
# FORCE task registration
# -------------------------------------------------
import app.workers.ingest_task  # noqa: F401

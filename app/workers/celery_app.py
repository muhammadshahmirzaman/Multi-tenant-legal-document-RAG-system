from celery import Celery
from app.core.config import settings

broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery = Celery(
    "legal_rag",
    broker=broker,
    backend=backend,
)

celery.conf.task_routes = {
    "app.workers.ingest_task.*": {"queue": "ingest"}
}

# optional configs
celery.conf.worker_prefetch_multiplier = 1

@celery.task(name="ping")
def ping():
    return {"ok": True}

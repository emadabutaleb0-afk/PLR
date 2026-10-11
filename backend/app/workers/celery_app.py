from celery import Celery
from app.core.config import get_settings

cfg = get_settings()
celery_app = Celery("merchbrain", broker=cfg.redis_url or "memory://", backend=cfg.redis_url or "cache+memory://")
celery_app.conf.update(task_track_started=True, task_time_limit=3600, worker_prefetch_multiplier=1, broker_connection_retry_on_startup=True)


@celery_app.task(name="merchbrain.run_job")
def run_job_task(job_id: str, kind: str, params: dict):
    from app.services.jobs import run_job
    run_job(job_id, kind, params)

"""Background jobs. Celery (Redis broker) when enabled; otherwise a daemon thread. State lives in the `jobs` table either way."""
from __future__ import annotations
import threading, time, uuid, logging
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.app import Job, now
from app.monitoring.metrics import JOB_DUR, IMPORT_FAIL

log = logging.getLogger("merchbrain.jobs")


def _set(job_id, **kw):
    db = SessionLocal()
    try:
        j = db.get(Job, job_id)
        for k, v in kw.items():
            setattr(j, k, v)
        db.commit()
    finally:
        db.close()


def run_job(job_id: str, kind: str, params: dict):
    """Executed by a thread or by a Celery worker."""
    t0 = time.time()
    _set(job_id, status="RUNNING", stage="starting")
    try:
        if kind in ("import", "validate"):
            from app.ingestion.pipeline import run_refresh
            res = run_refresh(mode=kind, triggered_by=params.get("user"), run_id=params.get("run_id"),
                              progress=lambda s, p: _set(job_id, stage=s, progress=p))
            if res.get("status") in ("FAILED", "PARTIAL"):
                IMPORT_FAIL.inc()
            _set(job_id, status="SUCCESS" if res.get("status") != "FAILED" else "FAILED", result=res, progress=1.0, message=res.get("error"))
        elif kind in ("retrain", "recommendations"):
            from app.services.post_load import refresh_everything
            db = SessionLocal()
            try:
                refresh_everything(db, uuid.uuid4().hex[:12], lambda s, p: _set(job_id, stage=s, progress=p), run_ml=True)
            finally:
                db.close()
            from app.core.cache import cache_clear
            cache_clear()
            _set(job_id, status="SUCCESS", progress=1.0, result={"ok": True})
        else:
            _set(job_id, status="FAILED", message=f"unknown job kind {kind}")
    except Exception:
        log.exception("job %s failed", job_id)
        _set(job_id, status="FAILED", message="The job failed. Details are in the server log.")
    finally:
        dur = time.time() - t0
        JOB_DUR.labels(kind).observe(dur)
        _set(job_id, finished_at=now(), duration_sec=round(dur, 1))


def submit(kind: str, params: dict | None = None, wait: bool = False) -> str:
    params = params or {}
    job_id = uuid.uuid4().hex[:12]
    db = SessionLocal()
    db.add(Job(id=job_id, kind=kind, status="QUEUED"))
    db.commit()
    db.close()
    cfg = get_settings()
    if wait:
        run_job(job_id, kind, params)
    elif cfg.celery_enabled and cfg.redis_url:
        from app.workers.celery_app import celery_app
        celery_app.send_task("merchbrain.run_job", args=[job_id, kind, params])
    else:
        threading.Thread(target=run_job, args=(job_id, kind, params), daemon=True).start()
    return job_id

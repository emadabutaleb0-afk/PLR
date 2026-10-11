from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.deps import require, current_user, has as has_scope
from app.core.config import get_settings
from app.ingestion.pipeline import discover
from app.ingestion.specs import FILES, LOAD_ORDER
from app.models.app import User, DataRefreshRun, FileHealth, DataQualityIssue, QuarantineRow, Job
from app.models.tables import TABLES
from app.api.common import freshness, PageParams, paginate
from app.services.jobs import submit
from app.services.audit import audit

router = APIRouter(prefix="/data", tags=["Data"])
jobs_router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _job(j: Job):
    return dict(id=j.id, kind=j.kind, status=j.status, progress=j.progress, stage=j.stage, message=j.message, result=j.result, created_at=j.created_at.isoformat(),
                finished_at=j.finished_at.isoformat() if j.finished_at else None, duration_sec=j.duration_sec)


def _start(kind, db, u, wait):
    cfg = get_settings()
    found = discover(cfg.data_dir)
    if not found["exists"]:
        raise HTTPException(422, "The configured company data folder does not exist or is not readable. Ask IT to check DATA_DIRECTORY.")
    if not found["present"]:
        raise HTTPException(422, "No CSV files were found in the company data folder. Copy the updated files there and try again.")
    running = db.scalars(select(Job).where(Job.kind.in_(["import", "validate"]), Job.status.in_(["QUEUED", "RUNNING"]))).first()
    if running and not wait:
        raise HTTPException(409, "A data refresh is already running. Please wait for it to finish.")
    audit(db, u, "data_import" if kind == "import" else "data_validate", "data", None, {"files_found": len(found["present"]), "missing": found["missing"]})
    job_id = submit(kind, {"user": u.email}, wait=wait)
    j = db.get(Job, job_id)
    db.refresh(j)
    return _job(j)


status_router = APIRouter(prefix="/system", tags=["System"])


@status_router.get("/status", summary="Is data loaded / being loaded? (any signed-in user)")
def system_status(db: Session = Depends(get_db), u: User = Depends(current_user)):
    cfg = get_settings()
    ok = db.scalars(select(DataRefreshRun).where(DataRefreshRun.mode == "import", DataRefreshRun.status.in_(["SUCCESS", "PARTIAL"])).limit(1)).first()
    job = db.scalars(select(Job).where(Job.kind == "import").order_by(Job.created_at.desc()).limit(1)).first()
    running = bool(job and job.status in ("QUEUED", "RUNNING"))
    found = discover(cfg.data_dir)
    return dict(has_data=bool(ok), importing=running, stage=job.stage if running else None, progress=round(job.progress or 0, 2) if running else None,
                last_error=(job.message if job and job.status == "FAILED" else None), files_found=len(found["present"]), data_folder_ok=found["exists"] and bool(found["present"]),
                can_import=has_scope(u, "data_import"))


@router.post("/import", status_code=202, summary="Import (replace) data from the configured company folder")
def import_data(wait: bool = Query(False, description="Run synchronously (used by tests/automation)"), db: Session = Depends(get_db), u: User = Depends(require("data_import"))):
    return _start("import", db, u, wait)


@router.post("/validate", status_code=202, summary="Validate the files without loading them")
def validate_data(wait: bool = False, db: Session = Depends(get_db), u: User = Depends(require("data_health"))):
    return _start("validate", db, u, wait)


def plausibility(db: Session) -> list[dict]:
    """Cross-table sanity checks surfaced to users (never silently ignored)."""
    out = []
    try:
        s, po = TABLES["sales_transactions"], TABLES["purchase_orders"]
        last = db.scalar(select(func.max(s.c.order_date)))
        if last:
            from datetime import timedelta
            lo = last - timedelta(days=365)
            sales = db.scalar(select(func.sum(s.c.net_sales_egp)).where(s.c.order_date > lo)) or 0
            buy = db.scalar(select(func.sum(po.c.ordered_qty * po.c.unit_cost_egp)).where(po.c.order_date > lo)) or 0
            if sales and buy > sales:
                out.append(dict(check="purchases_vs_sales", status="WARNING", message=f"Material purchases in the last 12 months (EGP {buy:,.0f}) exceed net sales (EGP {sales:,.0f}). Purchase_Orders quantities or costs may not be on the same scale as sales; supplier cost figures should be read as relative, not absolute."))
            else:
                out.append(dict(check="purchases_vs_sales", status="OK", message="Material purchases are below net sales."))
    except Exception:
        pass
    return out


@router.get("/reconciliation", summary="Cross-file consistency checks and non-comparable headline numbers")
def reconciliation(db: Session = Depends(get_db), u: User = Depends(require("data_health"))):
    from app.validation.reconcile import reconcile
    try:
        res = reconcile(get_settings().data_dir)
    except FileNotFoundError as e:
        raise HTTPException(409, f"Reconciliation needs the company files: {e.filename}")
    audit(db, u, "reconciliation_run", "data", None, {"status": res["status"]})
    return res


@router.get("/health", summary="Data health: files, freshness, failures, warnings")
def data_health(db: Session = Depends(get_db), u: User = Depends(require("data_health"))):
    cfg = get_settings()
    found = discover(cfg.data_dir)
    fh = {f.file: f for f in db.scalars(select(FileHealth))}
    files = []
    for f in LOAD_ORDER:
        h = fh.get(f)
        files.append(dict(file=f, present_in_folder=f in found["present"], rows=h.rows_loaded if h else 0, rows_read=h.rows_read if h else 0, rows_rejected=h.rows_rejected if h else 0,
                          last_update=h.file_modified.isoformat() if h and h.file_modified else None, newest_data_date=h.latest_data_date if h else None,
                          null_rate=round(h.null_rate, 4) if h else None, duplicate_rate=round(h.duplicate_rate, 4) if h else None,
                          status=(h.status if h else ("NOT_LOADED" if f in found["present"] else "MISSING")), message=h.message if h else None, data_class=h.data_class if h else None))
    last = db.scalars(select(DataRefreshRun).where(DataRefreshRun.mode == "import").order_by(DataRefreshRun.start_time.desc()).limit(1)).first()
    issues = []
    if last:
        issues = [dict(file=i.file, rule=i.rule, severity=i.severity, rows=i.row_count, message=i.message, sample_rows=i.sample)
                  for i in db.scalars(select(DataQualityIssue).where(DataQualityIssue.run_id == last.run_id).order_by(DataQualityIssue.severity, DataQualityIssue.row_count.desc()).limit(100))]
    failed = [f["file"] for f in files if f["status"] in ("FAILED",)]
    modeled = [f["file"] for f in files if f["data_class"] and ("odel" in f["data_class"] or "training" in f["data_class"].lower())]
    overall = "UNHEALTHY" if failed or not last else ("ATTENTION" if any(f["status"] in ("WARNING", "MISSING") for f in files) else "HEALTHY")
    return dict(overall=overall, freshness=freshness(db), data_directory_exists=found["exists"], files_found=len(found["present"]), files_missing=found["missing"], files=files, failed_files=failed,
                last_refresh=(dict(run_id=last.run_id, start_time=last.start_time.isoformat(), end_time=last.end_time.isoformat() if last.end_time else None, status=last.status,
                                   files_processed=last.files_processed, rows_loaded=last.rows_loaded, rows_rejected=last.rows_rejected, validation_warnings=last.validation_warnings, stage=last.stage) if last else None),
                validation_warnings=issues, plausibility=plausibility(db),
                data_provenance=dict(modeled_files=modeled, note=("These files are labelled as modelled/training data in their Data_Class column. Figures built on them are demonstrations, not company results." if modeled else None)))


@router.get("/runs")
def runs(p: PageParams = Depends(), db: Session = Depends(get_db), u: User = Depends(require("data_health"))):
    rows = [dict(run_id=r.run_id, mode=r.mode, start_time=r.start_time.isoformat(), end_time=r.end_time.isoformat() if r.end_time else None, status=r.status, files_processed=r.files_processed,
                 rows_loaded=r.rows_loaded, rows_rejected=r.rows_rejected, validation_warnings=r.validation_warnings, triggered_by=r.triggered_by)
            for r in db.scalars(select(DataRefreshRun).order_by(DataRefreshRun.start_time.desc()).limit(200))]
    return paginate(rows, p)


@router.get("/quarantine")
def quarantine(p: PageParams = Depends(), run_id: str | None = None, file: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("data_health"))):
    q = select(QuarantineRow)
    if run_id: q = q.where(QuarantineRow.run_id == run_id)
    if file: q = q.where(QuarantineRow.file == file)
    rows = [dict(run_id=r.run_id, file=r.file, row_number=r.row_number, reason=r.reason) for r in db.scalars(q.limit(5000))]   # raw values are intentionally not returned
    return paginate(rows, p, ("file", "reason"))


@jobs_router.get("/{job_id}")
def job(job_id: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "Job not found.")
    return _job(j)


@jobs_router.get("")
def jobs(db: Session = Depends(get_db), u: User = Depends(current_user)):
    return [_job(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()).limit(20))]


@jobs_router.post("/retrain", status_code=202, summary="Retrain models and refresh recommendations in the background")
def retrain(db: Session = Depends(get_db), u: User = Depends(require("data_import"))):
    audit(db, u, "retrain_requested")
    jid = submit("retrain", {"user": u.email})
    return _job(db.get(Job, jid))

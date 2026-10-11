"""Extract -> Validate -> Transform -> Load -> Recompute features -> Refresh analytics -> ML inference -> Refresh recommendations."""
from __future__ import annotations
import os, time, uuid, logging
from datetime import datetime, date
from pathlib import Path
from typing import Callable
import pandas as pd
from sqlalchemy import select, delete
from app.core.config import get_settings
from app.core.cache import cache_clear
from app.db.session import SessionLocal, engine
from app.models.app import DataRefreshRun, DataQualityIssue, QuarantineRow, FileHealth, now
from app.models.tables import TABLES
from app.ingestion.specs import FILES, LOAD_ORDER, SOFT_LINKS
from app.ingestion.loader import load_tables, existing_keys
from app.validation.validator import read_csv, validate_frame

log = logging.getLogger("merchbrain.ingestion")

STAGES = ["extract", "validate", "transform", "load", "features", "analytics", "ml", "recommendations", "done"]


def discover(data_dir: str) -> dict:
    d = Path(data_dir)
    present, missing = {}, []
    lower = {p.name.lower(): p for p in d.glob("*.csv")} if d.exists() else {}
    for f in LOAD_ORDER:
        p = lower.get(f.lower())
        (present.__setitem__(f, p) if p else missing.append(f))
    return dict(dir=str(d), exists=d.exists(), present=present, missing=missing)


def run_refresh(data_dir: str | None = None, mode: str = "import", triggered_by: str | None = None,
                run_id: str | None = None, progress: Callable[[str, float], None] | None = None,
                run_ml: bool = True) -> dict:
    cfg = get_settings()
    data_dir = data_dir or cfg.data_dir
    run_id = run_id or uuid.uuid4().hex[:12]
    t0 = time.time()
    db = SessionLocal()
    run = DataRefreshRun(run_id=run_id, mode=mode, triggered_by=triggered_by, stage="extract")
    db.add(run)
    db.commit()

    def step(stage, pct):
        run.stage, run.progress = stage, pct
        db.commit()
        if progress:
            progress(stage, pct)

    try:
        step("extract", 0.02)
        found = discover(data_dir)
        if not found["exists"] or not found["present"]:
            run.status, run.end_time = "FAILED", now()
            run.report = {"error": f"No CSV files found in the configured data directory ({data_dir}). "
                                   "Copy the company CSV files there and retry.", "missing": found["missing"]}
            db.commit()
            return {"run_id": run_id, "status": "FAILED", **run.report}

        step("validate", 0.10)
        results, ref_keys, unavailable = {}, {}, set()
        n = len(found["present"])
        for i, f in enumerate(LOAD_ORDER):
            if f not in found["present"]:
                continue
            spec = FILES[f]
            try:
                raw = read_csv(found["present"][f])
            except Exception as e:
                from app.validation.validator import ValidationResult
                r = ValidationResult(file=f, fatal=f"{f} could not be read as a CSV file ({type(e).__name__})")
                results[f] = r
                continue
            # parents available either from this run or from what is already loaded
            for _, rt, rc in spec.fks:
                if rt not in ref_keys:
                    pf = next((x.file for x in FILES.values() if x.table == rt), None)
                    if pf in found["present"] and pf in results and results[pf].fatal is None:
                        continue
                    with engine.connect() as c:
                        k = existing_keys(c, rt, rc)
                    if k:
                        ref_keys[rt] = {str(x) for x in k}
            parents_ok = all((rt in ref_keys) for _, rt, _ in spec.fks)
            if not parents_ok:
                missing_parents = [rt for _, rt, _ in spec.fks if rt not in ref_keys]
                from app.validation.validator import ValidationResult
                r = ValidationResult(file=f, rows_read=0, fatal=(
                    f"{f} cannot be loaded because its parent table(s) are unavailable: {', '.join(missing_parents)}"))
                results[f] = r
                continue
            r = validate_frame(spec, raw, ref_keys, stale_days=cfg.stale_data_days)
            results[f] = r
            if r.fatal is None and len(spec.pk) == 1:
                ref_keys[spec.table] = set(r.clean[spec.pk[0]].astype(str))
            step("validate", 0.10 + 0.35 * (len(results) / max(n, 1)))

        # soft (non-FK) cross-file checks
        for f, col, pf, pcol, msg in SOFT_LINKS:
            a, b = results.get(f), results.get(pf)
            if a and b and a.clean is not None and b.clean is not None and col in a.clean and pcol in b.clean:
                miss = set(a.clean[col].dropna()) - set(b.clean[pcol].dropna())
                if miss:
                    a.issues.append(dict(rule="soft_link", severity="warn", row_count=len(miss),
                                         message=f"{msg}. Not found: {', '.join(sorted(miss)[:5])}", sample=[]))

        step("transform", 0.48)
        frames = {f: r.clean for f, r in results.items() if r.fatal is None and r.clean is not None}
        total_rejected = sum(r.rows_rejected for r in results.values())
        warnings = sum(1 for r in results.values() for i in r.issues if i["severity"] == "warn") + \
            sum(1 for r in results.values() if r.fatal)
        failed = [f for f, r in results.items() if r.fatal]

        report = {"files": {}, "missing_files": found["missing"], "failed_files": failed,
                  "data_directory_configured": True}
        for f, r in results.items():
            report["files"][f] = dict(rows_read=r.rows_read, rows_clean=r.rows_clean, rows_rejected=r.rows_rejected,
                                      null_rate=round(r.null_rate, 5), duplicate_rate=round(r.duplicate_rate, 5),
                                      fatal=r.fatal, latest_date=r.latest_date, data_class=r.data_class,
                                      issues=r.issues, column_null_rates=r.column_null_rates)
        # persist quality issues + quarantine (always, import and validate-only)
        for f, r in results.items():
            if r.fatal:
                db.add(DataQualityIssue(run_id=run_id, file=f, rule="file_failed", severity="error", row_count=r.rows_read,
                                        message=r.fatal))
            for i in r.issues:
                db.add(DataQualityIssue(run_id=run_id, file=f, **i))
            for q in r.quarantine:
                db.add(QuarantineRow(run_id=run_id, file=f, **q))
        db.commit()

        loaded_info = {"loaded": {}, "orphans_removed": {}}
        if mode == "import" and frames:
            step("load", 0.55)
            with engine.begin() as conn:
                loaded_info = load_tables(conn, frames)
            for t, n_ in loaded_info["orphans_removed"].items():
                warnings += 1
                db.add(DataQualityIssue(run_id=run_id, file=t, rule="orphans_removed", severity="warn", row_count=n_,
                                        message=f"{n_} existing rows in {t} referenced records that no longer exist after the parent file was replaced, and were removed"))
            # file health snapshot
            for f in LOAD_ORDER:
                fh = db.get(FileHealth, f) or FileHealth(file=f, run_id=run_id)
                r = results.get(f)
                fh.run_id = run_id
                if r is None:
                    fh.present, fh.status, fh.message = False, "MISSING", "File not found in the data directory"
                    if fh.rows_loaded is None:
                        fh.rows_loaded = 0
                else:
                    fh.present = True
                    fh.rows_read, fh.rows_rejected = r.rows_read, r.rows_rejected
                    fh.rows_loaded = loaded_info["loaded"].get(f, 0)
                    fh.null_rate, fh.duplicate_rate = r.null_rate, r.duplicate_rate
                    fh.latest_data_date, fh.data_class = r.latest_date, r.data_class
                    fh.file_modified = datetime.fromtimestamp(os.path.getmtime(found["present"][f]))
                    if r.fatal:
                        fh.status, fh.message = "FAILED", r.fatal
                    elif any(i["rule"] == "stale_data" for i in r.issues):
                        fh.status, fh.message = "WARNING", "Data looks stale"
                    elif r.rows_rejected or any(i["severity"] == "warn" for i in r.issues):
                        fh.status = "WARNING"
                        fh.message = f"{r.rows_rejected} rows quarantined" if r.rows_rejected else "Validation warnings"
                    else:
                        fh.status, fh.message = "OK", None
                db.add(fh)
            db.commit()
            run.rows_loaded = sum(loaded_info["loaded"].values())

            from app.services.post_load import refresh_everything
            refresh_everything(db, run_id, step, run_ml=run_ml)
            cache_clear()

        run.files_processed = len(results)
        run.rows_rejected = total_rejected
        run.validation_warnings = warnings
        run.status = "FAILED" if (not frames) else ("PARTIAL" if failed or total_rejected else "SUCCESS")
        run.report = report
        run.stage, run.progress, run.end_time = "done", 1.0, now()
        db.commit()
        log.info("refresh %s %s files=%s loaded=%s rejected=%s in %.1fs", run_id, run.status, len(results),
                 run.rows_loaded, total_rejected, time.time() - t0)
        return {"run_id": run_id, "status": run.status, "files_processed": run.files_processed,
                "rows_loaded": run.rows_loaded, "rows_rejected": total_rejected, "validation_warnings": warnings,
                "failed_files": failed, "missing_files": found["missing"], "mode": mode,
                "duration_sec": round(time.time() - t0, 1)}
    except Exception as e:  # never leak a stack trace to the user; keep it in the structured log
        log.exception("refresh %s crashed", run_id)
        db.rollback()
        run = db.get(DataRefreshRun, run_id)
        run.status, run.end_time, run.stage = "FAILED", now(), "failed"
        run.report = {"error": "The data refresh stopped unexpectedly. Previously loaded data is unchanged. "
                               "Check the server log for run " + run_id}
        db.commit()
        return {"run_id": run_id, "status": "FAILED", "error": run.report["error"]}
    finally:
        db.close()

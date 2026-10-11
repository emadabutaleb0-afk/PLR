import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from app.core.config import get_settings
from app.core import logging as logsetup, errors
from app.core.middleware import Hardening
from app.core.security import hash_password
from app.db.session import Base, engine, SessionLocal
import app.models  # noqa
from app.models.app import User
from app.api import auth_routes, business, actions, data_routes, misc, commercial, workspace
from app.monitoring.metrics import render

log = logging.getLogger("merchbrain")


def bootstrap():
    """Create tables when Alembic has not been run (dev/tests) and ensure a first CEO account exists."""
    cfg = get_settings()
    if cfg.database_url.startswith("sqlite") or cfg.environment != "production":
        Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if not db.scalars(select(User).limit(1)).first():
            db.add(User(email=cfg.bootstrap_admin_email.lower(), full_name="CEO", password_hash=hash_password(cfg.bootstrap_admin_password), role="CEO"))
            db.commit()
            log.warning("Bootstrap CEO account created (%s). Change the password immediately.", cfg.bootstrap_admin_email)
    finally:
        db.close()


def auto_import_if_empty():
    """First start (or an empty database): load the company CSVs in the background so nobody ever lands on an empty app."""
    cfg = get_settings()
    if not cfg.auto_import_on_start or cfg.environment == "test":
        return
    from app.models.app import DataRefreshRun, Job
    from app.ingestion.pipeline import discover
    db = SessionLocal()
    try:
        done = db.scalars(select(DataRefreshRun).where(DataRefreshRun.mode == "import", DataRefreshRun.status.in_(["SUCCESS", "PARTIAL"])).limit(1)).first()
        busy = db.scalars(select(Job).where(Job.kind == "import", Job.status.in_(["QUEUED", "RUNNING"])).limit(1)).first()
        if done or busy:
            return
        found = discover(cfg.data_dir)
        if not found["present"]:
            log.warning("No CSV files found in %s - copy the company files there, then press 'Refresh data'.", cfg.data_dir)
            return
        from app.services.jobs import submit
        log.warning("Empty database: importing %s company files from %s in the background.", len(found["present"]), cfg.data_dir)
        submit("import", {"user": "system:first-start"})
    except Exception:
        log.exception("automatic first import could not be started")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logsetup.setup()
    cfg = get_settings()
    if cfg.environment == "production" and cfg.production_problems():
        raise RuntimeError("Unsafe production configuration: " + "; ".join(cfg.production_problems()))
    if cfg.environment == "production" and cfg.bootstrap_admin_email.endswith(".local"):
        log.warning("BOOTSTRAP_ADMIN_EMAIL (%s) is a placeholder address: set a real one before handing the system over.", cfg.bootstrap_admin_email)
    bootstrap()
    # a job left RUNNING by a crashed/stopped server would block every future refresh: close it out
    if not cfg.celery_enabled:   # with Celery the worker is a separate process and may legitimately still be running
        from app.models.app import Job, now as _now
        _db = SessionLocal()
        try:
            for j in _db.scalars(select(Job).where(Job.status.in_(["QUEUED", "RUNNING"]))):
                j.status, j.message, j.finished_at = "FAILED", "The server was restarted while this job was running.", _now()
            _db.commit()
        finally:
            _db.close()
    auto_import_if_empty()
    yield


def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(title="SHARNOUBY MERCH BRAIN API", version="1.0.0", description="Fashion Retail Decision Intelligence Platform - on-premise decision and execution layer.",
                  lifespan=lifespan, docs_url="/docs" if cfg.environment != "production" else None, redoc_url=None)
    app.add_middleware(Hardening)
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])
    errors.install(app)
    for r in (auth_routes.router, business.exec_r, business.mer_r, business.prod_r, business.inv_r, business.mkt_r, business.sup_r, business.qual_r, business.ops_r, business.rec_r,
              actions.router, commercial.router, data_routes.router, data_routes.jobs_router, data_routes.status_router, misc.search_r, misc.export_r, misc.admin_r, workspace.router):
        app.include_router(r, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    def health():
        try:
            with engine.connect() as c:
                c.execute(text("select 1"))
            return {"status": "ok"}
        except Exception:
            return Response(status_code=503, content='{"status":"database_unavailable"}', media_type="application/json")

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        body, ctype = render()
        return Response(body, media_type=ctype)
    return app


app = create_app()

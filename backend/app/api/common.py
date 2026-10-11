from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from fastapi import Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.cache import cache_get, cache_set
from app.models.app import AnalyticsSnapshot, DataRefreshRun
from app.core.config import get_settings


def snap(db: Session, key: str, default: Any = None):
    hit = cache_get("snap:" + key)
    if hit is not None:
        return hit
    row = db.get(AnalyticsSnapshot, key)
    if row is None:
        return default
    cache_set("snap:" + key, row.payload, 900)
    return row.payload


def freshness(db: Session) -> dict:
    hit = cache_get("freshness")
    if hit:
        return hit
    run = db.scalars(select(DataRefreshRun).where(DataRefreshRun.mode == "import", DataRefreshRun.status.in_(["SUCCESS", "PARTIAL"])).order_by(DataRefreshRun.start_time.desc()).limit(1)).first()
    ex = snap(db, "executive", {}) or {}
    if not run:
        out = {"data_updated_at": None, "age_hours": None, "data_as_of": None, "status": "NO_DATA", "message": "No data has been imported yet."}
    else:
        end = run.end_time or run.start_time
        age = (datetime.utcnow() - end).total_seconds() / 3600
        as_of = ex.get("as_of")
        stale_days = None
        if as_of:
            stale_days = (datetime.utcnow().date() - datetime.fromisoformat(as_of).date()).days
        stale = stale_days is not None and stale_days > get_settings().stale_data_days
        out = {"data_updated_at": end.isoformat(), "age_hours": round(age, 1), "data_as_of": as_of, "newest_data_age_days": stale_days,
               "status": "STALE" if stale else "FRESH",
               "message": (f"Newest business data is {stale_days} days old - decisions may be out of date." if stale else f"Data updated {_ago(age)}.")}
    cache_set("freshness", out, 60)
    return out


def _ago(h: float) -> str:
    if h < 1:
        return "less than an hour ago"
    if h < 48:
        return f"{int(h)} hour{'s' if int(h) != 1 else ''} ago"
    return f"{int(h // 24)} days ago"


class PageParams:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200), sort: str | None = None, order: str = Query("desc", pattern="^(asc|desc)$"), q: str | None = None):
        self.page, self.page_size, self.sort, self.order, self.q = page, page_size, sort, order, q


def paginate(rows: list[dict], p: PageParams, search_fields: tuple = (), db: Session | None = None, extra: dict | None = None) -> dict:
    if p.q and search_fields:
        ql = p.q.lower()
        rows = [r for r in rows if any(ql in str(r.get(f, "")).lower() for f in search_fields)]
    if p.sort and rows and p.sort in rows[0]:
        nn = [r for r in rows if r.get(p.sort) is not None]
        nl = [r for r in rows if r.get(p.sort) is None]
        nn.sort(key=lambda r: r[p.sort], reverse=p.order == "desc")
        rows = nn + nl
    total = len(rows)
    s = (p.page - 1) * p.page_size
    out = {"items": rows[s:s + p.page_size], "total": total, "page": p.page, "page_size": p.page_size, "pages": (total + p.page_size - 1) // p.page_size}
    if db is not None:
        out["freshness"] = freshness(db)
    if extra:
        out.update(extra)
    return out


def eq_filter(rows: list[dict], **kw) -> list[dict]:
    for k, v in kw.items():
        if v:
            rows = [r for r in rows if str(r.get(k)) == str(v)]
    return rows

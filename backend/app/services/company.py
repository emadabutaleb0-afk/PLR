from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.app import AnalyticsSnapshot
from app.models.tables import TABLES
from app.core.config import get_settings


def get_company_name(db: Session) -> dict:
    """Return dict(company_name=..., source=...)
    Order of precedence:
    1. User custom setting (stored in AnalyticsSnapshot key='company_profile')
    2. Config from env (COMPANY_NAME)
    3. Detected from uploaded data (most common brand in product_master, or business unit)
    4. Fallback default ('Business Gate')
    """
    # 1. Custom user setting
    prof = db.get(AnalyticsSnapshot, "company_profile")
    if prof and prof.payload and prof.payload.get("name"):
        return {"company_name": str(prof.payload["name"]).strip(), "source": "user"}

    # 2. Config setting
    cfg = get_settings()
    env_name = getattr(cfg, "company_name", "")
    if env_name and env_name.strip():
        return {"company_name": env_name.strip(), "source": "config"}

    # 3. Detect from data (product_master brand or business units)
    try:
        pm = TABLES.get("product_master")
        if pm is not None:
            top_brand = db.execute(
                select(pm.c.brand, func.count())
                .where(pm.c.brand.isnot(None), pm.c.brand != "")
                .group_by(pm.c.brand)
                .order_by(func.count().desc())
            ).first()
            if top_brand and top_brand[0]:
                return {"company_name": str(top_brand[0]).strip(), "source": "data"}

        bu = TABLES.get("business_units")
        if bu is not None:
            first_bu = db.execute(select(bu.c.business_unit).where(bu.c.business_unit.isnot(None))).first()
            if first_bu and first_bu[0]:
                return {"company_name": str(first_bu[0]).strip(), "source": "data"}
    except Exception:
        pass

    # 4. Default
    return {"company_name": "Business Gate", "source": "default"}


def set_company_name(db: Session, name: str) -> dict:
    cleaned = (name or "").strip()
    prof = db.get(AnalyticsSnapshot, "company_profile")
    if not cleaned:
        if prof:
            db.delete(prof)
            db.commit()
        return get_company_name(db)

    if not prof:
        prof = AnalyticsSnapshot(key="company_profile", payload={"name": cleaned})
        db.add(prof)
    else:
        prof.payload = {"name": cleaned}
    db.commit()
    return {"company_name": cleaned, "source": "user"}

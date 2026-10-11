"""Commercial decision endpoints: command center, profit leakage, supply readiness, channel allocation, discount intelligence."""
from __future__ import annotations
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.deps import require, strip_fields
from app.models.app import User
from app.api.common import snap, freshness
from app.intelligence import allocation as alloc_e, scenarios as scen_e
from app.services.audit import audit
from app.services.weekly_report import build_pdf

router = APIRouter(prefix="/commercial", tags=["Commercial Intelligence"])
NONE = "No analytics are available yet. Import the company data first."


def _get(db: Session, key: str, default=None):
    d = snap(db, key, default)
    if not d:
        raise HTTPException(404, NONE)
    return d


@router.get("/command-center", summary="Headline numbers and the five actions for today")
def command_center(db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    return {**strip_fields(u, _get(db, "command_center")), "freshness": freshness(db)}


@router.get("/decision-plans", summary="Three alternative cross-department plans (max profit / balanced / min risk) with conflicts resolved")
def decision_plans(db: Session = Depends(get_db), u: User = Depends(require("recovery"))):
    return {**strip_fields(u, _get(db, "decision_plans")), "freshness": freshness(db)}


@router.get("/autopsy", summary="Business autopsy: exact profit-change decomposition plus evidence chains across departments")
def autopsy(db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    return {**strip_fields(u, _get(db, "autopsy")), "freshness": freshness(db)}


@router.get("/leakage", summary="Profit leakage over the last 12 months, by type")
def leakage(db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    return {**strip_fields(u, _get(db, "leakage")), "freshness": freshness(db)}


@router.get("/supply", summary="Demand -> production -> material requirement and supplier risk")
def supply(db: Session = Depends(get_db), u: User = Depends(require("suppliers"))):
    return {**strip_fields(u, _get(db, "supply")), "freshness": freshness(db)}


def _no_store_manager(u: User):
    if u.role == "STORE_MANAGER":
        raise HTTPException(403, "Channel allocation compares all channels and is not available for location-restricted roles.")


@router.get("/allocation", summary="Retail vs Online vs Wholesale stock split per product")
def allocation(only_actionable: bool = False, db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    _no_store_manager(u)
    d = _get(db, "allocation")
    rows = [r for r in d.get("rows", []) if r["worth_acting"] or not only_actionable]
    return {**strip_fields(u, dict(summary=d.get("summary", {}), rows=rows[:100], note=d.get("note"))), "freshness": freshness(db)}


@router.get("/allocation/{product_id}", summary="Split a quantity of one product across channels")
def allocation_split(product_id: str, units: int = Query(500, ge=1, le=1_000_000), db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    _no_store_manager(u)
    d = _get(db, "allocation")
    p = d.get("params", {}).get(product_id)
    if not p:
        raise HTTPException(404, "This product has no allocation data (it needs sales or stock in at least two channels).")
    row = next((r for r in d["rows"] if r["product_id"] == product_id), None)
    return strip_fields(u, dict(product_id=product_id, product_name=row["product_name"] if row else product_id, units=units, split=alloc_e.split_units(p, units), horizon_days=p["horizon"], note=d.get("note")))


@router.get("/discounts", summary="Discount response and margin given away, by channel and product")
def discounts(db: Session = Depends(get_db), u: User = Depends(require("costs"))):
    return {**_get(db, "discounts"), "freshness": freshness(db)}


class ScenarioIn(BaseModel):
    product_id: str | None = Field(None, max_length=40)
    channel: str | None = Field(None, max_length=40)
    material_id: str | None = Field(None, max_length=40)
    new_discount: float | None = Field(None, ge=0, le=0.6)
    lift_per_5pp: float = Field(0.0, ge=-0.5, le=1.0)
    extra_units: int | None = Field(None, ge=1, le=1_000_000)
    pct: float | None = Field(None, ge=-0.5, le=2.0)
    pass_through: float = Field(0.0, ge=0, le=1)


@router.get("/scenario/options", summary="Products, channels and materials available for what-if scenarios")
def scenario_options(db: Session = Depends(get_db), u: User = Depends(require("costs"))):
    return scen_e.options(_get(db, "scenario_base"))


@router.post("/scenario/{kind}", summary="Run a what-if scenario: discount, extra_stock or material_price")
def scenario(kind: str, body: ScenarioIn, db: Session = Depends(get_db), u: User = Depends(require("costs"))):
    try:
        return scen_e.run_scenario(_get(db, "scenario_base"), kind, **body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/weekly-report.pdf", summary="Owner's weekly report (PDF, English)")
def weekly_report(db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    audit(db, u, "export", "report", "weekly", {"format": "pdf"})
    pdf = build_pdf(_get(db, "command_center"), _get(db, "leakage"), _get(db, "supply"), _get(db, "discounts"), freshness(db))
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="merchbrain-weekly-{datetime.utcnow():%Y%m%d}.pdf"'})


@router.get("/customers", summary="Customer rhythm, overdue accounts, acquisition source and service quality")
def customers(db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    return {**strip_fields(u, _get(db, "customers")), "freshness": freshness(db)}

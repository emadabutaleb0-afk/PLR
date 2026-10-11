from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.deps import require, scope_rows, strip_fields, has
from app.models.app import User, Recommendation
from app.models.tables import TABLES
from app.api.common import snap, freshness, PageParams, paginate, eq_filter
from app.services.audit import audit

URG = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
exec_r = APIRouter(prefix="/executive", tags=["Executive"])
prod_r = APIRouter(prefix="/products", tags=["Products"])
inv_r = APIRouter(prefix="/inventory", tags=["Inventory"])
mkt_r = APIRouter(prefix="/marketing", tags=["Marketing"])
sup_r = APIRouter(prefix="/suppliers", tags=["Suppliers"])
qual_r = APIRouter(prefix="/quality", tags=["Quality"])
ops_r = APIRouter(prefix="/operations", tags=["Operations"])
rec_r = APIRouter(prefix="/recovery", tags=["Recovery"])
mer_r = APIRouter(prefix="/merchandising", tags=["Merchandising"])


def rec_dict(r: Recommendation) -> dict:
    return dict(rec_key=r.rec_key, engine=r.engine, category=r.category, product_id=r.product_id, location_id=r.location_id, entity_type=r.entity_type, entity_id=r.entity_id,
                title=r.title, problem=r.problem, why=r.why, action=r.action, department=r.department, impact_type=r.impact_type, estimated_value_egp=round(r.estimated_value_egp),
                estimated_loss_egp=round(r.estimated_loss_egp), confidence=round(r.confidence, 2), urgency=r.urgency, priority_score=r.priority_score, evidence=r.evidence,
                is_estimate=r.is_estimate, status=r.status, updated_at=r.updated_at.isoformat() if r.updated_at else None)


def _recs(db: Session, u: User, status="OPEN", category=None, urgency=None, department=None, product_id=None, location_id=None, ranked_only=False) -> list[dict]:
    q = select(Recommendation).where(Recommendation.status.in_(status.split(",")))
    if category: q = q.where(Recommendation.category == category)
    if urgency: q = q.where(Recommendation.urgency == urgency)
    if department: q = q.where(Recommendation.department == department)
    if product_id: q = q.where(Recommendation.product_id == product_id)
    if location_id: q = q.where(Recommendation.location_id == location_id)
    if ranked_only: q = q.where(Recommendation.priority_score > 0)
    rows = [rec_dict(r) for r in db.scalars(q.order_by(Recommendation.priority_score.desc()))]
    if not has(u, "suppliers"):
        rows = [r for r in rows if r["entity_type"] != "supplier"]
    if not has(u, "marketing") and u.role != "MARKETING_MANAGER":
        rows = [r for r in rows if r["entity_type"] != "campaign"]
    return strip_fields(u, scope_rows(u, rows))


# ------------------------------------------------------------------ executive
@exec_r.get("/overview")
def overview(db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    data = snap(db, "executive")
    if not data:
        raise HTTPException(404, "No analytics are available yet. Import the company data first.")
    return {**strip_fields(u, data), "freshness": freshness(db)}


@exec_r.get("/decisions")
def decisions(limit: int = Query(6, ge=1, le=20), db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    """'What needs your attention today': the best open decision from each business area, so the CEO sees breadth not noise."""
    rows = _recs(db, u, ranked_only=True)
    areas = {"REPLENISH": "Replenish", "RELOCATE": "Transfer inventory", "LOW_STOCK_PUSH": "Pause campaign", "PRODUCTION_ISSUE": "Pause campaign", "INVESTIGATE_SUPPLIER": "Investigate supplier",
             "FIX_BOTTLENECK": "Fix production issue", "MAINTAIN_MACHINE": "Fix production issue", "REPLENISH_SIZE": "Replenish size", "DISCOUNT": "Discount", "FIX_MARGIN": "Margin", "FIX_QUALITY": "Quality",
             "STOP_REPLENISHMENT": "Stop replenishment", "OVERSTOCK_UNDERSUPPORTED": "Support overstock", "SCALE": "Scale"}
    seen, out = set(), []
    for r in rows:
        a = areas.get(r["category"], r["category"])
        if a in seen:
            continue
        seen.add(a); out.append({**r, "area": a})
        if len(out) >= limit:
            break
    return {"items": out, "freshness": freshness(db)}


@exec_r.get("/recovery-opportunities")
def recovery_opps(p: PageParams = Depends(), category: str | None = None, urgency: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    rows = _recs(db, u, category=category, urgency=urgency, ranked_only=True)
    return paginate(rows, p, ("title", "problem", "department"), db, {"total_value_egp": round(sum(r["estimated_value_egp"] for r in rows))})


@rec_r.get("/priorities")
def priorities(p: PageParams = Depends(), category: str | None = None, urgency: str | None = None, department: str | None = None, status: str = "OPEN",
               db: Session = Depends(get_db), u: User = Depends(require("recovery"))):
    rows = _recs(db, u, status, category, urgency, department, ranked_only=True)
    p.sort = p.sort or "priority_score"
    return paginate(rows, p, ("title", "problem", "department", "action"), db, {"total_value_egp": round(sum(r["estimated_value_egp"] for r in rows)), "total_loss_egp": round(sum(r["estimated_loss_egp"] for r in rows))})


@mer_r.get("/overview")
def merch(db: Session = Depends(get_db), u: User = Depends(require("products"))):
    d = snap(db, "merchandising", {})
    return {**strip_fields(u, d), "freshness": freshness(db)}


# ------------------------------------------------------------------ products
def _pl(db, u):
    return scope_rows(u, snap(db, "product_location", []))


def _agg_products(rows: list[dict]) -> list[dict]:
    by: dict = {}
    for r in rows:
        by.setdefault(r["product_id"], []).append(r)
    out = []
    for pid, g in by.items():
        units, net, gp = sum(x["units_12m"] or 0 for x in g), sum(x["net_12m"] or 0 for x in g), sum(x["gp_12m"] or 0 for x in g)
        stock, vel = sum(x["closing_stock"] or 0 for x in g), sum(x["vel"] or 0 for x in g)
        top = max(g, key=lambda x: ((x["recommended_action"] not in (None, "MAINTAIN")), (x["estimated_value_egp"] or 0)))
        ret = sum((x["return_rate"] or 0) * (x["units_12m"] or 0) for x in g) / max(units, 1)
        out.append(dict(product_id=pid, sku=g[0]["sku"], product_name=g[0]["product_name"], product_family=g[0]["product_family"], catalog_season=g[0]["catalog_season"],
                        units_12m=units, net_12m=round(net), gp_12m=round(gp), margin_12m=round(gp / net, 4) if net else None, stock=stock, days_of_cover=round(min(stock / vel, 999), 1) if vel else None,
                        return_rate=round(ret, 4), recommended_action=top["recommended_action"], action_urgency=top["urgency"], action_value_egp=round(top["estimated_value_egp"] or 0),
                        stockout_risk=max((x["stockout_risk"] for x in g), key=lambda s: URG.get({"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}[s], 0)),
                        dead_risk=max((x["dead_risk"] for x in g), key=lambda s: URG.get(s, 0))))
    return out


@prod_r.get("")
def list_products(p: PageParams = Depends(), family: str | None = None, season: str | None = None, action: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("products"))):
    rows = _agg_products(_pl(db, u))
    rows = eq_filter(rows, product_family=family, catalog_season=season, recommended_action=action)
    p.sort = p.sort or "net_12m"
    return paginate(strip_fields(u, rows), p, ("product_name", "sku", "product_id"), db)


def _sql_series(db, u, product_id):
    t = TABLES["sales_transactions"]
    q = select(t.c.month_key, func.sum(t.c.quantity).label("units"), func.sum(t.c.net_sales_egp).label("net"), func.sum(t.c.gross_profit_egp).label("gp"),
               func.sum(t.c.refund_value_egp).label("refunds")).where(t.c.product_id == product_id).group_by(t.c.month_key).order_by(t.c.month_key)
    if u.role == "STORE_MANAGER":
        q = q.where(t.c.location_id.in_(u.allowed_locations or []))
    return [dict(month=r.month_key, units=int(r.units), net=round(r.net), gp=round(r.gp), refunds=round(r.refunds or 0)) for r in db.execute(q)]


@prod_r.get("/{product_id}")
def product_detail(product_id: str, db: Session = Depends(get_db), u: User = Depends(require("products"))):
    pm = TABLES["product_master"]
    row = db.execute(select(pm).where(pm.c.product_id == product_id)).mappings().first()
    if not row:
        raise HTTPException(404, f"Product {product_id} was not found.")
    locs = [r for r in _pl(db, u) if r["product_id"] == product_id]
    if not locs:
        raise HTTPException(403, "This product has no stock or sales in the locations you can access.")
    agg = _agg_products(locs)[0]
    audit(db, u, "product_viewed", "product", product_id)
    series = _sql_series(db, u, product_id)
    detail = dict(
        header=dict(product_id=product_id, sku=row["sku"], product_name=row["product_name"], brand=row["brand"], product_family=row["product_family"], season=row["catalog_season"],
                    gender=row["gender"], audience=row["audience"], sizes=row["sizes"], retail_price_egp=row["public_retail_price_egp"], image_url=None,
                    current_action=agg["recommended_action"], action_urgency=agg["action_urgency"]),
        kpis=dict(sales_12m=agg["net_12m"], units_12m=agg["units_12m"], margin=agg["margin_12m"], stock=agg["stock"], return_rate=agg["return_rate"], days_of_cover=agg["days_of_cover"]),
        performance=series, locations=locs, freshness=freshness(db))
    detail["sizes"] = [r for r in snap(db, "sizes", {}).get("rows", []) if r["product_id"] == product_id and (u.role != "STORE_MANAGER" or r["location_id"] in (u.allowed_locations or []))]
    detail["sizes_note"] = snap(db, "sizes", {}).get("note")
    if has(u, "marketing") or u.role == "MARKETING_MANAGER":
        mt = TABLES["marketing"]
        detail["marketing"] = [dict(r._mapping) for r in db.execute(select(mt.c.campaign_id, mt.c.campaign_name, mt.c.platform, mt.c.start_date, mt.c.end_date, mt.c.spend_egp, mt.c.attributed_revenue_egp, mt.c.orders_attributed)
                                                                  .where(mt.c.product_id == product_id).order_by(mt.c.start_date.desc()).limit(25))]
    qt = TABLES["quality"]
    qrows = db.execute(select(qt.c.stage, qt.c.defect_type, func.sum(qt.c.rejected_qty).label("rejected"), func.sum(qt.c.inspected_qty).label("inspected"), func.sum(qt.c.estimated_loss_egp).label("loss"))
                       .where(qt.c.product_id == product_id).group_by(qt.c.stage, qt.c.defect_type)).all()
    detail["quality"] = [dict(stage=r.stage, defect_type=r.defect_type, rejected=int(r.rejected), inspected=int(r.inspected), loss=round(r.loss or 0)) for r in qrows]
    if has(u, "operations") or has(u, "quality"):
        po = TABLES["production_orders"]
        pr = db.execute(select(func.count(), func.avg(po.c.efficiency_pct), func.avg(po.c.delay_days), func.sum(po.c.produced_qty), func.sum(po.c.rejected_qty)).where(po.c.product_id == product_id)).first()
        detail["production"] = dict(orders=pr[0], avg_efficiency=round(pr[1] or 0, 1), avg_delay_days=round(pr[2] or 0, 2), produced=pr[3], rejected=pr[4])
    detail["recommendations"] = _recs(db, u, "OPEN,ACCEPTED,DEFERRED", product_id=product_id)
    return strip_fields(u, detail)


@prod_r.get("/{product_id}/performance")
def product_performance(product_id: str, db: Session = Depends(get_db), u: User = Depends(require("products"))):
    if not any(r["product_id"] == product_id for r in _pl(db, u)):
        raise HTTPException(404, f"Product {product_id} was not found in your accessible data.")
    return strip_fields(u, {"series": _sql_series(db, u, product_id), "freshness": freshness(db)})


@prod_r.get("/{product_id}/recommendation")
def product_recommendation(product_id: str, db: Session = Depends(get_db), u: User = Depends(require("products"))):
    rows = [r for r in _pl(db, u) if r["product_id"] == product_id]
    if not rows:
        raise HTTPException(404, f"Product {product_id} was not found in your accessible data.")
    strat = next((s for s in snap(db, "product_strategy", []) if s["product_id"] == product_id), None) if has(u, "executive") or has(u, "costs") else None
    return strip_fields(u, {"by_location": [dict(location_id=r["location_id"], location_name=r["location_name"], action=r["recommended_action"], confidence=r["confidence"], reasons=r["top_reasons"],
                                                 value_egp=r["estimated_value_egp"], urgency=r["urgency"]) for r in rows],
                            "strategy": strat, "recommendations": _recs(db, u, "OPEN,ACCEPTED,DEFERRED", product_id=product_id), "freshness": freshness(db)})


@prod_r.get("/{product_id}/sizes")
def product_sizes(product_id: str, db: Session = Depends(get_db), u: User = Depends(require("products"))):
    s = snap(db, "sizes", {})
    rows = scope_rows(u, [r for r in s.get("rows", []) if r["product_id"] == product_id])
    if not rows:
        raise HTTPException(404, f"No size data for product {product_id}.")
    return {"rows": rows, "note": s.get("note"), "freshness": freshness(db)}


@prod_r.get("/strategy/all", include_in_schema=True)
def strategy_all(p: PageParams = Depends(), decision: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("executive"))):
    rows = eq_filter(snap(db, "product_strategy", []), decision=decision)
    p.sort = p.sort or "overall_score"
    return paginate(strip_fields(u, rows), p, ("product_name", "sku"), db)


# ------------------------------------------------------------------ inventory
@inv_r.get("/health")
def inventory_health(db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    rows = _pl(db, u)
    by_loc: dict = {}
    for r in rows:
        d = by_loc.setdefault(r["location_id"], dict(location_id=r["location_id"], location_name=r["location_name"], items=0, stock_units=0, stock_value=0.0, stockout_high=0, stockout_medium=0, dead_high=0, dead_medium=0, covers=[]))
        d["items"] += 1; d["stock_units"] += r["closing_stock"] or 0; d["stock_value"] += r["stock_value"] or 0
        d["stockout_high"] += r["stockout_risk"] == "HIGH"; d["stockout_medium"] += r["stockout_risk"] == "MEDIUM"
        d["dead_high"] += r["dead_risk"] == "HIGH"; d["dead_medium"] += r["dead_risk"] == "MEDIUM"
        d["covers"].append(r["doc"] or 0)
    locs = []
    for d in by_loc.values():
        c = sorted(d.pop("covers")); d["median_cover_days"] = round(c[len(c) // 2], 1) if c else None; d["stock_value"] = round(d["stock_value"]); locs.append(d)
    heat = [dict(product_id=r["product_id"], product_name=r["product_name"], location_id=r["location_id"], days_of_cover=round(min(r["doc"] or 0, 400), 1), stockout_risk=r["stockout_risk"], dead_risk=r["dead_risk"]) for r in rows]
    return strip_fields(u, {"locations": locs, "heatmap": heat, "freshness": freshness(db)})


@inv_r.get("/stockout-risk")
def stockout_risk(p: PageParams = Depends(), level: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"), location_id: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    rows = [r for r in _pl(db, u) if r["stockout_risk"] != "LOW" or level == "LOW"]
    rows = eq_filter(rows, stockout_risk=level, location_id=location_id)
    for r in rows:
        r["risk_message"] = {"HIGH": "HIGH STOCKOUT RISK - likely to run out before new stock can arrive.", "MEDIUM": "Watch: stock is close to the reorder point.", "LOW": "Low risk"}[r["stockout_risk"]]
    p.sort = p.sort or "estimated_value_egp"
    return paginate(strip_fields(u, rows), p, ("product_name", "sku", "location_name"), db)


@inv_r.get("/dead-stock")
def dead_stock(p: PageParams = Depends(), location_id: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    rows = eq_filter(scope_rows(u, snap(db, "dead_stock", [])), location_id=location_id)
    p.sort = p.sort or "stock_value_at_risk"
    return paginate(strip_fields(u, rows), p, ("product_name", "location_name"), db, {"total_stock_value_at_risk": None if not has(u, "costs") else round(sum(r["stock_value_at_risk"] or 0 for r in rows))})


@inv_r.get("/transfers")
def transfers(p: PageParams = Depends(), db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    rows = snap(db, "transfers", [])
    if u.role == "STORE_MANAGER":
        a = set(u.allowed_locations or []); rows = [r for r in rows if r["from_location"] in a or r["to_location"] in a]
    p.sort = p.sort or "revenue_protected"
    return paginate(strip_fields(u, rows), p, ("product_name", "from_name", "to_name"), db, {"note": "Transfers assume the inventory locations hold interchangeable physical stock. Transfer cost is not in the data and is taken from configuration."})


@inv_r.get("/lost-sales")
def lost_sales(db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    d = snap(db, "lost_sales", {})
    if u.role == "STORE_MANAGER":
        d = {**d, "by_pl": scope_rows(u, d.get("by_pl", [])), "summary": {"label": d.get("summary", {}).get("label")}, "by_month": []}
    return {**strip_fields(u, d), "freshness": freshness(db)}


@inv_r.get("/productivity")
def productivity(p: PageParams = Depends(), klass: str | None = Query(None, alias="class"), db: Session = Depends(get_db), u: User = Depends(require("inventory"))):
    if not has(u, "costs"):
        raise HTTPException(403, "Inventory productivity uses cost data your role cannot access.")
    rows = eq_filter(scope_rows(u, snap(db, "productivity", [])), **{"class": klass})
    p.sort = p.sort or "gmroi"
    return paginate(rows, p, ("product_name", "location_name"), db)


# ------------------------------------------------------------------ marketing
@mkt_r.get("/collisions")
def collisions(p: PageParams = Depends(), type: str | None = None, severity: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("marketing"))):
    rows = eq_filter(snap(db, "marketing", {}).get("collisions", []), type=type, severity=severity)
    return paginate(rows, p, ("campaign_name", "product_id", "why"), db)


@mkt_r.get("/performance")
def mkt_performance(db: Session = Depends(get_db), u: User = Depends(require("marketing"))):
    d = snap(db, "marketing", {})
    return {k: v for k, v in d.items() if k != "collisions"} | {"freshness": freshness(db)}


# ------------------------------------------------------------------ suppliers (procurement-sensitive)
@sup_r.get("/performance")
def sup_perf(p: PageParams = Depends(), db: Session = Depends(get_db), u: User = Depends(require("suppliers"))):
    rows = snap(db, "suppliers", {}).get("table", [])
    keep = ["supplier_id", "supplier_name", "primary_category", "orders", "on_time_rate", "acceptance_rate", "avg_delay_days", "avg_lead_days", "on_time_change_pp", "affected_products", "spend", "true_cost_score", "rank"]
    rows = [{k: r.get(k) for k in keep} for r in rows]
    p.sort = p.sort or "rank"; p.order = "asc" if p.sort == "rank" and p.order == "desc" else p.order
    return paginate(rows, p, ("supplier_name", "supplier_id"), db)


@sup_r.get("/true-cost")
def sup_true_cost(db: Session = Depends(get_db), u: User = Depends(require("suppliers"))):
    d = snap(db, "suppliers", {})
    return {**d, "freshness": freshness(db)}


# ------------------------------------------------------------------ quality / operations
@qual_r.get("/impact")
def quality_impact(db: Session = Depends(get_db), u: User = Depends(require("quality"))):
    return {**strip_fields(u, snap(db, "quality", {})), "caution": "Relationships shown are associations in the data. They do not prove that one problem caused another.", "freshness": freshness(db)}


@ops_r.get("/bottlenecks")
def bottlenecks(db: Session = Depends(get_db), u: User = Depends(require("operations"))):
    return {**snap(db, "operations", {}), "freshness": freshness(db)}

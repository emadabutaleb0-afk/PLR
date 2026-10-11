"""Workspace read models for the V5 frontend (notifications, command map, time machine, decision board, product 360, report catalog).

Everything here is READ-ONLY and built from existing tables / snapshots. Nothing in this module approves, executes or changes a business
record: approvals, action changes and transfers keep going through the existing /recommendations/.../feedback and /actions endpoints,
which enforce role scopes, the stale-data guard and audit logging.
Permissions mirror the rest of the API: scopes via require()/has(), location isolation via scope_rows(), cost fields via strip_fields().
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.deps import current_user, has, scope_rows, strip_fields
from app.models.app import (User, Recommendation, RecommendationFeedback, ActionItem, Alert, DecisionTracking, DataRefreshRun, FileHealth, AuditLog)
from app.models.tables import TABLES
from app.api.common import snap, freshness
from app.api.business import _recs, _pl, _agg_products
from app.api.actions import _get_rec, ACTION_STATUSES

router = APIRouter(prefix="/workspace", tags=["Workspace"])
DELAYED_AFTER_DAYS = 14          # an action that has not reached DONE/REJECTED after this long is shown as delayed (actions have no due date)
URG = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _month(v) -> str | None:
    return str(v)[:7] if v else None


def _allowed_locs(u: User):
    return set(u.allowed_locations or []) if u.role == "STORE_MANAGER" else None


# ======================================================================= notifications
@router.get("/notifications", summary="Real, permission-filtered work items: approvals, alerts, data issues, delayed actions, measured outcomes")
def notifications(db: Session = Depends(get_db), u: User = Depends(current_user)):
    items: list[dict] = []
    totals: dict[str, int] = {}
    allowed = _allowed_locs(u)
    now = datetime.utcnow()

    if has(u, "decide") and has(u, "recovery"):
        recs = [r for r in _recs(db, u, "OPEN", ranked_only=True) if r["urgency"] in ("CRITICAL", "HIGH")]
        totals["approval"] = len(recs)
        for r in recs[:15]:
            items.append(dict(id=f"approval:{r['rec_key']}", kind="approval", severity="CRITICAL" if r["urgency"] == "CRITICAL" else "WARNING", title=r["title"],
                              detail=f"Awaiting approval · estimated {round(r['estimated_value_egp']):,} EGP (estimate, confidence {round(r['confidence'] * 100)}%)",
                              entity=dict(type="decision", id=r["rec_key"], url="/war-room?open=" + r["rec_key"]), ts=r["updated_at"]))
    if has(u, "alerts"):
        rows = [a for a in db.scalars(select(Alert).where(Alert.status == "UNREAD").order_by(Alert.priority.desc(), Alert.created_at.desc()))
                if allowed is None or a.location_id in allowed]
        totals["alert"] = len(rows)
        for a in rows[:15]:
            items.append(dict(id=f"alert:{a.id}", kind="alert", severity=a.severity, title=a.title, detail=a.body[:200],
                              entity=dict(type="alert", id=str(a.id), url="/alerts"), ts=a.created_at.isoformat()))
    if has(u, "data_health"):
        bad = [f for f in db.scalars(select(FileHealth)) if f.status in ("WARNING", "FAILED", "MISSING")]
        fr = freshness(db)
        n = len(bad) + (1 if fr.get("status") in ("STALE", "NO_DATA") else 0)
        totals["data_quality"] = n
        if fr.get("status") in ("STALE", "NO_DATA"):
            items.append(dict(id="data:fresh", kind="data_quality", severity="WARNING", title="Business data is out of date" if fr["status"] == "STALE" else "No data imported yet",
                              detail=fr.get("message"), entity=dict(type="data", id="freshness", url="/data"), ts=fr.get("data_updated_at")))
        for f in bad[:10]:
            items.append(dict(id=f"data:{f.file}", kind="data_quality", severity="CRITICAL" if f.status in ("FAILED", "MISSING") else "WARNING", title=f.file,
                              detail=f"Status: {f.status.title()}", entity=dict(type="data", id=f.file, url="/data"), ts=f.file_modified.isoformat() if f.file_modified else None))
    if has(u, "actions"):
        open_ = [a for a in db.scalars(select(ActionItem).where(ActionItem.status.in_(["NEW", "UNDER_REVIEW", "APPROVED", "IN_PROGRESS"])).order_by(ActionItem.created_at))
                 if (now - a.created_at).days >= DELAYED_AFTER_DAYS]
        if allowed is not None:
            mine = {r.rec_key for r in db.scalars(select(Recommendation).where(Recommendation.location_id.in_(list(allowed))))}
            open_ = [a for a in open_ if a.rec_key in mine or a.owner_email == u.email]
        totals["delayed_action"] = len(open_)
        for a in open_[:15]:
            d = (now - a.created_at).days
            items.append(dict(id=f"action:{a.id}", kind="delayed_action", severity="WARNING", title=a.title, detail=f"Open for {d} days · status {a.status.replace('_', ' ').title()} · owner {a.owner_email or 'unassigned'}",
                              entity=dict(type="action", id=str(a.id), url="/war-room?action=" + str(a.id)), ts=a.created_at.isoformat(), age_days=d))
    if has(u, "value"):
        since = now - timedelta(days=30)
        done = list(db.scalars(select(DecisionTracking).where(DecisionTracking.status.in_(["MEASURED", "UNMEASURABLE"]), DecisionTracking.measured_at >= since).order_by(DecisionTracking.measured_at.desc())))
        if allowed is not None:
            done = [t for t in done if t.location_id in allowed]
        totals["outcome"] = len(done)
        for t in done[:10]:
            res = t.result or {}
            items.append(dict(id=f"outcome:{t.id}", kind="outcome", severity="INFO", title=f"Outcome {t.status.lower()}: {t.rec_key.split(':')[-1] if t.rec_key else t.id}",
                              detail=(f"Measured effect {res.get('effect_gp_egp'):,} EGP gross profit; " + ("stands out from placebo tests." if res.get("significant") else "not distinguishable from chance, so nothing is claimed.")) if t.status == "MEASURED" and res.get("effect_gp_egp") is not None else (res.get("reason") or "Measurement finished."), entity=dict(type="decision", id=t.rec_key, url="/decisions?tab=tracking"),
                              ts=t.measured_at.isoformat() if t.measured_at else None))
    items.sort(key=lambda x: ({"CRITICAL": 0, "WARNING": 1, "OPPORTUNITY": 2, "INFO": 3}.get(x["severity"], 3), x.get("ts") or ""), reverse=False)
    return dict(items=items, totals=totals, total=sum(totals.values()), generated_at=now.isoformat(), freshness=freshness(db),
                note=f"Actions have no due date in the data model, so 'delayed' means open for {DELAYED_AFTER_DAYS}+ days.")


# ======================================================================= command map
@router.get("/network", summary="Real relationships only: product-location, product-material (BOM), material-supplier (purchase orders), decision-product/location")
def network(limit: int = Query(30, ge=5, le=80), focus: str | None = Query(None, max_length=60), db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not (has(u, "products") or has(u, "suppliers") or has(u, "executive")):
        raise HTTPException(403, "Your role does not have access to the command map.")
    allowed = _allowed_locs(u)
    nodes: dict[str, dict] = {}
    edges: dict[tuple, dict] = {}

    def node(kind, id_, label, **data):
        nodes.setdefault(f"{kind}:{id_}", dict(id=f"{kind}:{id_}", kind=kind, ref=id_, label=label, data=data))

    def edge(a, b, rel, **data):
        if a in nodes and b in nodes:
            edges.setdefault((a, b, rel), dict(id=f"{a}>{b}>{rel}", source=a, target=b, rel=rel, data=data))

    pl = _pl(db, u)
    prods = {p["product_id"]: p for p in _agg_products(pl)} if has(u, "products") else {}
    recs = _recs(db, u, "OPEN", ranked_only=True) if has(u, "recovery") else []
    rec_by_prod: dict[str, list] = defaultdict(list)
    for r in recs:
        if r["product_id"]:
            rec_by_prod[r["product_id"]].append(r)
    # which products: the focus product, else those with the most open decision value, then the biggest sellers
    ranked = sorted(prods, key=lambda p: (-sum(r["estimated_value_egp"] for r in rec_by_prod.get(p, [])), -(prods[p]["net_12m"] or 0)))
    chosen = [focus] if focus and focus in prods else []
    chosen += [p for p in ranked if p not in chosen][: max(limit - len(chosen), 0)]

    lt = TABLES["locations"]
    for r in db.execute(select(lt.c.location_id, lt.c.location_name, lt.c.location_type, lt.c.channel, lt.c.governorate)):
        if allowed is None or r.location_id in allowed:
            node("location", r.location_id, r.location_name, type=r.location_type, channel=r.channel, governorate=r.governorate)
    if u.role != "STORE_MANAGER" and has(u, "executive"):
        bt, go = TABLES["business_units"], TABLES["group_operations"]
        last = {}
        for r in db.execute(select(go.c.month, go.c.business_unit, go.c.primary_kpi, go.c.volume, go.c.operational_efficiency_pct, go.c.open_issues_count).order_by(go.c.month)):
            last[r.business_unit] = dict(month=_month(r.month), kpi=r.primary_kpi, volume=r.volume, efficiency_pct=r.operational_efficiency_pct, open_issues=r.open_issues_count)
        for r in db.execute(select(bt.c.business_unit, bt.c.function, bt.c.public_capacity)):
            node("unit", r.business_unit, r.business_unit, function=r.function, capacity=r.public_capacity, latest=last.get(r.business_unit))

    sales_by_loc: dict[str, dict] = defaultdict(lambda: dict(net=0.0, units=0, stock=0))
    for r in pl:
        s = sales_by_loc[r["location_id"]]
        s["net"] += r["net_12m"] or 0; s["units"] += r["units_12m"] or 0; s["stock"] += r["closing_stock"] or 0
    for lid, s in sales_by_loc.items():
        n = nodes.get(f"location:{lid}")
        if n: n["data"].update(net_12m=round(s["net"]), units_12m=s["units"], stock_units=s["stock"])

    for pid in chosen:
        p = prods[pid]
        node("product", pid, p["product_name"], sku=p["sku"], family=p["product_family"], units_12m=p["units_12m"], net_12m=p["net_12m"], stock=p["stock"],
             days_of_cover=p["days_of_cover"], return_rate=p["return_rate"], open_decisions=len(rec_by_prod.get(pid, [])),
             open_decision_value_egp=round(sum(r["estimated_value_egp"] for r in rec_by_prod.get(pid, []))))
    for r in pl:
        if r["product_id"] in chosen:
            edge(f"product:{r['product_id']}", f"location:{r['location_id']}", "stocked_at", units_12m=r["units_12m"], stock=r["closing_stock"])

    if has(u, "suppliers"):
        bom, po = TABLES["product_bom"], TABLES["purchase_orders"]
        mats = set()
        for r in db.execute(select(bom.c.product_id, bom.c.material_id, bom.c.material_name, bom.c.required_per_unit, bom.c.unit).where(bom.c.product_id.in_(chosen))):
            node("material", r.material_id, r.material_name, unit=r.unit)
            edge(f"product:{r.product_id}", f"material:{r.material_id}", "uses", required_per_unit=r.required_per_unit, unit=r.unit)
            mats.add(r.material_id)
        sup = {r.supplier_id: r.supplier_name for r in db.execute(select(TABLES["suppliers"].c.supplier_id, TABLES["suppliers"].c.supplier_name))}
        agg: dict[tuple, dict] = defaultdict(lambda: dict(orders=0, ordered=0.0, rejected=0.0, delay=0, delayed_n=0))
        for r in db.execute(select(po.c.supplier_id, po.c.material_id, po.c.ordered_qty, po.c.rejected_qty, po.c.promised_date, po.c.actual_receipt_date).where(po.c.material_id.in_(mats))):
            a = agg[(r.supplier_id, r.material_id)]
            a["orders"] += 1; a["ordered"] += r.ordered_qty or 0; a["rejected"] += r.rejected_qty or 0
            if r.promised_date and r.actual_receipt_date:
                a["delayed_n"] += 1; a["delay"] += max((r.actual_receipt_date - r.promised_date).days, 0)
        for (sid, mid), a in agg.items():
            node("supplier", sid, sup.get(sid, sid))
            edge(f"material:{mid}", f"supplier:{sid}", "supplied_by", purchase_orders=a["orders"], rejected_rate=round(a["rejected"] / a["ordered"], 4) if a["ordered"] else None,
                 avg_delay_days=round(a["delay"] / a["delayed_n"], 2) if a["delayed_n"] else None)
        for sid in {s for s, _ in agg}:
            n = nodes[f"supplier:{sid}"]
            tot = [a for (s, _), a in agg.items() if s == sid]
            n["data"].update(purchase_orders=sum(a["orders"] for a in tot), materials_in_view=len(tot))

    for r in recs:
        if r["product_id"] in chosen or (r["location_id"] and not r["product_id"]):
            node("decision", r["rec_key"], r["title"], urgency=r["urgency"], value_egp=r["estimated_value_egp"], confidence=r["confidence"], category=r["category"],
                 department=r["department"], is_estimate=True)
            if r["product_id"] in chosen: edge(f"decision:{r['rec_key']}", f"product:{r['product_id']}", "concerns")
            if r["location_id"]: edge(f"decision:{r['rec_key']}", f"location:{r['location_id']}", "at_location")
    # decisions that reference a product outside the view would be dangling; edge() already drops them
    out_nodes = list(nodes.values())
    return strip_fields(u, dict(nodes=out_nodes, edges=list(edges.values()), total_products=len(prods), shown_products=len(chosen), focus=focus, freshness=freshness(db),
                                notes=["Edges come from stock/sales rows, the bill of materials, purchase orders and open recommendations. Nothing else is connected.",
                                       "Business units have no link to locations, products or suppliers in the data, so they are shown without connections.",
                                       "Decision values are estimates, not realised results."]))


@router.get("/scope-options", summary="Locations the signed-in user may filter by (location-restricted roles see only their own)")
def scope_options(db: Session = Depends(get_db), u: User = Depends(current_user)):
    allowed = _allowed_locs(u)
    lt = TABLES["locations"]
    locs = [dict(location_id=r.location_id, location_name=r.location_name, channel=r.channel) for r in db.execute(select(lt.c.location_id, lt.c.location_name, lt.c.channel).order_by(lt.c.location_name))
            if allowed is None or r.location_id in allowed]
    return dict(locations=locs)


# ======================================================================= time machine
def _series(db: Session, u: User, product_id: str | None, location_id: str | None, since: str | None, until: str | None):
    allowed = _allowed_locs(u)
    if location_id and allowed is not None and location_id not in allowed:
        raise HTTPException(403, "That location is outside the locations you manage.")
    out: dict[str, dict] = defaultdict(dict)
    cov: dict[str, dict] = {}

    def put(metric, month, val):
        if (since and month < since) or (until and month > until): return
        out[month][metric] = round(val, 2) if isinstance(val, float) else val
        c = cov.setdefault(metric, dict(first=month, last=month, months=0)); c["first"] = min(c["first"], month); c["last"] = max(c["last"], month)

    s = TABLES["sales_transactions"]
    q = select(s.c.month_key, s.c.quantity, s.c.net_sales_egp, s.c.gross_profit_egp, s.c.refund_value_egp, s.c.returned)
    if product_id: q = q.where(s.c.product_id == product_id)
    if location_id: q = q.where(s.c.location_id == location_id)
    if allowed is not None: q = q.where(s.c.location_id.in_(list(allowed)))
    agg: dict[str, list] = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0])
    for r in db.execute(q):
        a = agg[_month(r.month_key)]; a[0] += r.quantity or 0; a[1] += r.net_sales_egp or 0; a[2] += r.gross_profit_egp or 0; a[3] += r.refund_value_egp or 0; a[4] += 1 if r.returned else 0
    for m, a in agg.items():
        put("units_sold", m, int(a[0])); put("net_sales_egp", m, a[1]); put("returned_lines", m, a[4]); put("refunds_egp", m, a[3])
        if has(u, "costs"): put("gross_profit_egp", m, a[2])
    ih = TABLES["inventory_history"]
    if has(u, "inventory") or has(u, "products"):
        q = select(ih.c.snapshot_month, ih.c.closing_stock, ih.c.stockout_days_in_month)
        if product_id: q = q.where(ih.c.product_id == product_id)
        if location_id: q = q.where(ih.c.location_id == location_id)
        if allowed is not None: q = q.where(ih.c.location_id.in_(list(allowed)))
        ia: dict[str, list] = defaultdict(lambda: [0, 0])
        for r in db.execute(q):
            a = ia[_month(r.snapshot_month)]; a[0] += r.closing_stock or 0; a[1] += r.stockout_days_in_month or 0
        for m, a in ia.items():
            put("closing_stock_units", m, int(a[0])); put("stockout_days", m, int(a[1]))
    if (has(u, "operations") or has(u, "quality")) and not location_id and allowed is None:
        po = TABLES["production_orders"]
        q = select(po.c.completion_date, po.c.produced_qty, po.c.rejected_qty, po.c.efficiency_pct)
        if product_id: q = q.where(po.c.product_id == product_id)
        pa: dict[str, list] = defaultdict(lambda: [0, 0, 0.0, 0])
        for r in db.execute(q):
            m = _month(r.completion_date)
            if not m: continue
            a = pa[m]; a[0] += r.produced_qty or 0; a[1] += r.rejected_qty or 0; a[2] += r.efficiency_pct or 0; a[3] += 1
        for m, a in pa.items():
            put("units_produced", m, int(a[0])); put("units_rejected", m, int(a[1]))
            if a[3]: put("avg_efficiency_pct", m, a[2] / a[3])
    if has(u, "marketing") and not location_id and allowed is None:
        mt = TABLES["marketing"]
        q = select(mt.c.start_date, mt.c.spend_egp)
        if product_id: q = q.where(mt.c.product_id == product_id)
        ma: dict[str, float] = defaultdict(float)
        for r in db.execute(q):
            if r.start_date: ma[_month(r.start_date)] += r.spend_egp or 0
        for m, v in ma.items(): put("campaign_spend_egp", m, v)
    for k in cov: cov[k]["months"] = sum(1 for m in out if k in out[m])
    return dict(sorted(out.items())), cov


@router.get("/timeline", summary="Monthly history from the raw business tables plus real event markers. Metrics with no history are listed as unavailable.")
def timeline(product_id: str | None = Query(None, max_length=40), location_id: str | None = Query(None, max_length=40),
             since: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"), until: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
             db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not (has(u, "products") or has(u, "executive")):
        raise HTTPException(403, "Your role does not have access to the time machine.")
    if product_id and not any(r["product_id"] == product_id for r in _pl(db, u)):
        raise HTTPException(404, "That product was not found in your accessible data.")
    months, cov = _series(db, u, product_id, location_id, since, until)
    wanted = ["units_sold", "net_sales_egp", "returned_lines", "refunds_egp", "gross_profit_egp", "closing_stock_units", "stockout_days", "units_produced", "units_rejected", "avg_efficiency_pct", "campaign_spend_egp"]
    unavailable = [dict(metric=m, reason=("Your role cannot see this metric." if m in ("gross_profit_egp",) and not has(u, "costs") else
                                         "No history in the data for this selection.")) for m in wanted if m not in cov]
    markers: list[dict] = []

    def add(kind, date, label, **x):
        mo = _month(date)
        if mo and (not since or mo >= since) and (not until or mo <= until):
            markers.append(dict(kind=kind, date=str(date)[:10], month=mo, label=label, **x))

    if has(u, "marketing") and not location_id and allowed_none(u):
        mt = TABLES["marketing"]
        q = select(mt.c.campaign_id, mt.c.campaign_name, mt.c.platform, mt.c.start_date, mt.c.end_date, mt.c.spend_egp)
        if product_id: q = q.where(mt.c.product_id == product_id)
        for r in db.execute(q.order_by(mt.c.start_date.desc()).limit(60)):
            add("campaign_start", r.start_date, f"{r.campaign_name} starts ({r.platform})", ref=r.campaign_id, spend_egp=round(r.spend_egp or 0), url="/marketing")
            add("campaign_end", r.end_date, f"{r.campaign_name} ends", ref=r.campaign_id)
    if has(u, "recovery"):
        q = select(DecisionTracking).order_by(DecisionTracking.approved_at.desc()).limit(100)
        if product_id: q = q.where(DecisionTracking.product_id == product_id)
        allowed = _allowed_locs(u)
        for t in db.scalars(q):
            if allowed is not None and t.location_id not in allowed: continue
            add("approval", t.approved_at, f"Decision approved by {t.approved_by or 'a manager'}", ref=t.rec_key, expected_value_egp=round(t.expected_value_egp), url="/decisions?tab=tracking")
            if t.executed_at: add("execution", t.executed_at, "Decision marked as executed", ref=t.rec_key)
            if t.measured_at: add("outcome", t.measured_at, f"Outcome {t.status.lower()}", ref=t.rec_key)
    if has(u, "data_health") and not product_id:
        for r in db.scalars(select(DataRefreshRun).where(DataRefreshRun.mode == "import").order_by(DataRefreshRun.start_time.desc()).limit(24)):
            add("data_refresh", r.start_time, f"Data refresh {r.status.lower()} ({r.rows_loaded:,} rows)", ref=r.run_id, url="/data")
    markers.sort(key=lambda m: m["date"])
    return strip_fields(u, dict(
        months=[dict(month=m, **v) for m, v in months.items()], coverage=cov, unavailable=unavailable, markers=markers, scope=dict(product_id=product_id, location_id=location_id), freshness=freshness(db),
        notes=["History is rebuilt from the raw monthly tables. Recommendation and alert snapshots are stored as latest-only, so what the system recommended in an earlier month is NOT available.",
               "Event markers are only campaigns, approvals, executions, measured outcomes and data refreshes that were actually recorded."]))


def allowed_none(u: User) -> bool:
    return _allowed_locs(u) is None


# ======================================================================= product 360 context
@router.get("/products/{product_id}/context", summary="Cross-department context for one product: procurement chain, returns, inventory history, decision history")
def product_context(product_id: str, db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not has(u, "products"):
        raise HTTPException(403, "Your role does not have access to product details.")
    locs = [r for r in _pl(db, u) if r["product_id"] == product_id]
    if not locs:
        raise HTTPException(404, "That product was not found in your accessible data.")
    allowed = _allowed_locs(u)
    out: dict = dict(product_id=product_id, freshness=freshness(db))
    s = TABLES["sales_transactions"]
    q = select(s.c.return_reason, s.c.quality_related_return, s.c.refund_value_egp).where(s.c.product_id == product_id, s.c.returned == True)  # noqa: E712
    if allowed is not None: q = q.where(s.c.location_id.in_(list(allowed)))
    ra: dict[str, list] = defaultdict(lambda: [0, 0.0, 0])
    for r in db.execute(q):
        a = ra[r.return_reason or "Not recorded"]; a[0] += 1; a[1] += r.refund_value_egp or 0; a[2] += 1 if r.quality_related_return else 0
    out["returns"] = sorted([dict(reason=k, lines=a[0], refund_egp=round(a[1]), quality_related=a[2]) for k, a in ra.items()], key=lambda x: -x["lines"])
    ih = TABLES["inventory_history"]
    q = select(ih.c.snapshot_month, ih.c.closing_stock, ih.c.sold_qty, ih.c.received_qty, ih.c.stockout_days_in_month).where(ih.c.product_id == product_id)
    if allowed is not None: q = q.where(ih.c.location_id.in_(list(allowed)))
    ia: dict[str, list] = defaultdict(lambda: [0, 0, 0, 0])
    for r in db.execute(q):
        a = ia[_month(r.snapshot_month)]; a[0] += r.closing_stock or 0; a[1] += r.sold_qty or 0; a[2] += r.received_qty or 0; a[3] += r.stockout_days_in_month or 0
    out["inventory_history"] = [dict(month=m, closing_stock=a[0], sold=a[1], received=a[2], stockout_days=a[3]) for m, a in sorted(ia.items())]
    if has(u, "suppliers"):
        bom, po, st = TABLES["product_bom"], TABLES["purchase_orders"], TABLES["suppliers"]
        mats = [dict(material_id=r.material_id, material_name=r.material_name, required_per_unit=r.required_per_unit, unit=r.unit) for r in db.execute(
            select(bom.c.material_id, bom.c.material_name, bom.c.required_per_unit, bom.c.unit).where(bom.c.product_id == product_id))]
        names = {r.supplier_id: r.supplier_name for r in db.execute(select(st.c.supplier_id, st.c.supplier_name))}
        for m in mats:
            by: dict[str, list] = defaultdict(lambda: [0, 0.0, 0.0, 0, 0])
            for r in db.execute(select(po.c.supplier_id, po.c.ordered_qty, po.c.rejected_qty, po.c.promised_date, po.c.actual_receipt_date).where(po.c.material_id == m["material_id"])):
                a = by[r.supplier_id]; a[0] += 1; a[1] += r.ordered_qty or 0; a[2] += r.rejected_qty or 0
                if r.promised_date and r.actual_receipt_date: a[3] += 1; a[4] += max((r.actual_receipt_date - r.promised_date).days, 0)
            m["suppliers"] = sorted([dict(supplier_id=k, supplier_name=names.get(k, k), purchase_orders=a[0], rejected_rate=round(a[2] / a[1], 4) if a[1] else None,
                                          avg_delay_days=round(a[4] / a[3], 2) if a[3] else None) for k, a in by.items()], key=lambda x: -x["purchase_orders"])
        out["procurement"] = mats
    if has(u, "operations") or has(u, "quality"):
        po_ = TABLES["production_orders"]
        out["production_orders"] = [dict(production_order_id=r.production_order_id, completion_date=str(r.completion_date) if r.completion_date else None, planned_qty=r.planned_qty, good_qty=r.good_qty,
                                         rejected_qty=r.rejected_qty, efficiency_pct=r.efficiency_pct, delay_days=r.delay_days, primary_bottleneck=r.primary_bottleneck)
                                    for r in db.execute(select(po_.c.production_order_id, po_.c.completion_date, po_.c.planned_qty, po_.c.good_qty, po_.c.rejected_qty, po_.c.efficiency_pct, po_.c.delay_days,
                                                               po_.c.primary_bottleneck).where(po_.c.product_id == product_id).order_by(po_.c.completion_date.desc()).limit(12))]
    hist = []
    if has(u, "recovery"):
        for r in db.scalars(select(Recommendation).where(Recommendation.product_id == product_id).order_by(Recommendation.updated_at.desc()).limit(40)):
            if allowed is not None and r.location_id not in allowed: continue
            hist.append(dict(rec_key=r.rec_key, title=r.title, status=r.status, urgency=r.urgency, estimated_value_egp=round(r.estimated_value_egp), is_estimate=r.is_estimate, updated_at=r.updated_at.isoformat()))
    out["decision_history"] = hist
    if has(u, "value"):
        tr = []
        for t in db.scalars(select(DecisionTracking).where(DecisionTracking.product_id == product_id).order_by(DecisionTracking.approved_at.desc()).limit(20)):
            if allowed is not None and t.location_id not in allowed: continue
            tr.append(dict(rec_key=t.rec_key, status=t.status, approved_at=t.approved_at.isoformat(), executed_at=t.executed_at.isoformat() if t.executed_at else None,
                           expected_value_egp=round(t.expected_value_egp), measured=bool(t.result and t.status == "MEASURED"), result=t.result if t.status == "MEASURED" else None))
        out["tracking"] = tr
    return strip_fields(u, out)


# ======================================================================= decision board
LANES = [("open", "Awaiting decision"), ("deferred", "Deferred"), ("approved", "Approved · not started"), ("in_progress", "In progress"), ("measuring", "Executed · measuring"), ("measured", "Measured"), ("rejected", "Rejected")]


@router.get("/board", summary="Decision workflow lanes built from recommendation, action and tracking status (read-only)")
def board(limit: int = Query(40, ge=5, le=200), db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not has(u, "recovery") and not has(u, "actions"):
        raise HTTPException(403, "Your role does not have access to the decision board.")
    allowed = _allowed_locs(u)
    lanes: dict[str, list] = {k: [] for k, _ in LANES}
    total: dict[str, int] = {k: 0 for k, _ in LANES}
    visible = {r["rec_key"]: r for r in _recs(db, u, "OPEN,ACCEPTED,DEFERRED,REJECTED")} if has(u, "recovery") else {}
    tracks = {t.rec_key: t for t in db.scalars(select(DecisionTracking).order_by(DecisionTracking.approved_at))} if has(u, "value") else {}
    acts = {a.rec_key: a for a in db.scalars(select(ActionItem)) if a.rec_key}
    now = datetime.utcnow()

    def card(r: dict, lane: str, a: ActionItem | None = None, t: DecisionTracking | None = None):
        c = dict(rec_key=r["rec_key"], title=r["title"], category=r["category"], department=r["department"], urgency=r["urgency"], confidence=r["confidence"], product_id=r["product_id"],
                 location_id=r["location_id"], value_egp=r["estimated_value_egp"], value_kind="estimate" if r["is_estimate"] else "recorded", has_evidence=bool(r.get("evidence")), lane=lane)
        if a: c.update(action_id=a.id, action_status=a.status, owner_email=a.owner_email, age_days=(now - a.created_at).days)
        if t: c.update(tracking_status=t.status, measured=t.status == "MEASURED", measured_effect_gp_egp=(t.result or {}).get("effect_gp_egp") if t.status == "MEASURED" else None, claimable_gp_egp=(t.result or {}).get("claimable_gp_egp") if t.status == "MEASURED" else None)
        return c

    for key, r in visible.items():
        a, t = acts.get(key), tracks.get(key)
        if r["status"] == "OPEN": lane = "open"
        elif r["status"] == "DEFERRED": lane = "deferred"
        elif r["status"] == "REJECTED": lane = "rejected"
        else:
            if t and t.status == "MEASURED": lane = "measured"
            elif t and t.status in ("EXECUTED", "MEASURING"): lane = "measuring"
            elif a and a.status in ("IN_PROGRESS",): lane = "in_progress"
            elif a and a.status == "DONE": lane = "measuring"
            else: lane = "approved"
        total[lane] += 1
        lanes[lane].append(card(r, lane, a, t))
    for k in lanes:
        lanes[k] = sorted(lanes[k], key=lambda c: (-URG.get(c["urgency"], 0), -c["value_egp"]))[:limit]
    can_decide = has(u, "decide")
    return strip_fields(u, dict(lanes=[dict(key=k, label=label, total=total[k], cards=lanes[k]) for k, label in LANES], can_decide=can_decide, freshness=freshness(db),
                                transitions=dict(open=["approve", "defer", "reject"], deferred=["approve", "reject"], approved=["start"], in_progress=["done"]) if can_decide else {},
                                notes=["Cards move only through the existing approval and action endpoints. Dragging a card asks for confirmation and the server decides.",
                                       "Values on open and approved cards are estimates. Only the Measured lane can show a measured effect."]))


@router.get("/decisions/history", summary="Activity history of one decision: feedback, action item, tracking and audit trail")
def decision_history(rec_key: str = Query(max_length=160), db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not has(u, "recovery"):
        raise HTTPException(403, "Your role does not have access to decisions.")
    r = _get_rec(db, u, rec_key)
    ev: list[dict] = [dict(ts=r.created_at.isoformat(), kind="detected", actor="system", text=f"Detected by the {r.engine} engine (estimate)")]
    for f in db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.rec_key == rec_key).order_by(RecommendationFeedback.ts)):
        ev.append(dict(ts=f.ts.isoformat(), kind=f.decision.lower(), actor=f.user_email, text={"ACCEPT": "Approved", "DEFER": "Deferred", "REJECT": "Rejected"}.get(f.decision, f.decision.title()), comment=f.comment))
        if f.outcome_ts: ev.append(dict(ts=f.outcome_ts.isoformat(), kind="outcome_entered", actor=f.user_email, text="Realised value entered manually", comment=f.outcome_note))
    a = db.scalars(select(ActionItem).where(ActionItem.rec_key == rec_key)).first()
    if a: ev.append(dict(ts=a.created_at.isoformat(), kind="action_created", actor=a.owner_email, text=f"Action item created · now {a.status.replace('_', ' ').title()}"))
    for t in db.scalars(select(DecisionTracking).where(DecisionTracking.rec_key == rec_key).order_by(DecisionTracking.approved_at)):
        if t.executed_at: ev.append(dict(ts=t.executed_at.isoformat(), kind="executed", actor=None, text="Execution recorded; measurement window started"))
        if t.measured_at: ev.append(dict(ts=t.measured_at.isoformat(), kind="measured", actor="system", text=f"Measurement {t.status.lower()}"))
    if has(u, "audit_view"):
        for l in db.scalars(select(AuditLog).where(AuditLog.entity == "recommendation", AuditLog.entity_id == rec_key).order_by(AuditLog.ts).limit(50)):
            ev.append(dict(ts=l.ts.isoformat(), kind="audit", actor=l.user_email, text=l.action.replace("_", " ")))
    ev.sort(key=lambda e: e["ts"])
    return dict(rec_key=rec_key, status=r.status, events=ev)


# ======================================================================= analytics catalogue (Power BI readiness)
REPORTS = [
    dict(id="recommendations", title="Decisions and estimated value", scope="recovery", grain="one row per open/accepted/deferred decision", dataset="recommendations", refresh="after each data refresh"),
    dict(id="products", title="Product performance (12 months)", scope="products", grain="one row per product", dataset="products", refresh="after each data refresh", cost_fields_need="costs"),
    dict(id="dead-stock", title="Dead and slow stock", scope="inventory", grain="one row per product x location", dataset="dead-stock", refresh="after each data refresh", cost_fields_need="costs"),
    dict(id="suppliers", title="Supplier true-cost ranking", scope="suppliers", grain="one row per supplier", dataset="suppliers", refresh="after each data refresh"),
]


@router.get("/reports", summary="Approved reporting views a BI tool (for example Power BI Desktop on-premise) may use through the existing export endpoints")
def reports(db: Session = Depends(get_db), u: User = Depends(current_user)):
    ok = [dict(r, endpoint=f"/api/v1/export/{r['dataset']}?format=csv", formats=["csv", "xlsx"], available=has(u, "export") and has(u, r["scope"])) for r in REPORTS if has(u, r["scope"])]
    return dict(reports=ok, can_export=has(u, "export"), freshness=freshness(db),
                requirements=["Exports use the signed-in user's role: cost columns and location rows are filtered exactly as in the application.",
                              "Power BI Desktop or Report Server can read the CSV/XLSX files or the API on the company network. Embedding Power BI reports inside this application is NOT implemented.",
                              "Embedding needs a Power BI Report Server (on-premise) or licensed capacity, a service account and an agreed security model; those are infrastructure decisions for the company's IT.",
                              "No company data is sent to any cloud service by this application."])

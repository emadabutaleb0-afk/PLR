from __future__ import annotations
import csv, io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.deps import require, current_user, has, scope_rows, strip_fields
from app.models.app import User, AuditLog, ModelRecord, Recommendation
from app.models.tables import TABLES
from app.api.common import snap, freshness, PageParams, paginate
from app.api.business import _recs
from app.services.audit import audit
from app.monitoring.metrics import MODEL_AGE

search_r = APIRouter(prefix="/search", tags=["Search"])
export_r = APIRouter(prefix="/export", tags=["Export"])
admin_r = APIRouter(prefix="/admin", tags=["Administration & Monitoring"])


@search_r.get("")
def global_search(q: str = Query(min_length=2, max_length=60), db: Session = Depends(get_db), u: User = Depends(current_user)):
    like = f"%{q}%"
    out = []
    if has(u, "products"):
        pm = TABLES["product_master"]
        allowed = {r["product_id"] for r in scope_rows(u, snap(db, "product_location", []))}
        for r in db.execute(select(pm.c.product_id, pm.c.product_name, pm.c.sku).where(or_(pm.c.product_name.ilike(like), pm.c.sku.ilike(like), pm.c.product_id.ilike(like))).limit(8)):
            if r.product_id in allowed:
                out.append(dict(type="Product", id=r.product_id, label=r.product_name, sub=r.sku, url=f"/products/{r.product_id}"))
    if u.role != "STORE_MANAGER":
        lt = TABLES["locations"]
        for r in db.execute(select(lt.c.location_id, lt.c.location_name).where(lt.c.location_name.ilike(like)).limit(5)):
            out.append(dict(type="Location", id=r.location_id, label=r.location_name, sub=r.location_id, url="/inventory"))
    if has(u, "suppliers"):
        st, mt = TABLES["suppliers"], TABLES["materials"]
        for r in db.execute(select(st.c.supplier_id, st.c.supplier_name).where(or_(st.c.supplier_name.ilike(like), st.c.supplier_id.ilike(like))).limit(5)):
            out.append(dict(type="Supplier", id=r.supplier_id, label=r.supplier_name, sub=r.supplier_id, url="/suppliers"))
        for r in db.execute(select(mt.c.material_id, mt.c.material_name).where(or_(mt.c.material_name.ilike(like), mt.c.material_id.ilike(like))).limit(5)):
            out.append(dict(type="Material", id=r.material_id, label=r.material_name, sub=r.material_id, url="/suppliers"))
    if has(u, "marketing"):
        ct = TABLES["marketing"]
        for r in db.execute(select(ct.c.campaign_id, ct.c.campaign_name).where(or_(ct.c.campaign_name.ilike(like), ct.c.campaign_id.ilike(like))).limit(5)):
            out.append(dict(type="Campaign", id=r.campaign_id, label=r.campaign_name, sub=r.campaign_id, url="/marketing"))
    if has(u, "costs") or u.role == "STORE_MANAGER":
        s = TABLES["sales_transactions"]
        qy = select(s.c.invoice_id, s.c.order_date, s.c.location_id).where(s.c.invoice_id.ilike(like + "")).limit(5)
        if u.role == "STORE_MANAGER":
            qy = qy.where(s.c.location_id.in_(u.allowed_locations or []))
        seen = set()
        for r in db.execute(qy):
            if r.invoice_id not in seen:
                seen.add(r.invoice_id); out.append(dict(type="Invoice", id=r.invoice_id, label=r.invoice_id, sub=str(r.order_date), url=None))
    return {"query": q, "results": out}


# ---------------------------------------------------------------- exports
def _dataset(db, u, name):
    if name == "recommendations":
        rows = _recs(db, u, "OPEN,ACCEPTED,DEFERRED", ranked_only=True)
        return [{k: r[k] for k in ("priority_score", "title", "category", "department", "urgency", "estimated_value_egp", "estimated_loss_egp", "confidence", "action", "status")} for r in rows], "export"
    if name == "products":
        from app.api.business import _agg_products, _pl
        return strip_fields(u, _agg_products(_pl(db, u))), "products"
    if name == "dead-stock":
        if not has(u, "inventory"): raise HTTPException(403, "No access to inventory data.")
        return strip_fields(u, scope_rows(u, snap(db, "dead_stock", []))), "inventory"
    if name == "suppliers":
        if not has(u, "suppliers"): raise HTTPException(403, "Procurement details are not available to your role.")
        return [{k: r.get(k) for k in ("supplier_id", "supplier_name", "orders", "on_time_rate", "acceptance_rate", "avg_delay_days", "spend", "observed_cost", "estimated_risk_cost", "true_cost_index", "true_cost_score", "rank")}
                for r in snap(db, "suppliers", {}).get("table", [])], "suppliers"
    raise HTTPException(404, "Unknown dataset. Use: recommendations, products, dead-stock, suppliers, executive-summary.")


def _pdf(db, u) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib import colors
    ex = snap(db, "executive", {}); st = getSampleStyleSheet(); buf = io.BytesIO()
    from app.services.company import get_company_name
    comp = get_company_name(db).get("company_name", "Business Gate")
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"{comp.upper()} - Executive summary")
    f = freshness(db)
    el = [Paragraph(f"{comp.upper()} - Executive summary", st["Title"]), Paragraph(f"{f['message']} (data as of {f.get('data_as_of')})", st["Normal"]), Spacer(1, 12)]
    k = [["KPI", "Value"]]
    for x in ex.get("kpis", []):
        v = x["value"]; k.append([x["label"], f"{v:.1%}" if x["unit"] == "pct" else (f"{v:.1f}x" if x["unit"] == "x" else f"EGP {v:,.0f}")])
    t = Table(k, colWidths=[260, 160]); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.grey)]))
    el += [t, Spacer(1, 14), Paragraph("Top decisions (estimates)", st["Heading2"])]
    for r in _recs(db, u, ranked_only=True)[:10]:
        el.append(Paragraph(f"<b>{r['title']}</b><br/>{r['action']}<br/>Expected impact EGP {r['estimated_value_egp']:,.0f} - confidence {r['confidence']:.0%} - {r['urgency']}", st["Normal"])); el.append(Spacer(1, 6))
    doc.build(el)
    return buf.getvalue()


@export_r.get("/{dataset}")
def export(dataset: str, format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"), db: Session = Depends(get_db), u: User = Depends(require("export"))):
    audit(db, u, "export", "dataset", dataset, {"format": format})
    stamp = datetime.utcnow().strftime("%Y%m%d")
    if dataset == "executive-summary" or format == "pdf":
        if not has(u, "executive") and dataset == "executive-summary":
            raise HTTPException(403, "The executive summary is not available to your role.")
        return StreamingResponse(io.BytesIO(_pdf(db, u)), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="merch-brain-summary-{stamp}.pdf"'})
    rows, _ = _dataset(db, u, dataset)
    if not rows:
        raise HTTPException(404, "There is nothing to export for this dataset yet.")
    cols = [c for c in rows[0].keys() if not isinstance(rows[0][c], (list, dict))]
    if format == "csv":
        buf = io.StringIO(); w = csv.writer(buf); w.writerow(cols)
        for r in rows:
            w.writerow([("'" + str(r.get(c)) if isinstance(r.get(c), str) and str(r.get(c))[:1] in "=+-@" else r.get(c)) for c in cols])   # CSV-injection safe
        return StreamingResponse(io.BytesIO(buf.getvalue().encode("utf-8-sig")), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{dataset}-{stamp}.csv"'})
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = dataset[:30]; ws.append(cols)
    for r in rows:
        ws.append([("'" + str(r.get(c)) if isinstance(r.get(c), str) and str(r.get(c))[:1] in "=+-@" else r.get(c)) for c in cols])
    b = io.BytesIO(); wb.save(b); b.seek(0)
    return StreamingResponse(b, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{dataset}-{stamp}.xlsx"'})


# ---------------------------------------------------------------- admin / monitoring
@admin_r.get("/audit-logs")
def audit_logs(p: PageParams = Depends(), action: str | None = None, db: Session = Depends(get_db), u: User = Depends(require("audit_view"))):
    q = select(AuditLog).order_by(AuditLog.ts.desc()).limit(2000)
    if action: q = q.where(AuditLog.action == action)
    rows = [dict(ts=a.ts.isoformat(), user=a.user_email, action=a.action, entity=a.entity, entity_id=a.entity_id, detail=a.detail) for a in db.scalars(q)]
    return paginate(rows, p, ("user", "action", "entity_id"))


@admin_r.get("/models")
def models(db: Session = Depends(get_db), u: User = Depends(require("models"))):
    active = db.scalars(select(ModelRecord).where(ModelRecord.is_active == True).order_by(ModelRecord.name)).all()  # noqa: E712
    hist = db.scalars(select(ModelRecord).order_by(ModelRecord.trained_at.desc()).limit(120)).all()
    out = []
    for m in active:
        age = (datetime.utcnow() - m.trained_at).days
        MODEL_AGE.labels(m.name).set(age)
        prev = [h for h in hist if h.name == m.name and h.id != m.id][:5]
        drift = None
        pm = (m.prediction_stats or {}).get("mean")
        if pm is not None and prev and (prev[0].prediction_stats or {}).get("mean") not in (None, 0):
            base = prev[0].prediction_stats["mean"]; drift = round((pm - base) / abs(base), 3)
        out.append(dict(name=m.name, version=m.version, algorithm=m.algorithm, trained_at=m.trained_at.isoformat(), age_days=age, train_window=m.train_window, rows_train=m.rows_train, rows_valid=m.rows_valid,
                        metrics=m.metrics, feature_importance=m.feature_importance, prediction_stats=m.prediction_stats, prediction_mean_change_vs_previous=drift,
                        stale=age > 45, note="Technical view for analysts. Executive screens only show business-language risk levels."))
    return {"models": out}


@admin_r.get("/system")
def system(db: Session = Depends(get_db), u: User = Depends(require("audit_view"))):
    from app.core.config import get_settings
    from app.core.cache import _r
    return {"environment": get_settings().environment, "database": "ok", "redis": "ok" if _r() else "not configured (in-process cache)", "celery": get_settings().celery_enabled}

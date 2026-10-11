"""Everything that happens after a successful load: features -> analytics views -> ML -> decision engines -> recommendations -> alerts."""
from __future__ import annotations
import logging
import pandas as pd
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.app import Recommendation, Alert, AnalyticsSnapshot, ModelRecord, now
from app.analytics.context import load_ctx
from app.analytics.features import build_features
from app.analytics import kpi
from app.ml.models import train_and_predict
from app.intelligence import inventory as inv_e, sizes as size_e, marketing as mkt_e, margin as mar_e, suppliers as sup_e, quality as qual_e, operations as ops_e
from app.intelligence import strategy as strat_e, recovery as rec_e, alerts as alert_e
from app.intelligence import leakage as leak_e, materials as mat_e, allocation as alloc_e, discount as disc_e, command as cmd_e, scenarios as scen_e, customers as cust_e
from app.intelligence.common import records, clean
from app.optimization import portfolio as portfolio_e
from app.intelligence import autopsy as autopsy_e

log = logging.getLogger("merchbrain.post_load")


def compute_all(db, run_ml=True) -> dict:
    cfg = get_settings()
    c = load_ctx(db)
    f = build_features(c, cfg)
    ml = train_and_predict(c, cfg.model_directory) if run_ml else None
    if ml is None:
        raise RuntimeError("ML disabled")
    pl = inv_e.prepare_pl(c, f, ml, cfg)
    tr = inv_e.optimise_transfers(pl, cfg)
    ds = inv_e.dead_stock(pl, c, f, cfg, tr)
    actions, rec_pa = inv_e.product_actions(pl, ds, tr, f, c, cfg)
    lost, prodv = inv_e.lost_sales(c, f), inv_e.productivity(c, f, cfg)
    sz = size_e.size_curve(c, pl, cfg)
    mkp = mkt_e.performance(c)
    coll, rec_coll = mkt_e.collisions(c, f, pl, cfg)
    mg = mar_e.margin_erosion(c, f, cfg)
    sup = sup_e.supplier_engine(c, f, cfg)
    ql = qual_e.quality_engine(c, f, cfg)
    ops = ops_e.operations_engine(c, f, cfg)
    strat = strat_e.strategy(c, f, pl, mg, sup, mkp, ql, actions, cfg)
    all_recs = rec_pa + sz["recs"] + rec_coll + mg["recs"] + sup["recs"] + ql["recs"] + ops["recs"]
    uniq: dict = {}
    for x in all_recs:                      # rec_key must be unique: keep the highest-value one if two engines collide
        if x["rec_key"] not in uniq or x["estimated_value_egp"] > uniq[x["rec_key"]]["estimated_value_egp"]:
            uniq[x["rec_key"]] = x
    all_recs = list(uniq.values())
    ranked = rec_e.prioritise(all_recs)
    alerts = alert_e.build_alerts(ranked)
    ex = kpi.executive(c, f, pl, ranked, lost, ds, mkp, ops, ml["registry"])
    merch = kpi.merchandising(c, pl, actions, strat, sz)
    leak = leak_e.profit_leakage(c, f, pl, lost, ds, cfg)
    supply = mat_e.supply_readiness(c, f, pl, cfg)
    alloc = alloc_e.channel_allocation(pl, cfg)
    disc = disc_e.discount_intelligence(c, f, cfg)
    cmd = cmd_e.command_center(pl, ranked, ex, leak, supply, disc)
    scen = scen_e.scenario_base(c, f, pl, cfg)
    cust = cust_e.customer_intelligence(c, cfg)
    stock = {(a, b): float(s) for a, b, s in zip(pl.product_id, pl.location_id, pl.closing_stock)}
    plans = portfolio_e.build_plans(all_recs, stock, cfg)
    autopsy = autopsy_e.business_autopsy(mg, leak, disc, ql, sup, ops, cfg, lost=lost, coll=coll)
    return dict(autopsy=autopsy, plans=plans, ctx=c, feats=f, ml=ml, pl=pl, transfers=tr, dead=ds, actions=actions, lost=lost, productivity=prodv, sizes=sz, mkt=mkp, collisions=coll,
                margin=mg, suppliers=sup, quality=ql, ops=ops, strategy=strat, recs=all_recs, ranked=ranked, alerts=alerts, executive=ex, merch=merch, leakage=leak, supply=supply, allocation=alloc, discounts=disc, command=cmd, scenario=scen, customers=cust, cfg=cfg)


def _snap(db, key, payload, run_id):
    row = db.get(AnalyticsSnapshot, key) or AnalyticsSnapshot(key=key, payload={})
    row.payload, row.run_id, row.updated_at = clean(payload), run_id, now()
    db.add(row)


def refresh_everything(db, run_id, step, run_ml=True):
    step("features", 0.62)
    r = compute_all(db, run_ml)
    step("analytics", 0.78)
    c, pl = r["ctx"], r["pl"]
    lname = c.loc.set_index("location_id").location_name.to_dict()
    pname = c.product.set_index("product_id").product_name.to_dict()
    # ---- snapshots (the API serves these; heavy work is never done on request)
    cols = ["product_id", "location_id", "product_name", "sku", "product_family", "catalog_season", "location_name", "channel", "closing_stock", "doc", "doc_file", "vel", "forecast_90d_units",
            "net_unit", "gp_unit", "cogs_unit", "stock_value", "units_12m", "net_12m", "gp_12m", "margin_12m", "return_rate", "quality_return_rate", "discount_depth", "v90", "v90_ly", "yoy", "trend",
            "stockout_days_3m", "stockout_risk", "dead_risk", "supplier_lead_time_days", "reorder_point_units", "safety_stock_units", "p_stockout_risk", "p_dead_stock_risk"]
    plr = pl[[x for x in cols if x in pl]].merge(r["actions"][["product_id", "location_id", "recommended_action", "confidence", "top_reasons", "estimated_value_egp", "urgency", "expected_business_impact"]], on=["product_id", "location_id"], how="left")
    _snap(db, "product_location", records(plr), run_id)
    _snap(db, "product_strategy", records(r["strategy"]), run_id)
    _snap(db, "executive", r["executive"], run_id)
    _snap(db, "merchandising", r["merch"], run_id)
    _snap(db, "leakage", r["leakage"], run_id)
    _snap(db, "supply", r["supply"], run_id)
    _snap(db, "allocation", r["allocation"], run_id)
    _snap(db, "discounts", r["discounts"], run_id)
    _snap(db, "command_center", r["command"], run_id)
    _snap(db, "scenario_base", r["scenario"], run_id)
    _snap(db, "customers", r["customers"], run_id)
    _snap(db, "decision_plans", r["plans"], run_id)
    _snap(db, "autopsy", r["autopsy"], run_id)
    _snap(db, "dead_stock", records(r["dead"][["product_id", "location_id", "product_name", "location_name", "closing_stock", "doc", "excess_units", "stock_value_at_risk", "p_dead", "expected_loss", "dead_risk", "primary_action", "recoverable_value", "md_discount", "md_max_discount", "md_units_cleared", "transfer_out_units"]].assign(options=r["dead"].options.astype(str))) if len(r["dead"]) else [], run_id)
    _snap(db, "transfers", records(r["transfers"].assign(product_name=r["transfers"].product_id.map(pname), from_name=r["transfers"].from_location.map(lname), to_name=r["transfers"].to_location.map(lname),
                                                         revenue_protected=lambda d: d[["units", "to_deficit"]].min(axis=1) * d.net_unit_to)) if len(r["transfers"]) else [], run_id)
    _snap(db, "lost_sales", dict(summary=r["lost"]["summary"], by_month=records(r["lost"]["by_month"].assign(month=r["lost"]["by_month"].month.dt.strftime("%Y-%m"))),
                                  by_pl=records(r["lost"]["by_pl"].merge(pl[["product_id", "location_id", "product_name", "location_name"]], on=["product_id", "location_id"]).sort_values("lost_revenue_12m", ascending=False).head(100))), run_id)
    _snap(db, "productivity", records(r["productivity"]), run_id)
    _snap(db, "sizes", dict(note=r["sizes"]["note"], rows=records(r["sizes"]["rows"][["product_id", "location_id", "product_name", "location_name", "size", "units_r", "units_b", "share_r", "share_b", "return_rate", "size_return_rate", "recommended_share", "reorder_units", "share_shift_pp", "risk"]]),
                            family_location=records(r["sizes"]["family_location"]), segment=records(r["sizes"]["segment"])), run_id)
    _snap(db, "marketing", dict(summary=r["mkt"]["summary"], by_platform=records(r["mkt"]["by_platform"]), by_product=records(r["mkt"]["by_product"]),
                                by_month=records(r["mkt"]["by_month"].assign(month=r["mkt"]["by_month"].month.dt.strftime("%Y-%m"))), collisions=records(r["collisions"]) if len(r["collisions"]) else []), run_id)
    _snap(db, "margin", dict(table=records(r["margin"]["table"]), effects=records(r["margin"]["effects"]), weights=r["margin"]["weights"]), run_id)
    s = r["suppliers"]
    _snap(db, "suppliers", dict(table=records(s["table"]), by_material=records(s["by_material"]), trend=records(s["trend"].assign(month=s["trend"].month.dt.strftime("%Y-%m"))), association=s["association"], labels=s["labels"]), run_id)
    q = r["quality"]
    _snap(db, "quality", dict(pareto=records(q["pareto"]), causes=records(q["causes"]), stage=records(q["stage"]), products=records(q["products"].head(50)), returns=records(q["returns"]),
                              monthly=records(q["monthly"].assign(month=q["monthly"].month.dt.strftime("%Y-%m"))), findings=q["findings"], cost_of_poor_quality=q["cost_of_poor_quality"]), run_id)
    o = r["ops"]
    _snap(db, "operations", dict(kpis=o["kpis"], bottlenecks=records(o["bottlenecks"]), lines=records(o["lines"]), monthly=records(o["monthly"].assign(month=o["monthly"].month.dt.strftime("%Y-%m"))),
                                 machines=records(o["machines"]), downtime_reasons=records(o["downtime_reasons"]), downtime_trend=records(o["downtime_trend"]), printing=records(o["printing"]),
                                 print_defects=records(o["print_defects"]), downtime_link=clean(o["downtime_link"]), group_ops=records(o["group_ops"].assign(month=o["group_ops"].month.dt.strftime("%Y-%m")))), run_id)
    # ---- model registry + monitoring
    step("ml", 0.86)
    for m in db.scalars(select(ModelRecord).where(ModelRecord.is_active == True)):  # noqa: E712
        m.is_active = False
    for m in r["ml"]["registry"]:
        db.add(ModelRecord(name=m["name"], version=m["version"], algorithm=m.get("algorithm", ""), rows_train=m.get("rows_train", 0), rows_valid=m.get("rows_valid", 0), metrics=clean(m.get("metrics")),
                           feature_importance=clean(m.get("feature_importance")), train_window=m.get("train_window"), path=m.get("path"), prediction_stats=clean(m.get("prediction_stats")), is_active=True))
    # ---- recommendations (stable rec_key; keep user decisions, expire stale open ones)
    step("recommendations", 0.92)
    existing = {x.rec_key: x for x in db.scalars(select(Recommendation))}
    seen = set()
    rank_set = {x["rec_key"]: x for x in r["ranked"]}
    for rec in r["recs"]:
        k = rec["rec_key"]
        rec = clean({**rec, "priority_score": rank_set.get(k, rec).get("priority_score", 0.0) if k in rank_set else 0.0})   # numpy -> plain python (PostgreSQL drivers reject numpy scalars)
        seen.add(k)
        row = existing.get(k)
        if row is None:
            db.add(Recommendation(**rec, run_id=run_id))
        else:
            for a, v in rec.items():
                setattr(row, a, v)
            row.run_id, row.updated_at = run_id, now()
            if row.status == "EXPIRED":
                row.status = "OPEN"
    for k, row in existing.items():
        if k not in seen and row.status == "OPEN":
            row.status = "EXPIRED"
    old = {a.alert_key: a for a in db.scalars(select(Alert))}
    keys = set()
    for a in clean(r["alerts"]):
        keys.add(a["alert_key"])
        row = old.get(a["alert_key"])
        if row is None:
            db.add(Alert(**a))
        else:
            row.priority, row.title, row.body, row.severity = a["priority"], a["title"], a["body"], a["severity"]
    for k, row in old.items():
        if k not in keys and row.status != "RESOLVED":
            row.status = "RESOLVED"
    db.commit()
    try:                                   # newly arrived data may complete the after-window of executed decisions
        from app.services import outcomes
        outcomes.measure_due(db)
    except Exception:
        log.exception("outcome measurement failed (the refresh itself is fine)")
    log.info("post-load complete: %s recommendations, %s ranked, %s alerts", len(r["recs"]), len(r["ranked"]), len(r["alerts"]))

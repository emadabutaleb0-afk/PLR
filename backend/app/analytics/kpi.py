"""KPI engine: executive, merchandising and inventory payloads (small JSON documents refreshed after each import)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import records, num, clean


def _period(c: Ctx, days, start=0):
    s = window(c.sales, "order_date", c.as_of, days + start, start)
    r = s.returned.fillna(False).astype(bool)
    return dict(revenue=float(s.net_sales_egp.sum()), gp=float(s.gross_profit_egp.sum()), units=int(s.quantity.sum()), refunds=float(s.refund_value_egp.fillna(0).sum()),
                returns_units=int(s.quantity[r].sum()))


def _chg(a, b):
    return None if not b else round((a - b) / abs(b), 4)


def executive(c: Ctx, f: dict, pl: pd.DataFrame, ranked: list[dict], lost: dict, ds: pd.DataFrame, mk: dict, ops: dict, models: list[dict]) -> dict:
    cur, prev = _period(c, 30), _period(c, 30, 30)
    ly = window(c.sales, "order_date", c.as_of - pd.Timedelta(days=365), 30)
    ly_rev = float(ly.net_sales_egp.sum())
    risk = pl[pl.stockout_risk.isin(["HIGH", "MEDIUM"])]
    lead = risk.supplier_lead_time_days.fillna(7)
    rev_risk = float((((risk.vel * (lead + 14)) - risk.closing_stock).clip(lower=0) * risk.net_unit.fillna(0)).sum())
    by_type: dict = {}
    for r in ranked:
        by_type[r["impact_type"]] = by_type.get(r["impact_type"], 0) + r["estimated_value_egp"]
    recoverable = float(sum(r["estimated_value_egp"] for r in ranked if r["impact_type"] in ("profit_protected", "loss_avoided", "profit_recovered", "capital_released")))
    mkt90 = window(c.mkt.assign(m=c.mkt.start_date + (c.mkt.end_date - c.mkt.start_date) / 2), "m", c.as_of, 90)
    m = f["monthly_pl"].groupby("month")[["net", "gp", "units"]].sum().reset_index()
    m["margin"] = safe_div(m.gp, m.net)
    ret90 = _period(c, 90)
    inv_loc = pl.groupby(["location_id", "location_name"]).apply(lambda d: pd.Series(dict(
        stock_value=d.stock_value.sum(), stockout_high=int((d.stockout_risk == "HIGH").sum()), stockout_medium=int((d.stockout_risk == "MEDIUM").sum()),
        dead_high=int((d.dead_risk == "HIGH").sum()), dead_medium=int((d.dead_risk == "MEDIUM").sum()), items=len(d))), include_groups=False).reset_index()
    inv_loc["healthy"] = inv_loc["items"] - inv_loc.stockout_high - inv_loc.stockout_medium - inv_loc.dead_high - inv_loc.dead_medium
    by_cat: dict = {}
    for r in ranked:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + r["estimated_value_egp"]
    top = [dict(rec_key=r["rec_key"], title=r["title"], category=r["category"], value=r["estimated_value_egp"], urgency=r["urgency"], confidence=r["confidence"]) for r in ranked[:8]]
    kp = lambda k, label, v, unit, ch=None, note=None: dict(key=k, label=label, value=num(v, 4 if unit == "pct" else 0), unit=unit, change=ch, note=note)
    return clean(dict(
        as_of=c.as_of.date().isoformat(), inventory_as_of=c.inv_month.date().isoformat(),
        period_label="Last 30 days vs previous 30 days",
        kpis=[kp("revenue", "Revenue", cur["revenue"], "egp", _chg(cur["revenue"], prev["revenue"]), f"vs same 30 days last year: {(_chg(cur['revenue'], ly_rev) or 0):+.1%}" if ly_rev else None),
              kp("gross_profit", "Gross Profit", cur["gp"], "egp", _chg(cur["gp"], prev["gp"])),
              kp("gross_margin", "Gross Margin", cur["gp"] / cur["revenue"] if cur["revenue"] else 0, "pct", None),
              kp("revenue_at_risk", "Revenue at Risk", rev_risk, "egp", None, "Next-30-day sales at stock-risk locations that stock cannot cover (estimate)"),
              kp("recoverable_profit", "Recoverable Profit", recoverable, "egp", None, "Sum of estimated values of open recommendations (estimates)"),
              kp("dead_stock_value", "Dead Stock Value", float(ds.stock_value_at_risk.sum()) if len(ds) else 0, "egp", None, "Stock at cost unlikely to sell within 90 days"),
              kp("stockout_exposure", "Stockout Exposure", lost["summary"]["lost_revenue_3m"] or 0, "egp", None, "Estimated sales already lost to stockouts in the last 3 months"),
              kp("return_cost", "Return Cost", ret90["refunds"], "egp", None, "Refunds issued in the last 90 days"),
              kp("marketing_efficiency", "Marketing Efficiency (ROAS)", float(mkt90.attributed_revenue_egp.sum() / max(mkt90.spend_egp.sum(), 1)), "x", None, "Attributed revenue per EGP of spend, last 90 days (modelled attribution)"),
              kp("production_efficiency", "Production Efficiency", (ops["kpis"]["efficiency_90d"] or 0) / 100, "pct", None, "Average line efficiency, last 90 days")],
        critical_decisions=int(sum(1 for r in ranked if r["urgency"] == "CRITICAL")),
        trend=records(m.assign(month=m.month.dt.strftime("%Y-%m"))[["month", "net", "gp", "margin", "units"]]),
        inventory_by_location=records(inv_loc), recovery_by_category=[dict(category=k, value=v) for k, v in sorted(by_cat.items(), key=lambda x: -x[1])],
        recovery_by_impact_type=by_type, top_decisions=top))


def merchandising(c: Ctx, pl: pd.DataFrame, actions: pd.DataFrame, strat: pd.DataFrame, sizes: dict) -> dict:
    p = pl.groupby(["product_id", "product_name", "sku"]).agg(units_90d=("v90", lambda x: x.sum() * 90), net_12m=("net_12m", "sum"), gp_12m=("gp_12m", "sum")).reset_index()
    p["margin"] = safe_div(p.gp_12m, p.net_12m)
    med = p.margin.median()
    top = p.sort_values("units_90d", ascending=False).head(10)
    win = p[(p.margin >= p.margin.quantile(0.75))].sort_values("gp_12m", ascending=False).head(10)
    a = actions.merge(pl[["product_id", "location_id", "product_name", "location_name"]], on=["product_id", "location_id"])
    pick = lambda act: records(a[a.recommended_action == act].sort_values("estimated_value_egp", ascending=False).head(10)[["product_id", "product_name", "location_name", "estimated_value_egp", "confidence", "urgency"]])
    sz = sizes["rows"]
    imb = sz[sz.risk != "BALANCED"].groupby(["product_id", "location_id"]).share_shift_pp.apply(lambda x: x.abs().max()).reset_index().sort_values("share_shift_pp", ascending=False).head(10)
    imb = imb.merge(pl[["product_id", "location_id", "product_name", "location_name"]], on=["product_id", "location_id"])
    dead = pl[pl.dead_risk != "LOW"].sort_values("stock_value", ascending=False).head(10)
    return clean(dict(top_sellers=records(top), high_margin_winners=records(win), dead_stock=records(dead[["product_id", "product_name", "location_name", "closing_stock", "doc", "stock_value", "dead_risk"]]),
                      size_imbalance=records(imb), to_scale=pick("SCALE"), to_discount=pick("DISCOUNT"), to_relocate=pick("RELOCATE"),
                      decision_mix=strat.decision.value_counts().to_dict()))

"""7. SUPPLIER TRUE COST ENGINE. Observed cost (facts in the data) is kept separate from Estimated risk cost (assumption-driven)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import make_rec, egp, num


def supplier_engine(c: Ctx, f: dict, cfg) -> dict:
    po = c.po.copy()
    po["spend"] = po.ordered_qty * po.unit_cost_egp
    po["delay"] = (po.actual_receipt_date - po.promised_date).dt.days
    po["late"] = (po.delay > 0).astype(int)
    po["lead_actual"] = (po.actual_receipt_date - po.order_date).dt.days
    po["rej_cost"] = po.rejected_qty * po.unit_cost_egp
    med = po.groupby("material_id").unit_cost_egp.transform("median")
    po["premium"] = ((po.unit_cost_egp - med).clip(lower=0)) * po.ordered_qty            # observed spend above the material's market median
    # exposure of production: average daily gross profit of the products that consume each material (via BOM)
    gp_prod = c.sales.groupby("product_id").agg(gp=("gross_profit_egp", "sum"), u=("quantity", "sum"))
    days = max((c.sales.order_date.max() - c.sales.order_date.min()).days, 1)
    gp_day = (gp_prod.gp / days)
    gpu = (gp_prod.gp / gp_prod.u)
    bom = c.bom.assign(gp_day=c.bom.product_id.map(gp_day), gpu=c.bom.product_id.map(gpu))
    mat_exp = bom.groupby("material_id").agg(daily_profit_exposure=("gp_day", "sum"), avg_req=("required_per_unit", "mean"), gpu=("gpu", "mean"), products=("product_id", "nunique"))
    po = po.merge(mat_exp.reset_index(), on="material_id", how="left")
    k = cfg.delay_impact_pass_through
    po["risk_delay"] = po.delay.clip(lower=0) * po.daily_profit_exposure.fillna(0) * k
    po["risk_reject"] = safe_div(po.rejected_qty, po.avg_req.fillna(1)) * po.gpu.fillna(0) * k

    def roll(d):
        g = d.groupby("supplier_id").agg(orders=("po_id", "count"), spend=("spend", "sum"), on_time_rate=("late", lambda x: 1 - x.mean()),
                                         avg_delay_days=("delay", lambda x: x.clip(lower=0).mean()), avg_lead_days=("lead_actual", "mean"),
                                         rejected_qty=("rejected_qty", "sum"), ordered_qty=("ordered_qty", "sum"), observed_rejection_cost=("rej_cost", "sum"),
                                         observed_price_premium=("premium", "sum"), risk_delay=("risk_delay", "sum"), risk_reject=("risk_reject", "sum")).reset_index()
        g["reject_rate"] = safe_div(g.rejected_qty, g.ordered_qty)
        g["acceptance_rate"] = 1 - g.reject_rate
        g["observed_cost"] = g.observed_rejection_cost + g.observed_price_premium
        g["estimated_risk_cost"] = g.risk_delay + g.risk_reject
        g["true_cost"] = g.observed_cost + g.estimated_risk_cost
        g["true_cost_index"] = safe_div(g.true_cost, g.spend)                  # true cost per EGP purchased
        g["observed_cost_index"] = safe_div(g.observed_cost, g.spend)
        return g
    end = c.as_of
    last12 = window(po, "order_date", end, 365)
    cur = roll(last12 if len(last12) > 50 else po)
    cur["true_cost_score"] = (100 * (1 - cur.true_cost_index.rank(pct=True) + 1 / max(len(cur), 1))).clip(0, 100).round(1)   # 100 = cheapest true cost
    cur["rank"] = cur.true_cost_index.rank(method="min").astype(int)
    cur = cur.merge(c.sup[["supplier_id", "supplier_name", "primary_category", "contracted", "payment_terms_days"]], on="supplier_id", how="left")
    # trend: last 6 months vs previous 6 months
    r6, p6 = window(po, "order_date", end, 180), window(po, "order_date", end, 360, 180)
    t = roll(r6).set_index("supplier_id")[["on_time_rate", "avg_delay_days", "reject_rate"]].join(
        roll(p6).set_index("supplier_id")[["on_time_rate", "avg_delay_days", "reject_rate"]], lsuffix="", rsuffix="_prev").reset_index()
    t["on_time_change_pp"] = (t.on_time_rate - t.on_time_rate_prev) * 100
    cur = cur.merge(t[["supplier_id", "on_time_rate_prev", "on_time_change_pp", "avg_delay_days_prev", "reject_rate_prev"]], on="supplier_id", how="left")
    # affected products (aggregated BOM -> material -> supplier link)
    ms = last12.groupby(["supplier_id", "material_id"]).spend.sum().reset_index()
    ap = ms.merge(c.bom[["material_id", "product_id"]], on="material_id").merge(c.product[["product_id", "product_name"]], on="product_id")
    affected = ap.groupby("supplier_id").product_id.nunique().rename("affected_products").reset_index()
    cur = cur.merge(affected, how="left")
    by_material = last12.groupby(["supplier_id", "material_id"]).agg(spend=("spend", "sum"), on_time=("late", lambda x: 1 - x.mean()), reject=("rejected_qty", "sum"), ordered=("ordered_qty", "sum"),
                                                                    unit_cost=("unit_cost_egp", "mean")).reset_index().merge(c.mat[["material_id", "material_name", "material_category"]], on="material_id")
    by_material["reject_rate"] = safe_div(by_material.reject, by_material.ordered)
    # monthly cost trend
    cost_trend = po.assign(month=po.order_date.dt.to_period("M").dt.to_timestamp()).groupby(["month"]).apply(lambda d: pd.Series(dict(spend=d.spend.sum(), on_time=1 - d.late.mean(), reject_rate=d.rejected_qty.sum() / max(d.ordered_qty.sum(), 1))), include_groups=False).reset_index()
    # association (not causation) between supplier delay and production delay by month
    pm = c.prod.assign(month=c.prod.start_date.dt.to_period("M").dt.to_timestamp()).groupby("month").delay_days.mean()
    sm = po.assign(month=po.order_date.dt.to_period("M").dt.to_timestamp()).groupby("month").delay.mean()
    j = pd.concat([pm, sm], axis=1, keys=["prod_delay", "supplier_delay"]).dropna()
    assoc = None
    if len(j) >= 12:
        from scipy.stats import spearmanr
        rho, p = spearmanr(j.prod_delay, j.supplier_delay)
        assoc = dict(rho=num(rho, 3), p_value=num(p, 3), months=len(j), reading="association only - correlation does not prove the supplier caused the production delay")
    recs = []
    for _, r in cur.iterrows():
        issues = []
        if pd.notna(r.on_time_change_pp) and r.on_time_change_pp <= -8 and r.orders >= 10:
            issues.append(f"On-time delivery fell {abs(r.on_time_change_pp):.0f} pts to {r.on_time_rate:.0%} (last 6 months vs the previous 6)")
        if r.true_cost_index >= cur.true_cost_index.quantile(0.75) and r.spend > cur.spend.median():
            issues.append(f"True cost is {r.true_cost_index:.1%} of spend (observed {r.observed_cost_index:.1%} + estimated risk {safe_div(r.estimated_risk_cost, r.spend):.1%})")
        if issues:
            amount = float(0.5 * r.observed_rejection_cost + 0.5 * r.estimated_risk_cost)   # scenario: halve rejections and delay impact; price premium is reported separately as a negotiation lever
            recs.append(make_rec("supplier_true_cost", "INVESTIGATE_SUPPLIER", f"Investigate supplier: {r.supplier_name}", "Supplier performance is costing more than the purchase price shows", issues + [
                f"Observed cost {egp(r.observed_cost)} (rejected material {egp(r.observed_rejection_cost)} + spend above the market-median price {egp(r.observed_price_premium)}); estimated risk cost {egp(r.estimated_risk_cost)} (assumption-driven)"],
                f"Review {r.supplier_name}: agree delivery and quality targets, or shift volume to a lower true-cost supplier", "loss_avoided", amount, float(r.true_cost), 0.6 if r.orders >= 30 else 0.45,
                "HIGH" if (pd.notna(r.on_time_change_pp) and r.on_time_change_pp <= -15) else "MEDIUM", entity_type="supplier", entity_id=r.supplier_id, department="Procurement",
                evidence=dict(observed=dict(rejection_cost=num(r.observed_rejection_cost), price_premium=num(r.observed_price_premium)), estimated_risk=dict(delay=num(r.risk_delay), rejection=num(r.risk_reject)),
                              assumption=f"{k:.0%} of a late/rejected material day or unit is assumed to reach production", affected_products=num(r.affected_products))))
    return dict(table=cur, by_material=by_material, trend=cost_trend, association=assoc, recs=recs, product_link=ap,
                labels=dict(observed="Observed Cost = rejected material value + spend above the material's median price (facts from Purchase_Orders)",
                            estimated=f"Estimated Risk Cost = delay days / rejected units x exposed daily gross profit x {k:.0%} pass-through ASSUMPTION"))

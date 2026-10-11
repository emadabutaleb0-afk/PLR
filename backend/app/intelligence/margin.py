"""6. MARGIN EROSION ENGINE. Deterministic decomposition (ML is not justified: month-to-month margin change is noise-like).
Compares the last 90 days with the previous 90 days for each product. The profit change is split into exact, additive effects."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import make_rec, egp, num

DRIVERS = ["volume", "discount", "cogs", "price_mix", "returns_refunds", "quality_loss", "rework", "production_rejects", "campaign_spend"]
LABEL = {"discount": "deeper discounts", "cogs": "higher cost of goods", "returns_refunds": "more returns and refunds", "quality_loss": "quality losses",
         "rework": "printing rework", "production_rejects": "production rejects", "campaign_spend": "higher campaign spend", "price_mix": "price / mix", "volume": "volume"}
ACTION = {"discount": "Cap discount depth and review wholesale discount tiers", "cogs": "Review BOM consumption and supplier prices for this product",
          "returns_refunds": "Investigate return reasons and tighten size/fit information", "quality_loss": "Open a corrective-action plan on the main defects",
          "rework": "Fix the printing process (machine/consumables) causing rework", "production_rejects": "Reduce reject rate on the production line",
          "campaign_spend": "Reduce or re-target campaign spend", "price_mix": "Review price list and channel mix"}


def _period(c: Ctx, f: dict, lo_days: int, hi_days: int) -> pd.DataFrame:
    end = c.as_of
    s = window(c.sales, "order_date", end, lo_days, hi_days)
    ret = s.returned.fillna(False).astype(bool); q = s.quality_related_return.fillna(False).astype(bool)
    d = s.assign(ret_gp=np.where(ret & ~q, s.gross_profit_egp, 0), q_ref=np.where(q, s.refund_value_egp.fillna(0), 0),
                 ret_units=np.where(ret, s.quantity, 0), dv=s.list_price_egp * s.quantity - s.net_sales_egp)
    g = d.groupby("product_id").agg(units=("quantity", "sum"), gross=("gross_sales_egp", "sum"), net=("net_sales_egp", "sum"), cogs=("estimated_cogs_egp", "sum"),
                                    gp=("gross_profit_egp", "sum"), ret_gp=("ret_gp", "sum"), q_ref=("q_ref", "sum"), ret_units=("ret_units", "sum"), dv=("dv", "sum")).reset_index()
    q_ = window(c.qual, "inspection_date", end, lo_days, hi_days).groupby("product_id").estimated_loss_egp.sum().rename("q_loss")
    pr = window(c.prt, "print_date", end, lo_days, hi_days).groupby("product_id").agg(rework=("rework_cost_egp", "sum"))
    pe = f["unit_econ"].set_index("product_id").cogs_unit
    po = window(c.prod, "start_date", end, lo_days, hi_days).groupby("product_id").rejected_qty.sum().rename("prod_rej_units").reset_index()
    po["prod_rej_cost"] = po.prod_rej_units * po.product_id.map(pe).fillna(0)
    mk = c.mkt.copy(); mk["mid"] = mk.start_date + (mk.end_date - mk.start_date) / 2
    mk = window(mk, "mid", end, lo_days, hi_days).groupby("product_id").spend_egp.sum().rename("campaign")
    g = g.merge(q_.reset_index(), how="left").merge(pr.reset_index(), how="left").merge(po[["product_id", "prod_rej_cost"]], how="left").merge(mk.reset_index(), how="left").fillna(0)
    num_cols = [c_ for c_ in g.columns if c_ != "product_id"]
    g[num_cols] = g[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
    g["leak_returns"] = g.ret_gp + g.q_ref
    g["contribution"] = g.gp - g.leak_returns - g.q_loss - g.rework - g.prod_rej_cost - g.campaign
    return g.set_index("product_id")


def margin_erosion(c: Ctx, f: dict, cfg) -> dict:
    p1, p0 = _period(c, f, 90, 0), _period(c, f, 180, 90)
    ids = p1.index.intersection(p0.index)
    a, b = p1.loc[ids], p0.loc[ids]
    out = pd.DataFrame(index=ids)
    u1, u0 = a.units, b.units
    out["units"], out["units_prev"] = u1, u0
    out["net"], out["net_prev"] = a.net, b.net
    out["margin"], out["margin_prev"] = safe_div(a.gp, a.net), safe_div(b.gp, b.net)
    out["contribution"], out["contribution_prev"] = a.contribution, b.contribution
    out["contribution_per_unit"], out["contribution_per_unit_prev"] = safe_div(a.contribution, u1), safe_div(b.contribution, u0)
    gpu0 = safe_div(b.gp, u0)
    eff = pd.DataFrame(index=ids)
    eff["volume"] = (u1 - u0) * gpu0
    eff["discount"] = -(safe_div(a.dv, u1) - safe_div(b.dv, u0)) * u1
    eff["cogs"] = -(safe_div(a.cogs, u1) - safe_div(b.cogs, u0)) * u1
    eff["price_mix"] = (a.gp - b.gp) - eff.volume - eff.discount - eff.cogs
    eff["returns_refunds"] = -(a.leak_returns - b.leak_returns)
    eff["quality_loss"] = -(a.q_loss - b.q_loss)
    eff["rework"] = -(a.rework - b.rework)
    eff["production_rejects"] = -(a.prod_rej_cost - b.prod_rej_cost)
    eff["campaign_spend"] = -(a.campaign - b.campaign)
    out["delta_contribution"] = a.contribution - b.contribution
    eff = eff.astype(float).fillna(0.0)
    out["delta_contribution"] = out.delta_contribution.astype(float)
    resid = out.delta_contribution - eff.sum(axis=1)
    eff["price_mix"] = eff.price_mix + resid                       # guarantees the effects add up exactly to the profit change
    # margin health score (0-100), transparent weights
    pct = lambda s, inv=False: (1 - s.rank(pct=True)) * 100 if inv else s.rank(pct=True) * 100
    sales12 = c.sales.groupby("product_id").agg(net=("net_sales_egp", "sum"), gp=("gross_profit_egp", "sum"), dv=("list_price_egp", "sum"), q=("quality_related_return", lambda x: x.fillna(False).astype(bool).mean()),
                                                r=("returned", lambda x: x.fillna(False).astype(bool).mean())).reindex(ids)
    margin_lvl = pct(safe_div(sales12.gp, sales12.net) if False else pd.Series(safe_div(sales12.gp, sales12.net), index=ids))
    trend = pct(pd.Series(out.margin - out.margin_prev, index=ids))
    disc = pct(pd.Series(safe_div(a.dv, a.gross + a.dv), index=ids), inv=True)
    retq = pct(pd.Series(safe_div(a.leak_returns, a.net), index=ids), inv=True)
    qual = pct(pd.Series(safe_div(a.q_loss + a.rework + a.prod_rej_cost, a.net), index=ids), inv=True)
    camp = pct(pd.Series(safe_div(a.campaign, a.net), index=ids), inv=True)
    w = dict(margin_level=0.30, margin_trend=0.20, discount_depth=0.15, returns_leakage=0.15, quality_cost=0.10, campaign_burden=0.10)
    out["margin_health_score"] = (w["margin_level"] * margin_lvl + w["margin_trend"] * trend + w["discount_depth"] * disc + w["returns_leakage"] * retq +
                                  w["quality_cost"] * qual + w["campaign_burden"] * camp).round(1)
    out["health_band"] = np.select([out.margin_health_score >= 65, out.margin_health_score >= 40], ["HEALTHY", "WATCH"], default="UNHEALTHY")
    erosion = (out.units >= out.units_prev * 1.03) & (out.contribution_per_unit <= out.contribution_per_unit_prev * 0.97)
    erosion |= (out.margin - out.margin_prev <= -0.02) & (out.delta_contribution < 0)
    out["selling_more_earning_less"] = erosion
    out = out.join(c.product.set_index("product_id")[["product_name", "sku", "product_family"]])
    recs = []
    for pid, r in out[out.selling_more_earning_less].iterrows():
        e = eff.loc[pid].drop(["volume"])
        neg = e[e < 0].sort_values()
        if neg.empty:
            continue
        top = neg.index[0]; amount = float(-neg.iloc[0])
        why = [f"Units {r.units / max(r.units_prev, 1) - 1:+.0%} but contribution per unit {r.contribution_per_unit / r.contribution_per_unit_prev - 1 if r.contribution_per_unit_prev else 0:+.0%} vs the previous 90 days",
               f"Margin {r.margin_prev:.1%} -> {r.margin:.1%}",
               f"Biggest drag: {LABEL[top]} ({egp(amount)} lower profit); total controllable drag {egp(-neg.sum())}"]
        recs.append(make_rec("margin_erosion", "FIX_MARGIN", f"Margin erosion: {r.product_name}", "Selling more but earning less", why,
                             f"{ACTION[top]} - restoring this driver to last quarter's level recovers about {egp(amount)} per quarter",
                             "profit_recovered", amount, float(-neg.sum()), 0.7, "HIGH" if amount > out.delta_contribution.abs().quantile(0.9) else "MEDIUM",
                             product_id=pid, department="Finance" if top in ("cogs",) else "Merchandising",
                             evidence=dict(drivers={k: num(v) for k, v in eff.loc[pid].items()}, margin_health_score=num(r.margin_health_score, 1), basis="last 90 days vs previous 90 days")))
    return dict(table=out.reset_index(), effects=eff.reset_index(), recs=recs, weights=w)

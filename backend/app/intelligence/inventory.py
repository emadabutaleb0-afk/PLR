"""Inventory-centred engines: Lost Sales, Dead Stock Rescue, Inventory Productivity, Transfers, Markdown, Product Action."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import safe_div, window
from app.optimization.transfer import optimise_transfers
from app.optimization.markdown import optimise_markdown
from app.intelligence.common import make_rec, confidence_from, egp, num

KEYS = ["product_id", "location_id"]


# ------------------------------------------------------------------ 10. LOST SALES
def lost_sales(c: Ctx, f: dict) -> dict:
    inv = c.inv[c.inv.stockout_days_in_month > 0].copy()
    inv["month"] = inv.snapshot_month
    m = f["monthly_pl"][KEYS + ["month", "net", "units", "gp"]].copy()
    inv = inv.merge(m, on=KEYS + ["month"], how="left").merge(f["unit_econ_pl"], on=KEYS, how="left", suffixes=("", "_ue")) \
        .merge(f["unit_econ"], on="product_id", how="left", suffixes=("", "_p"))
    price = (inv.net / inv.units.replace(0, np.nan)).fillna(inv.net_unit).fillna(inv.net_unit_p)
    gpu = (inv.gp / inv.units.replace(0, np.nan)).fillna(inv.gp_unit).fillna(inv.gp_unit_p)
    inv["estimated_lost_units"] = inv.stockout_days_in_month * inv.avg_daily_sales_90d
    inv["estimated_lost_revenue"] = inv.estimated_lost_units * price
    inv["estimated_lost_profit"] = inv.estimated_lost_units * gpu
    cols = KEYS + ["month", "stockout_days_in_month", "avg_daily_sales_90d", "estimated_lost_units",
                   "estimated_lost_revenue", "estimated_lost_profit"]
    rows = inv[cols].fillna(0)
    last3 = rows[rows.month > c.inv_month - pd.DateOffset(months=3)]
    last12 = rows[rows.month > c.inv_month - pd.DateOffset(months=12)]
    by_pl = last12.groupby(KEYS).agg(lost_units_12m=("estimated_lost_units", "sum"), lost_revenue_12m=("estimated_lost_revenue", "sum"),
                                     lost_profit_12m=("estimated_lost_profit", "sum"), stockout_days_12m=("stockout_days_in_month", "sum")).reset_index()
    by_month = rows.groupby("month").agg(lost_units=("estimated_lost_units", "sum"), lost_revenue=("estimated_lost_revenue", "sum")).reset_index()
    return dict(by_pl=by_pl, by_month=by_month, rows=rows,
                summary=dict(lost_revenue_12m=num(last12.estimated_lost_revenue.sum()), lost_units_12m=num(last12.estimated_lost_units.sum()),
                             lost_profit_12m=num(last12.estimated_lost_profit.sum()), lost_revenue_3m=num(last3.estimated_lost_revenue.sum()),
                             label="ESTIMATE: stockout days x trailing 90-day average daily sales x actual selling price. "
                                   "Average daily sales during a stockout month can be depressed, so this is conservative."))


# ------------------------------------------------------------------ 11. INVENTORY PRODUCTIVITY
def productivity(c: Ctx, f: dict, cfg) -> pd.DataFrame:
    pl = f["pl"][KEYS + ["product_name", "sku", "location_name", "doc", "closing_stock", "cogs_unit", "gp_unit", "stock_value"]].copy()
    avg_units = c.inv[c.inv.snapshot_month > c.inv_month - pd.DateOffset(months=3)].groupby(KEYS).closing_stock.mean().rename("avg_units_90d")
    gp90 = window(c.sales, "order_date", c.as_of, 90).groupby(KEYS).gross_profit_egp.sum().rename("gp_90d")
    d = pl.merge(avg_units.reset_index(), how="left").merge(gp90.reset_index(), how="left").fillna({"gp_90d": 0})
    d["avg_inventory_cost"] = d.avg_units_90d * d.cogs_unit
    d["profit_per_inventory_day"] = safe_div(d.gp_90d, d.avg_units_90d * 90)          # EGP gross profit per unit held per day
    d["gmroi"] = safe_div(d.gp_90d * 365 / 90, d.avg_inventory_cost)                   # annualised GP per EGP of inventory
    med = d.gmroi.median()
    d["class"] = np.select(
        [(d.gmroi >= med) & (d.doc <= 90), (d.gmroi < med) & (d.doc > 120), (d.gmroi >= med) & (d.doc > 90), (d.gmroi < med) & (d.doc <= 90)],
        ["FAST_PROFITABLE", "SLOW_CAPITAL_TRAPPING", "SLOW_PROFITABLE", "FAST_LOW_MARGIN"], default="BALANCED")
    return d


# ------------------------------------------------------------------ 2. DEAD STOCK RESCUE (+ transfers + markdown)
def prepare_pl(c: Ctx, f: dict, ml: dict, cfg) -> pd.DataFrame:
    pl = f["pl"].copy()
    pr, fc = ml["predictions"], ml["forecast"]
    pl = pl.merge(pr, on=KEYS, how="left").merge(fc[KEYS + ["forecast_daily", "forecast_90d_units", "ly_next90_units"]], on=KEYS, how="left")
    raw = pl.forecast_daily.where(pl.forecast_daily > 0, pl.avg_daily_sales_90d).fillna(0).clip(lower=0)
    # guard rail: a forecast may ramp seasonally, but not beyond 2x the larger of current pace and last year's same-season pace
    cap = 2.0 * np.maximum(pl.v90, pl.ly_next90_units.fillna(0) / 91.0)
    pl["vel"] = np.minimum(raw, cap.where(cap > 0, raw)).clip(lower=0.4 * pl.v90)
    pl["vel"] = pl.vel.where(pl.vel > 0, pl.v90)
    pl["doc_fc"] = safe_div(pl.closing_stock, pl.vel, np.inf)
    pl["doc_file"] = pl.doc                                   # Days_of_Cover as supplied (current pace)
    pl["doc"] = np.minimum(pl.doc_file, pl.doc_fc)            # effective cover: the more conservative of current pace and expected demand
    reg = {m["name"]: m for m in ml["registry"]}
    stock_ok = bool(reg.get("stockout_risk", {}).get("usable"))
    dead_ok = bool(reg.get("dead_stock_risk", {}).get("usable"))
    if "p_stockout_risk" not in pl:
        pl["p_stockout_risk"] = np.nan
    if "p_dead_stock_risk" not in pl:
        pl["p_dead_stock_risk"] = np.nan
    # monthly variability for confidence
    cv = c.inv.groupby(KEYS).sold_qty.agg(lambda x: x.std() / x.mean() if x.mean() > 0 else np.nan).rename("cv")
    pl = pl.merge(cv.reset_index(), how="left")
    pl["history_months"] = pl.merge(c.inv.groupby(KEYS).size().rename("n").reset_index(), how="left").n.values
    # stockout risk level
    lead = pl.supplier_lead_time_days.fillna(7)
    p = pl.p_stockout_risk
    high = (pl.closing_stock <= 0) | (pl.doc < lead * 0.5) | ((pl.doc < lead) & (p.fillna(0.5) >= 0.3)) | (p >= 0.6)
    med = (pl.closing_stock <= pl.reorder_point_units) | (p >= 0.25) | (pl.doc < lead * 2)
    pl["stockout_risk"] = np.where(high, "HIGH", np.where(med, "MEDIUM", "LOW"))
    # dead-stock risk
    pd_ = pl.p_dead_stock_risk
    rule_hi, rule_md = pl.doc > cfg.dead_cover_days, pl.doc > cfg.dead_cover_days * 0.67
    if dead_ok:
        hi = ((pd_ >= 0.7) & (pl.doc > 90)) | (pl.doc > cfg.dead_cover_days * 1.5)
        md = ((pd_ >= 0.4) & (pl.doc > 60)) | rule_hi
    else:
        hi, md = rule_hi, rule_md
    pl["dead_risk"] = np.where(hi, "HIGH", np.where(md, "MEDIUM", "LOW"))
    pl.attrs.update(stockout_model_ok=stock_ok, dead_model_ok=dead_ok)
    return pl


def dead_stock(pl: pd.DataFrame, c: Ctx, f: dict, cfg, transfers: pd.DataFrame) -> pd.DataFrame:
    d = pl[pl.dead_risk != "LOW"].copy()
    ref_days = 90
    d["excess_units"] = (d.closing_stock - d.vel * ref_days).clip(lower=0)
    d["stock_value_at_risk"] = d.excess_units * d.cogs_unit.fillna(0)
    p_dead = d.p_dead_stock_risk.fillna(pd.Series(np.where(d.dead_risk == "HIGH", 0.8, 0.45), index=d.index))
    d["p_dead"] = p_dead
    d["expected_loss"] = d.stock_value_at_risk * p_dead
    mkt = f["mkt_prod"].set_index("product_id")
    med_roas = mkt.roas_all.median()
    outs = transfers.groupby(["product_id", "from_location"]).units.sum() if len(transfers) else pd.Series(dtype=float)
    res = []
    for _, r in d.iterrows():
        t_out = float(outs.get((r.product_id, r.location_id), 0))
        md = optimise_markdown(r.closing_stock, r.vel, r.net_unit, r.cogs_unit, r.p_dead, cfg)
        spend90 = float(mkt.spend_90d.get(r.product_id, 0)); roas = float(mkt.roas_all.get(r.product_id, 0))
        yoy = r.yoy if pd.notna(r.yoy) else 1.0
        opts, primary = [], None
        if t_out >= 10:
            opts.append("TRANSFER")
        if md["feasible"] and md["uplift"] > 0 and md["discount"] > 0:
            opts.append("DISCOUNT")
        if roas >= med_roas and spend90 <= mkt.spend_90d.median() and r.channel != "Wholesale":
            opts.append("MARKETING_SUPPORT")
        if r.received_qty > 0 and r.doc > cfg.dead_cover_days * 0.67:
            opts.append("STOP_REPLENISHMENT")
        if r.doc > cfg.dead_cover_days * 1.5 and yoy < 0.8 and r.dead_risk == "HIGH":
            opts.append("PHASE_OUT")
        primary = opts[0] if opts else ("STOP_REPLENISHMENT" if r.dead_risk == "HIGH" else None)
        # recoverable value: expected loss avoided by the primary action
        rec_val = 0.0
        if primary == "TRANSFER":
            rec_val = min(t_out, r.excess_units) * r.cogs_unit * r.p_dead
        elif primary == "DISCOUNT":
            rec_val = max(md["uplift"], 0)
        elif primary == "STOP_REPLENISHMENT":
            rec_val = min(r.received_qty * 3, r.excess_units) * r.cogs_unit * r.p_dead
        elif primary == "MARKETING_SUPPORT":
            rec_val = 0.15 * r.excess_units * r.cogs_unit * r.p_dead  # conservative: 15% of the excess might be pulled forward
        elif primary == "PHASE_OUT":
            rec_val = 0.5 * r.expected_loss
        res.append(dict(options=opts, primary_action=primary, transfer_out_units=t_out, md_discount=md["discount"],
                        md_feasible=md["feasible"], md_max_discount=md["max_feasible"], md_units_cleared=md.get("units_cleared"),
                        md_units_cleared_base=md.get("units_cleared_base"), md_uplift=md["uplift"], md_cash=md.get("cash_recovered"),
                        recoverable_value=rec_val, spend_90d=spend90, roas_all=roas))
    out = pd.concat([d.reset_index(drop=True), pd.DataFrame(res)], axis=1)
    return out


# ------------------------------------------------------------------ 12. PRODUCT ACTION (integrator)
def product_actions(pl: pd.DataFrame, dead: pd.DataFrame, transfers: pd.DataFrame, f: dict, c: Ctx, cfg) -> tuple[pd.DataFrame, list[dict]]:
    dead_i = dead.set_index(KEYS) if len(dead) else pd.DataFrame()
    qp = f["qual_prod"].set_index("product_id"); pp = f["prod_prod"].set_index("product_id")
    q_hi = qp.q_reject_rate.quantile(0.85) if len(qp) else 1
    med_margin, med_rr = pl.margin_12m.median(), pl.return_rate.median()
    recs, rows = [], []
    tr_in = transfers.groupby(["product_id", "to_location"]).units.sum() if len(transfers) else pd.Series(dtype=float)
    tr_out = transfers.groupby(["product_id", "from_location"]).units.sum() if len(transfers) else pd.Series(dtype=float)
    lname = c.loc.set_index("location_id").location_name.to_dict()
    for _, r in pl.iterrows():
        k = (r.product_id, r.location_id)
        lead = r.supplier_lead_time_days if pd.notna(r.supplier_lead_time_days) else 7
        t_in, t_out = float(tr_in.get(k, 0)), float(tr_out.get(k, 0))
        d = dead_i.loc[k] if len(dead_i) and k in dead_i.index else None
        qrate = float(qp.q_reject_rate.get(r.product_id, 0)) if len(qp) else 0
        qloss = float(qp.q_loss.get(r.product_id, 0)) if len(qp) else 0
        action, why, value, loss, impact, urg, sig, agree = "MAINTAIN", [], 0.0, 0.0, "none", "LOW", 0.3, None
        extra = {}
        yoy = r.yoy if pd.notna(r.yoy) else None
        shortfall = max(0.0, r.vel * (lead + 14) - r.closing_stock)
        profit_protect = shortfall * (r.gp_unit if pd.notna(r.gp_unit) else 0)
        rev_protect = shortfall * (r.net_unit if pd.notna(r.net_unit) else 0)
        stock_issue = r.stockout_risk in ("HIGH", "MEDIUM") and shortfall > 0
        if stock_issue and t_in >= 10:
            action = "RELOCATE"
            frm = transfers[(transfers.product_id == r.product_id) & (transfers.to_location == r.location_id)]
            src = frm.sort_values("units", ascending=False).iloc[0]
            why = [f"{lname.get(r.location_id)} has {r.doc:.1f} days of cover (supplier lead time {lead:.0f} days)",
                   f"{lname.get(src.from_location)} holds {src.from_cover_days:.0f} days of cover and can spare stock",
                   f"Demand here is {src.to_velocity / max(src.from_velocity, 1e-9):.1f}x faster than at the source"]
            value, impact = min(t_in, shortfall) * (r.gp_unit or 0), "profit_protected"
            extra = dict(transfer=dict(units=int(t_in), source=src.from_location, revenue_protected=min(t_in, shortfall) * (r.net_unit or 0)))
            urg = "CRITICAL" if r.stockout_risk == "HIGH" and r.doc < lead else "HIGH"
            sig = float(np.clip((lead - r.doc) / max(lead, 1), 0, 1)); loss = profit_protect
        elif stock_issue:
            action = "REPLENISH"
            qty = math.ceil(max(0, r.vel * (lead + cfg.target_cover_days) + (r.safety_stock_units or 0) - r.closing_stock))
            why = [f"Only {r.doc:.1f} days of cover against a {lead:.0f}-day supplier lead time",
                   f"Expected demand about {r.vel:.1f} units/day; stock is {int(r.closing_stock)} units (reorder point {int(r.reorder_point_units)})"]
            if pd.notna(r.p_stockout_risk) and r.p_stockout_risk >= 0.3 and pl.attrs.get("stockout_model_ok"):
                why.append("Risk model also rates this combination as likely to stock out next month")
                agree = r.p_stockout_risk >= 0.3
            if r.stockout_days_3m and r.stockout_days_3m > 0:
                why.append(f"Already stocked out for {int(r.stockout_days_3m)} days in the last 3 months")
            value, impact, loss = profit_protect, "profit_protected", profit_protect
            urg = "CRITICAL" if (r.closing_stock <= 0 or r.doc < lead / 2) and r.stockout_risk == "HIGH" else ("HIGH" if r.stockout_risk == "HIGH" else "MEDIUM")
            sig = float(np.clip((lead - r.doc) / max(lead, 1), 0, 1))
            extra = dict(reorder_qty=qty, revenue_protected=rev_protect)
        elif qrate >= q_hi and qloss > 0 and r.return_rate > med_rr:
            action = "FIX"
            why = [f"Quality reject rate {qrate:.1%} is in the worst 15% of products",
                   f"Customer return rate here is {r.return_rate:.1%} (portfolio median {med_rr:.1%})",
                   f"Estimated quality loss in the last 180 days: {egp(qloss)}"]
            value, impact, loss, urg, sig = qloss * 0.5, "loss_avoided", qloss, "HIGH", 0.6
        elif d is not None and d.primary_action:
            pa = d.primary_action
            if pa == "TRANSFER":
                action = "RELOCATE"
            else:
                action = pa if pa in ("DISCOUNT", "STOP_REPLENISHMENT", "PHASE_OUT") else ("DISCOUNT" if "DISCOUNT" in d.options else "STOP_REPLENISHMENT")
            if pa == "MARKETING_SUPPORT":
                action = "DISCOUNT" if "DISCOUNT" in d.options else "STOP_REPLENISHMENT"
            why = [f"{r.doc:.0f} days of cover at expected demand; sells only ~{d.md_units_cleared_base or 0:.0f} of {int(r.closing_stock)} units in 90 days",
                   f"About {int(d.excess_units)} units ({egp(d.stock_value_at_risk)} at cost) are unlikely to sell"]
            if pl.attrs.get("dead_model_ok"):
                why.append(f"Dead-stock risk model rates this {d.p_dead:.0%} likely to remain unsold")
                agree = d.p_dead >= 0.5
            if action == "DISCOUNT":
                why.append(f"A {d.md_discount:.0%} discount keeps margin above the {cfg.margin_floor_pct:.0%} floor (max feasible {d.md_max_discount:.0%})")
            if action == "RELOCATE":
                why.append(f"{int(d.transfer_out_units)} units can move to a location with a shortage")
            if action == "STOP_REPLENISHMENT":
                why.append("Stock is still being received while cover is already very high")
            value, impact, loss = d.recoverable_value, ("capital_released" if action != "RELOCATE" else "loss_avoided"), d.expected_loss
            urg = "HIGH" if d.dead_risk == "HIGH" and d.stock_value_at_risk > pl.stock_value.quantile(0.75) else ("MEDIUM" if d.dead_risk == "HIGH" else "LOW")
            sig = float(np.clip((r.doc - cfg.dead_cover_days * 0.67) / cfg.dead_cover_days, 0, 1))
            extra = dict(markdown=dict(discount=d.md_discount, units_cleared=d.md_units_cleared, uplift=d.md_uplift),
                         excess_units=d.excess_units, stock_value_at_risk=d.stock_value_at_risk, p_dead=d.p_dead)
        elif (yoy is not None and yoy >= 1.15) and r.margin_12m >= med_margin and r.doc >= lead and r.doc <= 90 and r.return_rate <= med_rr * 1.2:
            action = "SCALE"
            why = [f"Sales over the last 90 days are {yoy:.2f}x the same period last year",
                   f"Margin {r.margin_12m:.1%} is above the portfolio median ({med_margin:.1%})",
                   f"Healthy cover ({r.doc:.0f} days) and a normal return rate ({r.return_rate:.1%})"]
            incr = r.v90 * 0.1 * 90 * (r.gp_unit or 0)
            value, impact, urg, sig = incr, "profit_generated", "MEDIUM", float(np.clip((yoy - 1.0) / 0.5, 0, 1))
        else:
            why = ["Cover, sales trend, margin and quality are all within normal ranges"]
        conf = confidence_from(sig, agree, int(r.history_months or 0), r.cv)
        rows.append(dict(product_id=r.product_id, location_id=r.location_id, recommended_action=action, confidence=conf,
                         top_reasons=why[:3], expected_business_impact=impact, estimated_value_egp=float(value),
                         estimated_loss_egp=float(loss), urgency=urg, stockout_risk=r.stockout_risk, dead_risk=r.dead_risk,
                         **{k: v for k, v in extra.items() if k in ("reorder_qty",)}))
        if action != "MAINTAIN" and value > 0:
            nm = f"{r.product_name} @ {lname.get(r.location_id)}"
            title = {"RELOCATE": f"Transfer stock: {nm}", "REPLENISH": f"Replenish: {nm}", "DISCOUNT": f"Discount to clear: {nm}",
                     "STOP_REPLENISHMENT": f"Stop replenishing: {nm}", "PHASE_OUT": f"Phase out: {nm}", "FIX": f"Fix quality: {nm}",
                     "SCALE": f"Scale up: {nm}"}[action]
            if action == "RELOCATE" and extra.get("transfer"):
                t = extra["transfer"]
                act = f"Transfer {int(t['units'])} units of {r.product_name} from {lname.get(t['source'])} to {lname.get(r.location_id)}"
            elif action == "RELOCATE":
                act = f"Move {int(d.transfer_out_units)} surplus units of {r.product_name} out of {lname.get(r.location_id)} to locations short of stock"
            elif action == "REPLENISH":
                act = f"Order about {extra['reorder_qty']:,} units of {r.product_name} for {lname.get(r.location_id)}"
            elif action == "DISCOUNT":
                act = f"Run a {d.md_discount:.0%} additional discount on {r.product_name} at {lname.get(r.location_id)} (margin floor protected)"
            elif action == "STOP_REPLENISHMENT":
                act = f"Stop incoming replenishment of {r.product_name} for {lname.get(r.location_id)} until cover falls below {cfg.dead_cover_days * 0.5:.0f} days"
            elif action == "PHASE_OUT":
                act = f"Plan the phase-out of {r.product_name}: no re-orders, clear existing stock"
            elif action == "FIX":
                act = f"Open a corrective-action review on {r.product_name} (quality rejects and returns)"
            else:
                act = f"Increase supply and visibility for {r.product_name} at {lname.get(r.location_id)}"
            problem = {"RELOCATE": "Stock is in the wrong place", "REPLENISH": "Likely to run out of stock", "DISCOUNT": "Stock is unlikely to sell at current pace",
                       "STOP_REPLENISHMENT": "Over-supplied while demand is slow", "PHASE_OUT": "Slow, declining product with trapped capital",
                       "FIX": "Quality problems are driving rejects and returns", "SCALE": "Winner with room to grow"}[action]
            recs.append(make_rec("product_action", action, title, problem, why, act, impact, value, loss, conf, urg,
                                 product_id=r.product_id, location_id=r.location_id,
                                 evidence=dict(days_of_cover=num(r.doc, 1), lead_time_days=num(lead), stock=int(r.closing_stock), velocity=num(r.vel, 2),
                                               forecast_90d=num(r.forecast_90d_units), net_unit=num(r.net_unit, 1), gp_unit=num(r.gp_unit, 1),
                                               stockout_risk=r.stockout_risk, dead_risk=r.dead_risk, **extra)))
    return pd.DataFrame(rows), recs

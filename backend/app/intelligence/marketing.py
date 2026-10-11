"""5. CAMPAIGN-INVENTORY COLLISION DETECTOR + marketing performance."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import make_rec, egp, num

SEV_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def performance(c: Ctx) -> dict:
    m = c.mkt.copy()
    m["ctr"] = safe_div(m.clicks, m.impressions); m["cvr"] = safe_div(m.orders_attributed, m.clicks)
    def roll(keys):
        g = m.groupby(keys).agg(campaigns=("campaign_id", "count"), spend=("spend_egp", "sum"), revenue=("attributed_revenue_egp", "sum"),
                                impressions=("impressions", "sum"), clicks=("clicks", "sum"), orders=("orders_attributed", "sum")).reset_index()
        g["roas"] = safe_div(g.revenue, g.spend); g["ctr"] = safe_div(g.clicks, g.impressions); g["cvr"] = safe_div(g.orders, g.clicks)
        g["cac_proxy"] = safe_div(g.spend, g.orders)
        return g
    prod = roll(["product_id"]).merge(c.product[["product_id", "product_name", "product_family"]], on="product_id")
    # spend share vs gross-profit share (over/under-support)
    gp = c.sales.groupby("product_id").gross_profit_egp.sum().rename("gp").reset_index()
    prod = prod.merge(gp, on="product_id", how="left")
    prod["spend_share"] = prod.spend / prod.spend.sum(); prod["gp_share"] = prod.gp / prod.gp.sum()
    prod["support_ratio"] = safe_div(prod.spend_share, prod.gp_share)
    prod["profit_roas"] = safe_div(prod.revenue * safe_div(prod.gp, c.sales.groupby("product_id").net_sales_egp.sum().reindex(prod.product_id).values), prod.spend)
    prod["support"] = np.select([prod.support_ratio > 1.6, prod.support_ratio < 0.6], ["TOO_MUCH_SPEND", "TOO_LITTLE_SUPPORT"], default="BALANCED")
    mm = m.assign(month=m.start_date.dt.to_period("M").dt.to_timestamp()).groupby("month").agg(spend=("spend_egp", "sum"), revenue=("attributed_revenue_egp", "sum")).reset_index()
    mm["roas"] = safe_div(mm.revenue, mm.spend)
    return dict(by_platform=roll(["platform"]), by_product=prod, by_month=mm, summary=dict(
        spend=num(m.spend_egp.sum()), revenue=num(m.attributed_revenue_egp.sum()), roas=num(m.attributed_revenue_egp.sum() / max(m.spend_egp.sum(), 1), 2),
        label="Attributed revenue comes from the campaign file (modelled attribution); it is not reconciled to Sales_Transactions."))


def collisions(c: Ctx, f: dict, pl: pd.DataFrame, cfg) -> tuple[pd.DataFrame, list[dict]]:
    end = c.as_of
    live = c.mkt[(c.mkt.end_date >= end - pd.Timedelta(days=21))].copy()
    qp, pp = f["qual_prod"].set_index("product_id"), f["prod_prod"].set_index("product_id")
    consumer = pl[pl.channel.isin(["Retail", "Online"])].groupby("product_id").agg(
        stock=("closing_stock", "sum"), vel=("vel", "sum"), lead=("supplier_lead_time_days", "max"), gp_unit=("gp_unit", "mean"), net_unit=("net_unit", "mean"),
        return_rate=("return_rate", "mean"), q_ret=("quality_return_rate", "mean"), dead=("dead_risk", lambda x: "HIGH" if (x == "HIGH").any() else ("MEDIUM" if (x == "MEDIUM").any() else "LOW")),
        stock_value=("stock_value", "sum"))
    consumer["cover"] = safe_div(consumer.stock, consumer.vel, np.inf)
    q85 = qp.q_reject_rate.quantile(0.85); d80 = pp.pr_delayed_share.quantile(0.8); r85 = pp.pr_reject_rate.quantile(0.85)
    qr85 = consumer.q_ret.quantile(0.85)
    mkt90 = f["mkt_prod"].set_index("product_id").spend_90d
    rows, recs = [], []
    nm = c.product.set_index("product_id").product_name
    for _, k in live.iterrows():
        pid = k.product_id
        if pid not in consumer.index:
            continue
        p = consumer.loc[pid]; days = max((k.end_date - k.start_date).days + 1, 1)
        base = dict(campaign_id=k.campaign_id, campaign_name=k.campaign_name, product_id=pid, platform=k.platform, spend=float(k.spend_egp),
                    revenue=float(k.attributed_revenue_egp), start=k.start_date.date().isoformat(), end=k.end_date.date().isoformat(),
                    consumer_cover_days=num(p.cover, 1))
        found = []
        lead = float(p.lead if pd.notna(p.lead) else 7)
        if p.cover < lead + 14:
            frac = float(np.clip(1 - p.cover / days, 0, 1)) if days > p.cover else 0.0
            wasted = k.spend_egp * max(frac, 0.15 if p.cover < lead else 0.0)
            found.append(("LOW_STOCK_PUSH", "CRITICAL" if p.cover < lead / 2 else "HIGH", wasted,
                          f"Campaign is pushing demand into stock that covers only {p.cover:.0f} days (supplier lead time {lead:.0f} days)",
                          "Pause or cap the campaign until stock is replenished or transferred in"))
        if pid in pp.index and (pp.pr_delayed_share.get(pid, 0) >= d80 or pp.pr_reject_rate.get(pid, 0) >= r85) and p.cover < 60:
            found.append(("PRODUCTION_ISSUE", "HIGH", k.spend_egp * 0.25,
                          f"Production for this product is delayed in {pp.pr_delayed_share[pid]:.0%} of recent orders with a {pp.pr_reject_rate[pid]:.1%} reject rate, and cover is only {p.cover:.0f} days",
                          "Hold paid support until production recovers"))
        if (pid in qp.index and qp.q_reject_rate.get(pid, 0) >= q85) or p.q_ret >= qr85:
            exposure = k.attributed_revenue_egp * float(p.q_ret)
            found.append(("POOR_QUALITY", "MEDIUM", exposure,
                          f"Product has a {qp.q_reject_rate.get(pid, 0):.1%} QC reject rate and {p.q_ret:.1%} quality-related returns",
                          "Shift budget to a healthier product until the quality issue is fixed"))
        for typ, sev, impact, why, act in found:
            rows.append(dict(**base, type=typ, severity=sev, estimated_impact_egp=float(impact), why=why, recommended_marketing_action=act))
            recs.append(make_rec("campaign_collision", typ, f"{typ.replace('_', ' ').title()}: {k.campaign_name[:60]}", "Marketing spend and inventory/quality are in conflict",
                                 [why, f"Campaign {k.campaign_id}: spend {egp(k.spend_egp)} on {k.platform}, runs {k.start_date.date()} to {k.end_date.date()}"], act,
                                 "loss_avoided", impact, impact, 0.6 if typ == "LOW_STOCK_PUSH" else 0.5, sev, product_id=pid,
                                 entity_type="campaign", entity_id=k.campaign_id, department="Marketing",
                                 evidence=dict(consumer_cover_days=num(p.cover, 1), spend=float(k.spend_egp), platform=k.platform, basis="spend x share of campaign period beyond stock coverage (estimate)")))
    # overstock products that get no marketing support
    for pid, p in consumer.iterrows():
        if p.dead in ("HIGH", "MEDIUM") and float(mkt90.get(pid, 0)) <= mkt90.median() * 0.5 and p.stock_value > consumer.stock_value.median():
            impact = 0.15 * p.stock_value
            rows.append(dict(campaign_id=None, campaign_name=None, product_id=pid, platform=None, spend=float(mkt90.get(pid, 0)), revenue=0, start=None, end=None,
                             consumer_cover_days=num(p.cover, 1), type="OVERSTOCK_UNDERSUPPORTED", severity="MEDIUM", estimated_impact_egp=float(impact),
                             why=f"{p.cover:.0f} days of cover but only {egp(mkt90.get(pid, 0))} of marketing in the last 90 days",
                             recommended_marketing_action="Add targeted campaign support"))
            recs.append(make_rec("campaign_collision", "OVERSTOCK_UNDERSUPPORTED", f"Support overstocked product: {nm.get(pid)}", "Excess stock with little marketing",
                                 [f"{p.cover:.0f} days of consumer-channel cover", f"Marketing spend last 90 days: {egp(mkt90.get(pid, 0))} (portfolio median {egp(mkt90.median())})"],
                                 f"Run a targeted campaign for {nm.get(pid)} to pull forward demand", "capital_released", impact, p.stock_value * 0.5, 0.45, "MEDIUM",
                                 product_id=pid, department="Marketing", evidence=dict(basis="assumes 15% of stock value could be pulled forward (conservative scenario)")))
    df = pd.DataFrame(rows)
    if len(df):
        df["rank"] = df.severity.map(SEV_ORDER)
        df = df.sort_values(["rank", "estimated_impact_egp"], ascending=False).drop(columns="rank")
    return df, recs

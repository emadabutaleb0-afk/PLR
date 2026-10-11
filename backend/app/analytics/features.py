"""Feature tables shared by every engine. Everything is derived from the loaded company tables."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx


def safe_div(a, b, default=0.0):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    out = np.full(np.broadcast(a, b).shape, default, dtype=float)
    np.divide(a, b, out=out, where=(b != 0) & ~np.isnan(b))
    return out


def window(df: pd.DataFrame, col: str, end: pd.Timestamp, days: int, start_days: int = 0) -> pd.DataFrame:
    lo, hi = end - pd.Timedelta(days=days), end - pd.Timedelta(days=start_days)
    return df[(df[col] > lo) & (df[col] <= hi)]


def unit_economics(c: Ctx) -> pd.DataFrame:
    """Net price, COGS and GP per unit by product (and by product x location) over the last 180 days, falling back to all-time."""
    s = c.sales
    def agg(d, keys):
        g = d.groupby(keys).agg(units=("quantity", "sum"), net=("net_sales_egp", "sum"), cogs=("estimated_cogs_egp", "sum"),
                                gp=("gross_profit_egp", "sum")).reset_index()
        g["net_unit"] = safe_div(g.net, g.units); g["cogs_unit"] = safe_div(g.cogs, g.units); g["gp_unit"] = safe_div(g.gp, g.units)
        return g
    rec = window(s, "order_date", c.as_of, 180)
    p_all, p_rec = agg(s, ["product_id"]), agg(rec, ["product_id"])
    pe = p_all.set_index("product_id")[["net_unit", "cogs_unit", "gp_unit"]].copy()
    pe.update(p_rec.set_index("product_id")[["net_unit", "cogs_unit", "gp_unit"]])
    pl_rec = agg(rec, ["product_id", "location_id"]).set_index(["product_id", "location_id"])[["net_unit", "cogs_unit", "gp_unit"]]
    return pe.reset_index(), pl_rec.reset_index()


def monthly_pl(c: Ctx) -> pd.DataFrame:
    s = c.sales
    r = s["returned"].fillna(False).astype(bool)
    q = s["quality_related_return"].fillna(False).astype(bool)
    d = s.assign(ret_units=np.where(r, s.quantity, 0), q_units=np.where(q, s.quantity, 0),
                 refund=s.refund_value_egp.fillna(0),
                 q_refund=np.where(q, s.refund_value_egp.fillna(0), 0),
                 ret_gp=np.where(r & ~q, s.gross_profit_egp, 0),  # restocked return: lose the line's gross profit
                 disc_val=s.list_price_egp * s.quantity - s.net_sales_egp)
    g = d.groupby(["product_id", "location_id", "month"]).agg(
        units=("quantity", "sum"), gross=("gross_sales_egp", "sum"), net=("net_sales_egp", "sum"),
        cogs=("estimated_cogs_egp", "sum"), gp=("gross_profit_egp", "sum"), ret_units=("ret_units", "sum"),
        q_units=("q_units", "sum"), refund=("refund", "sum"), q_refund=("q_refund", "sum"), ret_gp=("ret_gp", "sum"),
        disc_val=("disc_val", "sum"), invoices=("invoice_id", "nunique")).reset_index()
    g["profit_after_returns"] = g.gp - g.ret_gp - g.q_refund
    return g


def build_features(c: Ctx, cfg) -> dict:
    out: dict = {}
    pe, pl_ue = unit_economics(c)
    out["unit_econ"], out["unit_econ_pl"] = pe, pl_ue
    m = monthly_pl(c)
    out["monthly_pl"] = m
    end = c.as_of

    # ---- product x location base table from the latest inventory snapshot
    last = c.inv[c.inv.snapshot_month == c.inv_month].copy()
    base = last[["product_id", "location_id", "closing_stock", "avg_daily_sales_90d", "safety_stock_units",
                 "reorder_point_units", "supplier_lead_time_days", "days_of_cover", "stockout_days_in_month",
                 "received_qty", "sold_qty", "damaged_qty"]].rename(columns={"stockout_days_in_month": "stockout_days_last"})
    so3 = c.inv[c.inv.snapshot_month > c.inv_month - pd.DateOffset(months=3)].groupby(["product_id", "location_id"]) \
        .stockout_days_in_month.sum().rename("stockout_days_3m").reset_index()
    base = base.merge(so3, how="left")
    s = c.sales
    for tag, (a, b) in {"v90": (90, 0), "v90_prev": (180, 90), "v30": (30, 0)}.items():
        w = window(s, "order_date", end, a, b).groupby(["product_id", "location_id"]).quantity.sum() / (a - b)
        base = base.merge(w.rename(tag).reset_index(), how="left")
    ly = window(s, "order_date", end - pd.Timedelta(days=365), 90).groupby(["product_id", "location_id"]).quantity.sum() / 90
    base = base.merge(ly.rename("v90_ly").reset_index(), how="left")
    base[["v90", "v90_prev", "v30", "v90_ly"]] = base[["v90", "v90_prev", "v30", "v90_ly"]].fillna(0)
    base["trend"] = safe_div(base.v90, base.v90_prev, 1.0)          # momentum (affected by season)
    base["yoy"] = safe_div(base.v90, base.v90_ly, np.nan)           # season-adjusted growth vs same 90 days last year
    # 12-month performance
    y = window(m.assign(d=m.month + pd.offsets.MonthEnd(0)), "d", end, 365)
    perf = y.groupby(["product_id", "location_id"]).agg(units_12m=("units", "sum"), net_12m=("net", "sum"), gp_12m=("gp", "sum"),
                                                        cogs_12m=("cogs", "sum"), ret_units_12m=("ret_units", "sum"),
                                                        q_units_12m=("q_units", "sum"), refund_12m=("refund", "sum"),
                                                        profit_after_returns_12m=("profit_after_returns", "sum"),
                                                        disc_val_12m=("disc_val", "sum"), gross_12m=("gross", "sum")).reset_index()
    perf["margin_12m"] = safe_div(perf.gp_12m, perf.net_12m)
    perf["return_rate"] = safe_div(perf.ret_units_12m, perf.units_12m)
    perf["quality_return_rate"] = safe_div(perf.q_units_12m, perf.units_12m)
    perf["discount_depth"] = safe_div(perf.disc_val_12m, perf.gross_12m + perf.disc_val_12m)
    base = base.merge(perf, how="left")
    base = base.merge(pl_ue.rename(columns={"net_unit": "net_unit_pl", "cogs_unit": "cogs_unit_pl", "gp_unit": "gp_unit_pl"})
                      [["product_id", "location_id", "net_unit_pl", "cogs_unit_pl", "gp_unit_pl"]], how="left")
    base = base.merge(pe, on="product_id", how="left")
    for k in ("net_unit", "cogs_unit", "gp_unit"):
        base[k] = base[k + "_pl"].fillna(base[k])
    base = base.merge(c.product[["product_id", "sku", "product_name", "product_family", "catalog_season", "public_retail_price_egp",
                                 "sizes", "gender", "audience"]], on="product_id", how="left")
    base = base.merge(c.loc[["location_id", "location_name", "channel"]], on="location_id", how="left")
    base["stock_value"] = base.closing_stock * base.cogs_unit.fillna(0)
    base["doc"] = base.days_of_cover
    out["pl"] = base

    # ---- marketing per product (last 90d)
    mk = c.mkt
    mk90 = mk[mk.end_date > end - pd.Timedelta(days=90)]
    g = mk90.groupby("product_id").agg(spend_90d=("spend_egp", "sum"), rev_90d=("attributed_revenue_egp", "sum")).reset_index()
    g["roas_90d"] = safe_div(g.rev_90d, g.spend_90d)
    gall = mk.groupby("product_id").agg(spend_all=("spend_egp", "sum"), rev_all=("attributed_revenue_egp", "sum")).reset_index()
    gall["roas_all"] = safe_div(gall.rev_all, gall.spend_all)
    out["mkt_prod"] = gall.merge(g, how="left").fillna({"spend_90d": 0, "rev_90d": 0, "roas_90d": 0})

    # ---- quality per product (last 180d) and production
    q = window(c.qual, "inspection_date", end, 180)
    qg = q.groupby("product_id").agg(inspected=("inspected_qty", "sum"), q_rejected=("rejected_qty", "sum"), q_loss=("estimated_loss_egp", "sum")).reset_index()
    qg["q_reject_rate"] = safe_div(qg.q_rejected, qg.inspected)
    out["qual_prod"] = qg
    pr = window(c.prod, "start_date", end, 180)
    pg = pr.groupby("product_id").agg(pr_orders=("production_order_id", "count"), pr_planned=("planned_qty", "sum"),
                                      pr_produced=("produced_qty", "sum"), pr_rejected=("rejected_qty", "sum"),
                                      pr_eff=("efficiency_pct", "mean"), pr_delay=("delay_days", "mean"),
                                      pr_delayed_share=("delay_days", lambda x: float((x > 0).mean()))).reset_index()
    pg["pr_reject_rate"] = safe_div(pg.pr_rejected, pg.pr_produced)
    out["prod_prod"] = pg
    return out

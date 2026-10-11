"""3. SIZE CURVE OPTIMISER. Learns actual size demand from sales and returns.
Limitation (stated in every output): Inventory_History has no size column, so the CURRENT stock-by-size distribution is
unavailable. The historical sales mix is shown as the proxy for the implicit stocking curve, and size risks are
'mix-shift risks', not stock-based stockout/overstock probabilities."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import make_rec, egp, num

KEYS = ["product_id", "location_id"]
NOTE = ("Current stock by size is unavailable (Inventory_History has no Size column). 'baseline' = the sales mix of the "
        "prior 12 months, used as a proxy for the implicit stocking curve.")


def _alloc(total: int, shares: pd.Series) -> pd.Series:
    raw = shares / shares.sum() * total if shares.sum() > 0 else shares * 0
    base = np.floor(raw)
    rem = int(total - base.sum())
    order = (raw - base).sort_values(ascending=False).index[:max(rem, 0)]
    base[order] += 1
    return base.astype(int)


def size_curve(c: Ctx, pl: pd.DataFrame, cfg) -> dict:
    s = c.sales.copy()
    s["ret_units"] = np.where(s.returned.fillna(False).astype(bool), s.quantity, 0)
    s["size_ret"] = np.where(s.return_reason.fillna("").eq("Size / fit"), s.quantity, 0)
    recent = window(s, "order_date", c.as_of, 180)
    base = window(s, "order_date", c.as_of - pd.Timedelta(days=180), 365)
    def agg(d):
        return d.groupby(KEYS + ["size"]).agg(units=("quantity", "sum"), ret=("ret_units", "sum"), size_ret=("size_ret", "sum")).reset_index()
    r, b = agg(recent), agg(base)
    m = r.merge(b, on=KEYS + ["size"], how="outer", suffixes=("_r", "_b")).fillna(0)
    m["share_r"] = m.units_r / m.groupby(KEYS).units_r.transform("sum").replace(0, np.nan)
    m["share_b"] = m.units_b / m.groupby(KEYS).units_b.transform("sum").replace(0, np.nan)
    m[["share_r", "share_b"]] = m[["share_r", "share_b"]].fillna(0)
    m["return_rate"] = safe_div(m.ret_r, m.units_r)
    m["size_return_rate"] = safe_div(m.size_ret_r, m.units_r)
    m["kept_r"] = (m.units_r - m.ret_r).clip(lower=0)
    m["kept_share"] = m.kept_r / m.groupby(KEYS).kept_r.transform("sum").replace(0, np.nan)
    n_r = m.groupby(KEYS).units_r.transform("sum")
    w = (n_r / (n_r + 150)).clip(0, 0.85)                       # shrink toward baseline when recent sample is small
    m["recommended_share"] = (w * m.kept_share.fillna(0) + (1 - w) * m.share_b)
    m["recommended_share"] = m.recommended_share / m.groupby(KEYS).recommended_share.transform("sum").replace(0, np.nan)
    m["share_shift_pp"] = (m.share_r - m.share_b) * 100
    rel = safe_div(m.share_r - m.share_b, m.share_b)
    m["risk"] = np.select([(m.share_shift_pp >= 3) & (rel >= 0.15), (m.share_shift_pp <= -3) & (rel <= -0.15) | (m.size_return_rate > 0.04)],
                          ["DEMAND_RISING_STOCKOUT_RISK", "DEMAND_FALLING_OVERSTOCK_OR_FIT_RISK"], default="BALANCED")
    # reorder need per product x location (same planning logic as the replenishment engine)
    lead = pl.supplier_lead_time_days.fillna(7)
    need = (pl.vel * (lead + cfg.target_cover_days) + pl.safety_stock_units.fillna(0) - pl.closing_stock).clip(lower=0).round().astype(int)
    needs = pl.assign(need=need)[KEYS + ["need", "product_name", "location_name", "gp_unit", "sizes"]]
    m = m.merge(needs, on=KEYS, how="left")
    out = []
    for (pid, lid), g in m.groupby(KEYS):
        total = int(g.need.iloc[0]) if pd.notna(g.need.iloc[0]) else 0
        g = g.copy()
        g["reorder_units"] = _alloc(total, g.set_index("size").recommended_share).reindex(g["size"]).values if total > 0 else 0
        out.append(g)
    m = pd.concat(out, ignore_index=True) if out else m
    fam = c.product.set_index("product_id").product_family
    m["product_family"] = m.product_id.map(fam)
    # family x location (more data per cell) and customer-segment view
    fl = m.groupby(["product_family", "location_id", "size"]).agg(units_r=("units_r", "sum"), units_b=("units_b", "sum"), ret=("ret_r", "sum")).reset_index()
    fl["share_r"] = fl.units_r / fl.groupby(["product_family", "location_id"]).units_r.transform("sum")
    fl["share_b"] = fl.units_b / fl.groupby(["product_family", "location_id"]).units_b.transform("sum")
    seg = window(s, "order_date", c.as_of, 365).groupby(["product_family", "customer_type", "size"]).quantity.sum().reset_index()
    seg["share"] = seg.quantity / seg.groupby(["product_family", "customer_type"]).quantity.transform("sum")
    # recommendations: only where a reorder is needed AND the mix has really shifted
    recs = []
    for (pid, lid), g in m.groupby(KEYS):
        total = int(g.need.iloc[0]) if pd.notna(g.need.iloc[0]) else 0
        if total < 50:
            continue
        mis = float((g.recommended_share - g.share_b).abs().sum() / 2)          # share of units that would sit in the wrong size
        if mis < 0.04:
            continue
        up = g.sort_values("share_shift_pp", ascending=False).iloc[0]
        down = g.sort_values("share_shift_pp").iloc[0]
        gpu = float(g.gp_unit.iloc[0] or 0)
        value = mis * total * gpu
        why = [f"Size {up['size']} share of sales rose {up.share_shift_pp:+.1f} pts vs the prior 12 months",
               f"Size {down['size']} share fell {down.share_shift_pp:+.1f} pts" + (f"; {down.size_return_rate:.1%} of its sales come back for size/fit" if down.size_return_rate > 0.03 else ""),
               NOTE]
        alloc = ", ".join(f"{r_['size']}: {int(r_.reorder_units)}" for _, r_ in g.sort_values("reorder_units", ascending=False).iterrows() if r_.reorder_units > 0)
        recs.append(make_rec("size_curve", "REPLENISH_SIZE", f"Re-weight reorder by size: {g.product_name.iloc[0]} @ {g.location_name.iloc[0]}",
                             "Reorder mix no longer matches what customers actually buy", why,
                             f"Reorder {total:,} units split by size as: {alloc}", "profit_protected", value, 0, 0.55 + 0.25 * min(float(g.units_r.sum()) / 1500, 1),
                             "MEDIUM" if value > 5000 else "LOW", product_id=pid, location_id=lid,
                             evidence=dict(reorder_total=total, mix_shift_share=mis, sizes=g[["size", "units_r", "share_r", "share_b", "recommended_share", "reorder_units"]].round(4).to_dict("records"))))
    return dict(rows=m, family_location=fl, segment=seg, recs=recs, note=NOTE)

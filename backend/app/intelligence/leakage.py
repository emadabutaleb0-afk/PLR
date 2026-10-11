"""12. PROFIT LEAKAGE ENGINE - where is the company losing money, in one additive view (last 12 months).

Five leakage types, each with an explicit basis so nobody mistakes an estimate for a fact:
  stockouts   ESTIMATE  stockout days x trailing-90d daily sales x actual gross profit per unit
  discounts   EXPOSURE  discount granted above the comfort band in Retail/Online (assumes no volume lift - see discount engine)
  quality     RECORDED  Estimated_Loss_EGP on QC inspections
  returns     RECORDED  gross profit of restocked returns + refunds of quality-related returns (same definition as the margin engine)
  production  ESTIMATE  rejected units x unit COGS (production orders + print batches) + print rework cost
Inspection losses and production rejects come from different tables and may partly describe the same units: they are shown separately, never netted.
VOLUME RECONCILIATION: factory records (production, print, QC) cover far more units than the sales ledger in the same 12 months. Factory-side leakage is therefore
attributed per product with ratio = min(1, units sold / units produced), so it is comparable with the sales-side leakage. Unscaled values are reported alongside."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.features import window
from app.intelligence.common import num, records, clean

TYPES = {
    "stockouts": dict(label="Stockout opportunity loss", basis="ESTIMATE", page="/inventory",
                      definition="Stockout days x trailing 90-day daily sales x gross profit per unit. Conservative: sales are depressed during a stockout."),
    "discounts": dict(label="Discount leakage", basis="EXPOSURE", page="/discounts",
                      definition="Discount value granted above the comfort band in Retail and Online. Assumes no volume lift, which is what the data shows."),
    "quality": dict(label="Quality loss", basis="RECORDED", page="/quality",
                    definition="Estimated loss on rejected units from QC inspections (as recorded in the Quality file)."),
    "returns": dict(label="Returns & refunds", basis="RECORDED", page="/quality",
                    definition="Gross profit lost on restocked returns plus refunds on quality-related returns."),
    "production": dict(label="Production & print waste", basis="ESTIMATE", page="/operations",
                       definition="Rejected production and print units at unit cost, plus print rework cost, attributed to the units the sales ledger can account for."),
}
NOTES = ["Quality inspection losses and production rejects come from different files and may partly overlap; they are shown separately and added without netting.",
         "Wholesale discounts are a structural price tier and are not counted as leakage.",
         "Leakage is what already happened in the last 12 months. It is not the same as recoverable profit: only part of it can be recovered."]


def profit_leakage(c, f: dict, pl: pd.DataFrame, lost: dict, ds: pd.DataFrame, cfg) -> dict:
    end = c.as_of
    first = (end.to_period("M") - 11).to_timestamp()
    ue = f["unit_econ"].set_index("product_id")
    cogs_u = ue.cogs_unit.reindex(c.product.product_id)
    cogs_u = cogs_u.fillna(float(cogs_u.median()) if cogs_u.notna().any() else 0.0)
    parts: list[pd.DataFrame] = []
    sold = window(c.sales, "order_date", end, 365).groupby("product_id").quantity.sum()
    made = c.prod[c.prod.start_date > end - pd.Timedelta(days=365)].groupby("product_id").produced_qty.sum()
    ratio = (sold.reindex(c.product.product_id) / made.reindex(c.product.product_id).replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
    raw = {}

    def add(kind, month, pid, val):
        d = pd.DataFrame(dict(month=pd.to_datetime(month), product_id=pid, value=np.asarray(val, dtype=float)))
        d["kind"] = kind
        parts.append(d[d.value > 0])

    # stockouts (inventory months)
    lr = lost["rows"]
    lr = lr[lr.month >= first]
    add("stockouts", lr.month, lr.product_id, lr.estimated_lost_profit)
    # discount exposure
    s = window(c.sales, "order_date", end, 365)
    s = s[s.channel.isin(["Retail", "Online"])]
    excess = (s.discount_pct.fillna(0) - cfg.discount_comfort_pct).clip(lower=0) * s.list_price_egp * s.quantity
    add("discounts", s.month, s.product_id, excess)
    # returns (same definition as monthly_pl.profit_after_returns)
    m = f["monthly_pl"]
    m = m[m.month >= first]
    add("returns", m.month, m.product_id, m.ret_gp + m.q_refund)
    # quality inspections
    q = c.qual[c.qual.inspection_date > end - pd.Timedelta(days=365)]
    raw["quality"] = float(q.estimated_loss_egp.fillna(0).sum())
    add("quality", q.inspection_date.dt.to_period("M").dt.to_timestamp(), q.product_id, q.estimated_loss_egp.fillna(0) * q.product_id.map(ratio).fillna(1.0))
    # production rejects + print waste
    pr = c.prod[c.prod.start_date > end - pd.Timedelta(days=365)]
    pv = pr.rejected_qty.fillna(0) * pr.product_id.map(cogs_u).fillna(0)
    pt = c.prt[c.prt.print_date > end - pd.Timedelta(days=365)]
    tv = pt.rejected_qty.fillna(0) * pt.product_id.map(cogs_u).fillna(0) + pt.rework_cost_egp.fillna(0)
    raw["production"] = float(pv.sum() + tv.sum())
    add("production", pr.start_date.dt.to_period("M").dt.to_timestamp(), pr.product_id, pv * pr.product_id.map(ratio).fillna(1.0))
    add("production", pt.print_date.dt.to_period("M").dt.to_timestamp(), pt.product_id, tv * pt.product_id.map(ratio).fillna(1.0))

    allv = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["month", "product_id", "value", "kind"])
    by_kind = allv.groupby("kind").value.sum().reindex(list(TYPES)).fillna(0.0)
    total = float(by_kind.sum())
    items = [dict(key=k, value=num(v), share=num(v / total, 4) if total else 0.0, **TYPES[k]) for k, v in by_kind.items()]
    items.sort(key=lambda x: -(x["value"] or 0))
    months = pd.date_range(first, periods=12, freq="MS")
    pm = allv.pivot_table(index="month", columns="kind", values="value", aggfunc="sum").reindex(months).reindex(columns=list(TYPES)).fillna(0.0)
    by_month = [dict(month=i.strftime("%Y-%m"), total=float(r.sum()), **{k: float(r[k]) for k in TYPES}) for i, r in pm.iterrows()]
    pp = allv.pivot_table(index="product_id", columns="kind", values="value", aggfunc="sum").reindex(columns=list(TYPES)).fillna(0.0)
    pp["total"] = pp.sum(axis=1)
    pp = pp.sort_values("total", ascending=False).head(15).reset_index()
    pp["product_name"] = pp.product_id.map(c.product.set_index("product_id").product_name)
    pp["main_driver"] = pp[list(TYPES)].idxmax(axis=1)
    # forward-looking: profit that is at risk if nothing changes
    risk = pl[pl.stockout_risk.isin(["HIGH", "MEDIUM"])]
    lead = risk.supplier_lead_time_days.fillna(7)
    so_risk = float((((risk.vel * (lead + 14)) - risk.closing_stock).clip(lower=0) * risk.gp_unit.fillna(0)).sum())
    dead_loss = float(ds.expected_loss.sum()) if len(ds) and "expected_loss" in ds else 0.0
    rec = dict(units_sold=num(sold.sum()), units_produced=num(made.sum()), units_inspected=num(q.inspected_qty.sum()),
               attribution_ratio=num(float(sold.sum() / made.sum()), 3) if made.sum() else None, unscaled_quality=num(raw.get("quality", 0)), unscaled_production=num(raw.get("production", 0)),
               label="Factory records cover more units than the sales ledger. Quality and production leakage are attributed per product by min(1, units sold / units produced); unscaled values are shown for transparency.")
    return clean(dict(
        reconciliation=rec, window_label=f"{first:%b %Y} - {end:%b %Y} (12 months)", total=total, items=items, by_month=by_month, top_products=records(pp), notes=NOTES,
        comfort_discount=cfg.discount_comfort_pct,
        profit_at_risk=dict(total=so_risk + dead_loss, stockout_profit_at_risk=so_risk, dead_stock_expected_loss=dead_loss,
                            label="Forward-looking estimate: gross profit that stock cannot cover at stock-risk locations (lead time + 14 days) plus the expected loss on stock unlikely to sell.")))

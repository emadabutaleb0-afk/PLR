"""18. CUSTOMER INTELLIGENCE - who is slipping away, how concentrated is profit, and does acquisition source or service quality matter?

Each customer is compared with THEIR OWN buying rhythm: expected gap = their median days between invoices (or the segment median if they have fewer than 3 invoices).
overdue ratio = days since last invoice / expected gap.   <=1.5 Active | 1.5-3 Slipping | >3 Lapsed | first invoice within 90 days and <=2 invoices New | single old invoice One-time.
Customer files are modelled/anonymised training data: only IDs, type and governorate are shown, never names."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.features import window, safe_div
from app.intelligence.common import num, records, clean

STATUS_ORDER = ["Active", "Slipping", "Lapsed", "New", "One-time"]
NOTES = ["Customers are compared with their own buying rhythm, so a monthly buyer and a yearly buyer are judged differently.",
         "Profit at risk from overdue customers is what these customers brought in the last 12 months; it is exposure, not a forecast of loss.",
         "Customer records in the supplied files are modelled/anonymised training data. No names or contact details are used."]


def customer_intelligence(c, cfg) -> dict:
    end = c.as_of
    s = c.sales[["customer_id", "customer_type", "invoice_id", "order_date", "net_sales_egp", "gross_profit_egp", "returned"]].dropna(subset=["customer_id"])
    inv = s.groupby(["customer_id", "invoice_id"]).agg(date=("order_date", "min"), net=("net_sales_egp", "sum"), gp=("gross_profit_egp", "sum"), ret=("returned", "max")).reset_index().sort_values(["customer_id", "date"])
    inv["gap"] = inv.groupby("customer_id").date.diff().dt.days
    cu = inv.groupby("customer_id").agg(orders=("invoice_id", "nunique"), first=("date", "min"), last=("date", "max"), median_gap=("gap", "median"), spend=("net", "sum"), gp=("gp", "sum"), returns=("ret", "mean")).reset_index()
    y = inv[inv.date > end - pd.Timedelta(days=365)].groupby("customer_id").agg(orders_12m=("invoice_id", "nunique"), gp_12m=("gp", "sum"), spend_12m=("net", "sum")).reset_index()
    cu = cu.merge(y, on="customer_id", how="left").fillna({"orders_12m": 0, "gp_12m": 0.0, "spend_12m": 0.0})
    cu = cu.merge(c.customers[["customer_id", "customer_type", "governorate", "acquisition_channel", "join_date"]], on="customer_id", how="left")
    cu["recency"] = (end - cu["last"]).dt.days
    seg_gap = cu[cu.orders >= 3].groupby("customer_type").median_gap.median()
    exp = np.where(cu.orders >= 3, cu.median_gap, cu.customer_type.map(seg_gap))
    cu["expected_gap"] = pd.Series(exp, index=cu.index).fillna(float(np.nanmedian(cu.median_gap.dropna()) if cu.median_gap.notna().any() else 60)).clip(lower=14)
    cu["overdue_ratio"] = cu.recency / cu.expected_gap
    new = ((end - cu["first"]).dt.days <= 90) & (cu.orders <= 2)
    one = (cu.orders == 1) & ~new
    cu["status"] = np.select([new, one, cu.overdue_ratio <= 1.5, cu.overdue_ratio <= 3], ["New", "One-time", "Active", "Slipping"], default="Lapsed")
    seg = cu.groupby("status").agg(customers=("customer_id", "count"), gp_12m=("gp_12m", "sum"), spend_12m=("spend_12m", "sum")).reindex(STATUS_ORDER).fillna(0).reset_index()
    seg["share_customers"] = safe_div(seg.customers, seg.customers.sum())
    seg["share_gp"] = safe_div(seg.gp_12m, seg.gp_12m.sum())
    overdue = cu[cu.status.isin(["Slipping", "Lapsed"]) & (cu.gp_12m > 0)]
    buyers12 = cu[cu.orders_12m > 0]
    top10 = buyers12.sort_values("gp_12m", ascending=False).head(max(int(len(buyers12) * 0.10), 1))
    wh = cu[cu.customer_type == "Wholesale"]
    accts = overdue.sort_values("gp_12m", ascending=False).head(15)[["customer_id", "customer_type", "governorate", "orders", "gp_12m", "recency", "expected_gap", "overdue_ratio", "status"]]
    ch = cu[cu.customer_type == "Retail"].groupby("acquisition_channel").agg(customers=("customer_id", "count"), buyers=("orders", lambda v: float(v.notna().mean())), repeat=("orders", lambda v: float((v >= 2).sum() / max(v.notna().sum(), 1))),
                                                                       gp_per_customer=("gp", "mean"), orders=("orders", "mean")).reset_index().sort_values("customers", ascending=False)
    spread = float(ch.repeat.max() - ch.repeat.min()) if len(ch) > 1 else 0.0
    gov = buyers12.groupby("governorate").agg(customers=("customer_id", "count"), gp_12m=("gp_12m", "sum")).reset_index().sort_values("gp_12m", ascending=False).head(8)
    cs = c.cs.copy()
    svc = cs.groupby("channel").agg(tickets=("ticket_id", "count"), csat=("csat_1_to_5", "mean"), first_response_min=("first_response_minutes", "mean"), resolution_h=("resolution_hours", "mean"), resolved=("resolved", "mean")).reset_index()
    iss = cs.groupby("issue_type").agg(tickets=("ticket_id", "count"), csat=("csat_1_to_5", "mean"), resolution_h=("resolution_hours", "mean")).reset_index().sort_values("csat")
    r90, p90 = window(cs, "open_date", end, 90), window(cs, "open_date", end, 180, 90)
    kp = dict(customers_12m=int(len(buyers12)), repeat_rate=num(float((cu.orders >= 2).mean()), 4), top10_share_gp=num(float(top10.gp_12m.sum() / max(buyers12.gp_12m.sum(), 1)), 4),
              overdue_customers=int(len(overdue)), overdue_gp_12m=num(float(overdue.gp_12m.sum())), overdue_wholesale=int((overdue.customer_type == "Wholesale").sum()),
              overdue_wholesale_gp=num(float(overdue[overdue.customer_type == "Wholesale"].gp_12m.sum())), wholesale_share_gp=num(float(wh.gp_12m.sum() / max(buyers12.gp_12m.sum(), 1)), 4),
              csat_90d=num(float(r90.csat_1_to_5.mean()), 2) if len(r90) else None, csat_prev_90d=num(float(p90.csat_1_to_5.mean()), 2) if len(p90) else None)
    channel_note = ("Acquisition channels behave almost the same in this data (repeat rate differs by under %.0f points), so the source of a customer does not predict their value here." % (spread * 100)) if spread < 0.03 else \
                   "Acquisition channels differ in repeat rate: compare cost per customer before moving budget."
    return clean(dict(kpis=kp, segments=records(seg), accounts=records(accts), channels=records(ch), channel_note=channel_note, governorates=records(gov), service_channels=records(svc), service_issues=records(iss), notes=NOTES,
                      window_label=f"{(end - pd.Timedelta(days=364)):%b %Y} - {end:%b %Y} (12 months)"))

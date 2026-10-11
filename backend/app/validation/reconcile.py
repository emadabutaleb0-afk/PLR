"""Cross-file reconciliation: do the company files agree with each other, and which headline numbers are NOT comparable?
Reads the CSVs directly (independent of the DB) so it can audit any data folder before or after an import.
Each check returns status OK / WARN / FAIL with the measured numbers; nothing is 'fixed' silently.
CLI:  python -m app.validation.reconcile <data_dir>
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd


def _r(d: Path, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(d / f"{name}.csv", encoding="utf-8-sig", **kw)


def _chk(name: str, status: str, detail: str, **numbers) -> dict:
    return dict(check=name, status=status, detail=detail, numbers={k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in numbers.items()})


def _share_bad(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else 0.0


def reconcile(data_dir: str) -> dict:
    d = Path(data_dir)
    out: list[dict] = []
    s = _r(d, "Sales_Transactions", parse_dates=["Order_Date"])
    inv = _r(d, "Inventory_History", parse_dates=["Snapshot_Month"])
    po = _r(d, "Purchase_Orders", parse_dates=["Order_Date"])
    pr = _r(d, "Production_Orders", parse_dates=["Start_Date"])
    qc = _r(d, "Quality", parse_dates=["Inspection_Date"])
    pm = _r(d, "Product_Master")

    # 1. period coverage: headline numbers across files are only comparable on the overlapping window
    cov = {n: (df[c].min(), df[c].max()) for n, df, c in
           [("sales", s, "Order_Date"), ("inventory", inv, "Snapshot_Month"), ("purchases", po, "Order_Date"), ("production", pr, "Start_Date"), ("quality", qc, "Inspection_Date")]}
    lo, hi = max(v[0] for v in cov.values()), min(v[1] for v in cov.values())
    out.append(_chk("period_coverage", "OK" if lo < hi else "FAIL",
                    "Files cover different periods; compare them only inside the common window." if any(v != (lo, hi) for v in cov.values()) else "All files cover the same period.",
                    common_from=str(lo.date()), common_to=str(hi.date()), **{f"{k}_range": f"{v[0].date()}..{v[1].date()}" for k, v in cov.items()}))

    # 2. sales arithmetic
    net_calc = s.Quantity * s.List_Price_EGP * (1 - s.Discount_Pct)
    bad_net = _share_bad((net_calc - s.Net_Sales_EGP).abs() > 1.0)
    bad_gp = _share_bad((s.Net_Sales_EGP - s.Estimated_COGS_EGP - s.Gross_Profit_EGP).abs() > 1.0)
    out.append(_chk("sales_arithmetic", "OK" if max(bad_net, bad_gp) < 0.01 else "WARN",
                    "Net = Qty x List x (1-Discount) and GP = Net - COGS should hold row by row.", net_mismatch_share=bad_net, gp_mismatch_share=bad_gp))

    # 3. sales vs inventory sold quantity, per product x month, in the common window
    s["m"] = s.Order_Date.dt.to_period("M").astype(str)
    inv["m"] = inv.Snapshot_Month.dt.to_period("M").astype(str)
    a = s.groupby(["Product_ID", "m"]).Quantity.sum().rename("sales_qty")
    b = inv.groupby(["Product_ID", "m"]).Sold_Qty.sum().rename("inv_qty")
    j = pd.concat([a, b], axis=1).dropna()
    gap = float((j.sales_qty - j.inv_qty).abs().sum() / max(j.inv_qty.sum(), 1))
    out.append(_chk("sales_vs_inventory_sold", "OK" if gap < 0.05 else "WARN",
                    "Units sold in the sales ledger vs units sold in inventory history (same product and month).", relative_gap=gap, matched_cells=len(j), sales_units=float(j.sales_qty.sum()), inventory_units=float(j.inv_qty.sum())))

    # 4. inventory identity
    ident = inv.Opening_Stock + inv.Received_Qty - inv.Sold_Qty + inv.Returned_Qty - inv.Damaged_Qty - inv.Closing_Stock
    bad = _share_bad(ident.abs() > 1)
    out.append(_chk("inventory_roll_forward", "OK" if bad < 0.01 else "WARN", "Opening + received - sold + returned - damaged should equal closing.", mismatch_share=bad))

    # 5. production and QC identities
    bad_p = _share_bad((pr.Good_Qty + pr.Rejected_Qty - pr.Produced_Qty).abs() > 1)
    bad_q = _share_bad((qc.Passed_Qty + qc.Rejected_Qty - qc.Inspected_Qty).abs() > 1)
    out.append(_chk("production_and_qc_identities", "OK" if max(bad_p, bad_q) < 0.01 else "WARN", "Good + rejected = produced; passed + rejected = inspected.", production_mismatch=bad_p, qc_mismatch=bad_q))

    # 6. referential integrity
    orphan = float((~s.Product_ID.isin(pm.Product_ID)).mean())
    out.append(_chk("sales_product_in_master", "OK" if orphan == 0 else "FAIL", "Every sold Product_ID must exist in Product_Master.", orphan_share=orphan))

    # 7. scope comparability (NOT errors: they stop wrong headline comparisons)
    win = lambda df, c: df[(df[c] >= lo) & (df[c] <= hi)]
    sw, pw, prw = win(s, "Order_Date"), win(po, "Order_Date"), win(pr, "Start_Date")
    sold_units, produced_units = float(sw.Quantity.sum()), float(prw.Produced_Qty.sum())
    ratio_u = produced_units / max(sold_units, 1)
    out.append(_chk("units_produced_vs_sold", "OK" if 0.5 <= ratio_u <= 1.5 else "WARN",
                    "Factory output is not the same scope as the sales ledger; per-product leakage must be scaled (V3 does this with min(1, sold/produced)).",
                    produced_units=produced_units, sold_units=sold_units, ratio=ratio_u))
    purch_value = float((pw.Ordered_Qty * pw.Unit_Cost_EGP).sum())
    cogs, net = float(sw.Estimated_COGS_EGP.sum()), float(sw.Net_Sales_EGP.sum())
    ratio_v = purch_value / max(net, 1)
    out.append(_chk("purchases_vs_sales_value", "OK" if ratio_v <= 1.0 else "WARN",
                    "Raw-material purchases exceed retail net sales: different accounting scope. Do not net them against each other or report them as one loss figure.",
                    purchases_egp=purch_value, net_sales_egp=net, cogs_egp=cogs, purchases_to_net_sales=ratio_v))

    worst = "FAIL" if any(c["status"] == "FAIL" for c in out) else "WARN" if any(c["status"] == "WARN" for c in out) else "OK"
    return dict(status=worst, checks=out, summary={k: sum(1 for c in out if c["status"] == k) for k in ("OK", "WARN", "FAIL")})


if __name__ == "__main__":
    import json
    print(json.dumps(reconcile(sys.argv[1]), ensure_ascii=False, indent=2, default=str))

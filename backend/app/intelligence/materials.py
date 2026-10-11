"""13. SUPPLY READINESS ENGINE - forecast demand -> inventory gap -> production requirement -> material requirement -> supplier risk.

Honest limits: the data has NO raw-material stock on hand, so this engine reports what is required and how reliably each material arrives; it does not claim a physical shortage.
Production need = max(90-day forecast + safety stock - stock on hand, 0), grossed up for the product's production reject rate."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.features import window, safe_div
from app.intelligence.common import num, records, clean

W = dict(late_rate=0.45, avg_delay=0.30, reject_rate=0.25)
HIGH, MED = 55, 35
LIMITS = ["No raw-material stock on hand exists in the data: requirement and supplier reliability are reported, not a physical shortage.",
          "Requirement uses the demand forecast and Product_BOM quantities as supplied; BOM is a modelled training BOM.",
          "Supplier risk is based on the last 12 months of purchase orders: lateness vs promised date, average delay when late, and rejected share."]


def _supplier_view(c, end) -> pd.DataFrame:
    po = c.po.copy()
    po = po[po.order_date > end - pd.Timedelta(days=365)] if (po.order_date > end - pd.Timedelta(days=365)).any() else po
    po["delay"] = (po.actual_receipt_date - po.promised_date).dt.days
    po["lead"] = (po.actual_receipt_date - po.order_date).dt.days
    po["late"] = (po.delay > 0).astype(float)
    po["spend"] = po.ordered_qty * po.unit_cost_egp
    g = po.groupby("material_id").agg(po_count=("po_id", "count"), spend=("spend", "sum"), ordered=("ordered_qty", "sum"), rejected=("rejected_qty", "sum"),
                                      late_rate=("late", "mean"), lead_p90=("lead", lambda x: float(x.dropna().quantile(0.9)) if x.notna().any() else np.nan),
                                      lead_avg=("lead", "mean")).reset_index()
    late = po[po.delay > 0].groupby("material_id").delay.mean().rename("avg_delay_when_late")
    g = g.merge(late.reset_index(), how="left").fillna({"avg_delay_when_late": 0.0})
    g["reject_rate"] = safe_div(g.rejected, g.ordered)
    top = po.groupby(["material_id", "supplier_id"]).spend.sum().reset_index().sort_values("spend", ascending=False).drop_duplicates("material_id")
    top = top.merge(c.sup[["supplier_id", "supplier_name"]], how="left").rename(columns={"supplier_id": "main_supplier_id", "supplier_name": "main_supplier"})
    g = g.merge(top[["material_id", "main_supplier_id", "main_supplier"]], how="left")
    g["risk_score"] = 100 * (W["late_rate"] * g.late_rate.fillna(0) + W["avg_delay"] * np.clip(g.avg_delay_when_late / 10, 0, 1) + W["reject_rate"] * np.clip(g.reject_rate / 0.05, 0, 1))
    g["risk"] = np.where(g.risk_score >= HIGH, "HIGH", np.where(g.risk_score >= MED, "MEDIUM", "LOW"))
    return g


def supply_readiness(c, f: dict, pl: pd.DataFrame, cfg) -> dict:
    end = c.as_of
    pe = f["unit_econ"].set_index("product_id")
    g = pl.groupby("product_id").agg(forecast=("forecast_90d_units", "sum"), vel=("vel", "sum"), stock=("closing_stock", "sum"), safety=("safety_stock_units", "sum"),
                                     min_cover=("doc", "min"), so_high=("stockout_risk", lambda x: int((x == "HIGH").sum())),
                                     so_any=("stockout_risk", lambda x: int(x.isin(["HIGH", "MEDIUM"]).sum()))).reset_index()
    g["forecast"] = np.where(g.forecast.fillna(0) > 0, g.forecast, g.vel * 90)
    g["need"] = (g.forecast + g.safety.fillna(0) - g.stock).clip(lower=0)
    rr = f["prod_prod"].set_index("product_id").pr_reject_rate.reindex(g.product_id)
    rr = rr.fillna(float(rr.median()) if rr.notna().any() else 0.0).clip(0, 0.3).values
    g["gross_need"] = g.need / (1 - rr)
    g["gp_unit"] = g.product_id.map(pe.gp_unit).fillna(0)
    g["profit_dependent"] = g.need * g.gp_unit
    g["profit_dependent_forecast"] = g.forecast * g.gp_unit
    sv = _supplier_view(c, end)
    b = c.bom[["product_id", "material_id", "required_per_unit"]].merge(g[["product_id", "forecast", "need", "gross_need", "profit_dependent", "profit_dependent_forecast"]], on="product_id", how="left")
    b["req_forecast"] = b.forecast.fillna(0) * b.required_per_unit
    b["req_gap"] = b.gross_need.fillna(0) * b.required_per_unit
    mat = b.groupby("material_id").agg(requirement_forecast_90d=("req_forecast", "sum"), requirement_gap_90d=("req_gap", "sum"), profit_dependent=("profit_dependent", "sum"),
                                        profit_dependent_forecast=("profit_dependent_forecast", "sum"), products=("product_id", "nunique")).reset_index()
    pname = c.product.set_index("product_id").product_name
    topp = b.sort_values("req_gap", ascending=False).assign(pname=lambda d: d.product_id.map(pname)).groupby("material_id").pname.apply(lambda x: list(x.head(3))).rename("top_products")
    mat = mat.merge(c.mat[["material_id", "material_name", "unit", "material_category", "standard_lead_time_days"]], on="material_id", how="left") \
             .merge(sv, on="material_id", how="left").merge(topp.reset_index(), on="material_id", how="left")
    mat["lead_slip_days"] = (mat.lead_p90 - mat.standard_lead_time_days)
    mat["order_ahead_days"] = np.ceil(mat.lead_p90.fillna(mat.standard_lead_time_days))
    mat["risk_score"] = mat.risk_score.fillna(0)
    mat["risk"] = mat.risk.fillna("LOW")
    mat = mat.sort_values(["risk_score", "profit_dependent"], ascending=False)
    mat["action"] = np.where(mat.risk.isin(["HIGH", "MEDIUM"]),
                             "Order at least " + mat.order_ahead_days.fillna(0).astype(int).astype(str) + " days ahead of need and keep a buffer: " + (mat.late_rate.fillna(0) * 100).round(0).astype(int).astype(str) + "% of recent purchase orders arrived late",
                             "No change needed: supplier delivery is reliable")
    # product readiness: can the factory + materials actually deliver the replenishment?
    pg = f["prod_prod"].set_index("product_id")
    qg = f["qual_prod"].set_index("product_id")
    pr = window(c.prod, "start_date", end, 180)
    pr = pr[pr.primary_bottleneck.astype(str).str.lower() != "none"]
    bott = pr.groupby("product_id").primary_bottleneck.agg(lambda x: x.value_counts().index[0]).rename("bottleneck")
    bom_risk = c.bom[["product_id", "material_id"]].merge(mat[["material_id", "material_name", "risk_score"]], on="material_id", how="left").sort_values("risk_score", ascending=False)
    worst = bom_risk.drop_duplicates("product_id").set_index("product_id")[["material_name", "risk_score"]].rename(columns={"material_name": "riskiest_material", "risk_score": "material_risk"})
    r = g.merge(c.product[["product_id", "product_name", "sku"]], on="product_id", how="left").merge(bott.reset_index(), how="left").merge(worst.reset_index(), how="left")
    r["delayed_share"] = r.product_id.map(pg.pr_delayed_share)
    r["prod_reject_rate"] = r.product_id.map(pg.pr_reject_rate)
    r["qc_reject_rate"] = r.product_id.map(qg.q_reject_rate)
    hi_pr, hi_qc = r.prod_reject_rate.quantile(0.75), r.qc_reject_rate.quantile(0.75)
    pts = ((r.delayed_share.fillna(0) >= 0.35).astype(int) + (r.prod_reject_rate.fillna(0) >= hi_pr).astype(int) + (r.qc_reject_rate.fillna(0) >= hi_qc).astype(int)
           + np.where(r.material_risk.fillna(0) >= HIGH, 2, np.where(r.material_risk.fillna(0) >= MED, 1, 0)) + r.bottleneck.notna().astype(int))
    r["readiness_points"] = pts
    r["readiness"] = np.where(pts >= 3, "AT_RISK", np.where(pts >= 1, "WATCH", "READY"))
    r = r[(r.so_any > 0) | (r.need > 0)].sort_values(["readiness_points", "profit_dependent"], ascending=False)

    def reasons(x):
        bits = []
        if isinstance(x.bottleneck, str):
            bits.append(f"production bottleneck: {x.bottleneck}")
        if pd.notna(x.delayed_share) and x.delayed_share >= 0.35:
            bits.append(f"{x.delayed_share:.0%} of recent production orders ran late")
        if pd.notna(x.material_risk) and x.material_risk >= MED:
            bits.append(f"depends on {x.riskiest_material} (supplier risk {x.material_risk:.0f}/100)")
        if pd.notna(x.qc_reject_rate) and x.qc_reject_rate >= hi_qc:
            bits.append("high quality reject rate")
        return bits
    r["reasons"] = r.apply(reasons, axis=1)
    r["verdict"] = np.where(r.reasons.map(len) == 0, "Factory, quality and suppliers look able to meet the replenishment.",
                            np.where(r.so_any > 0, "Replenishment may be delayed", "Watch"))
    cols = ["product_id", "product_name", "sku", "so_high", "so_any", "min_cover", "forecast", "stock", "need", "gross_need", "profit_dependent", "bottleneck", "delayed_share",
            "prod_reject_rate", "qc_reject_rate", "riskiest_material", "material_risk", "readiness", "readiness_points", "verdict", "reasons"]
    mc = ["material_id", "material_name", "unit", "material_category", "requirement_forecast_90d", "requirement_gap_90d", "products", "top_products", "profit_dependent", "main_supplier",
          "po_count", "spend", "late_rate", "avg_delay_when_late", "reject_rate", "standard_lead_time_days", "lead_p90", "lead_slip_days", "order_ahead_days", "risk_score", "risk", "action"]
    flow = dict(forecast_units=num(g.forecast.sum()), stock_units=num(g.stock.sum()), safety_units=num(g.safety.sum()), production_need_units=num(g.need.sum()),
                gross_production_units=num(g.gross_need.sum()), materials_at_risk=int(mat.risk.isin(["HIGH", "MEDIUM"]).sum()), materials_high=int((mat.risk == "HIGH").sum()),
                profit_dependent=num(g.profit_dependent.sum()), products_at_risk=int((r.readiness == "AT_RISK").sum()))
    return clean(dict(flow=flow, materials=records(mat[mc]), products=records(r[cols].head(40)), weights=W, thresholds=dict(high=HIGH, medium=MED), limits=LIMITS))

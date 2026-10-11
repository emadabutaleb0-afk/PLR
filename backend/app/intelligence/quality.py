"""8. QUALITY IMPACT ENGINE - links QC, production, printing, returns and customer service. Association is reported, never causation."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import make_rec, egp, num


def _m(d, col):
    return d.assign(month=d[col].dt.to_period("M").dt.to_timestamp())


def quality_engine(c: Ctx, f: dict, cfg) -> dict:
    q = c.qual.copy(); q["defect_type"] = q.defect_type.fillna("None"); q["root_cause"] = q.root_cause.fillna("None")
    defects = q[q.defect_type != "None"]
    pareto = defects.groupby("defect_type").agg(loss=("estimated_loss_egp", "sum"), rejected=("rejected_qty", "sum"), events=("qc_id", "count")).sort_values("loss", ascending=False).reset_index()
    pareto["cum_share"] = pareto.loss.cumsum() / pareto.loss.sum()
    causes = defects.groupby("root_cause").agg(loss=("estimated_loss_egp", "sum"), rejected=("rejected_qty", "sum")).sort_values("loss", ascending=False).reset_index()
    stage = q.groupby("stage").agg(inspected=("inspected_qty", "sum"), rejected=("rejected_qty", "sum"), loss=("estimated_loss_egp", "sum")).reset_index()
    stage["reject_rate"] = safe_div(stage.rejected, stage.inspected)
    prod_q = q.groupby("product_id").agg(inspected=("inspected_qty", "sum"), rejected=("rejected_qty", "sum"), loss=("estimated_loss_egp", "sum")).reset_index()
    prod_q["reject_rate"] = safe_div(prod_q.rejected, prod_q.inspected)
    ret = c.sales[c.sales.returned.fillna(False).astype(bool)]
    returns_by_reason = ret.groupby("return_reason").agg(units=("quantity", "sum"), refund=("refund_value_egp", "sum")).sort_values("refund", ascending=False).reset_index()
    qret = ret[ret.quality_related_return.fillna(False).astype(bool)].groupby("product_id").agg(q_return_units=("quantity", "sum"), q_refund=("refund_value_egp", "sum")).reset_index()
    prod_q = prod_q.merge(qret, how="left").fillna({"q_return_units": 0, "q_refund": 0}).merge(c.product[["product_id", "product_name", "sku"]], on="product_id")
    prod_q["cost_of_poor_quality"] = prod_q.loss + prod_q.q_refund
    # monthly series for associations
    qm = _m(q, "inspection_date").groupby("month").apply(lambda d: pd.Series(dict(qc_reject_rate=d.rejected_qty.sum() / max(d.inspected_qty.sum(), 1), qc_loss=d.estimated_loss_egp.sum())), include_groups=False)
    pm = _m(c.prt, "print_date").groupby("month").apply(lambda d: pd.Series(dict(print_reject_rate=d.rejected_qty.sum() / max(d.printed_qty.sum(), 1), rework_cost=d.rework_cost_egp.sum())), include_groups=False)
    pr = _m(c.prod, "start_date").groupby("month").apply(lambda d: pd.Series(dict(prod_reject_rate=d.rejected_qty.sum() / max(d.produced_qty.sum(), 1), prod_delay=d.delay_days.mean())), include_groups=False)
    s = c.sales.assign(q=c.sales.quality_related_return.fillna(False).astype(bool))
    sm = s.groupby("month").apply(lambda d: pd.Series(dict(quality_return_rate=d.loc[d.q, "quantity"].sum() / max(d.quantity.sum(), 1), quality_refund=d.loc[d.q, "refund_value_egp"].sum())), include_groups=False)
    cs = _m(c.cs, "open_date").groupby("month").apply(lambda d: pd.Series(dict(tickets=len(d), csat=d.csat_1_to_5.mean(), return_tickets=int((d.issue_type.str.contains("eturn|efund|uality|efect", na=False)).sum()))), include_groups=False)
    monthly = pd.concat([qm, pm, pr, sm, cs], axis=1).dropna(how="all")
    findings, pairs = [], [("qc_reject_rate", "quality_return_rate", "Higher QC reject rates and quality-related returns"),
                          ("print_reject_rate", "quality_return_rate", "Printing reject rates and quality-related returns"),
                          ("prod_reject_rate", "quality_return_rate", "Production reject rates and quality-related returns"),
                          ("quality_return_rate", "csat", "Quality-related returns and customer satisfaction (CSAT)"),
                          ("qc_reject_rate", "return_tickets", "QC reject rates and return/quality tickets")]
    for a, b, text in pairs:
        for lag in (0, 1):
            d = pd.concat([monthly[a].shift(lag), monthly[b]], axis=1).dropna()
            if len(d) >= 18:
                rho, p = spearmanr(d.iloc[:, 0], d.iloc[:, 1])
                strong = abs(rho) >= 0.3 and p < 0.05
                findings.append(dict(pair=text, lag_months=lag, rho=num(rho, 3), p_value=num(p, 4), months=len(d), reliable=bool(strong),
                                     reading=(f"{text} move together (rho {rho:+.2f}, {len(d)} months). This is an association; it does not prove cause." if strong
                                              else f"No reliable relationship found between {text.lower()} at a {lag}-month lag (rho {rho:+.2f}, p {p:.2f}).")))
    cpq = dict(qc_loss=num(q.estimated_loss_egp.sum()), printing_rework=num(c.prt.rework_cost_egp.sum()), quality_refunds=num(ret[ret.quality_related_return.fillna(False).astype(bool)].refund_value_egp.sum()))
    # recommendations: product x stage x defect with the largest recent loss
    recent = window(defects, "inspection_date", c.as_of, 180)
    top = recent.groupby(["product_id", "stage", "defect_type", "root_cause"]).agg(loss=("estimated_loss_egp", "sum"), rejected=("rejected_qty", "sum")).reset_index().sort_values("loss", ascending=False)
    thr = top.loss.quantile(0.95) if len(top) else 0
    nm = c.product.set_index("product_id").product_name
    recs = []
    for _, r in top[top.loss >= thr].head(12).iterrows():
        recs.append(make_rec("quality_impact", "FIX_QUALITY", f"Quality loss: {r.defect_type} at {r.stage} ({nm.get(r.product_id)})", "A recurring defect is costing money",
                             [f"{r.defect_type} at {r.stage} stage lost {egp(r.loss)} in the last 180 days ({int(r.rejected)} rejected units)", f"Recorded root cause: {r.root_cause}",
                              "Association with returns/CSAT is tracked on the Quality page; causality is not claimed"],
                             f"Run a corrective action on {r.defect_type} ({r.root_cause}) at {r.stage} for {nm.get(r.product_id)}", "loss_avoided", float(r.loss) * 0.5, float(r.loss), 0.6,
                             "HIGH" if r.loss > top.loss.quantile(0.99) else "MEDIUM", product_id=r.product_id, department="Quality", suffix=f"{r.stage}:{r.defect_type}:{r.root_cause}",
                             evidence=dict(basis="recoverable = 50% of recent loss if the defect is halved (scenario)", stage=r.stage, defect=r.defect_type, root_cause=r.root_cause)))
    return dict(pareto=pareto, causes=causes, stage=stage, products=prod_q.sort_values("cost_of_poor_quality", ascending=False), returns=returns_by_reason,
                monthly=monthly.reset_index(), findings=findings, cost_of_poor_quality=cpq, recs=recs)

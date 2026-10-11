"""Operations Control: production efficiency, bottlenecks, machine downtime, printing rework."""
from __future__ import annotations
import numpy as np
import pandas as pd
from app.analytics.context import Ctx
from app.analytics.features import window, safe_div
from app.intelligence.common import make_rec, egp, num


def operations_engine(c: Ctx, f: dict, cfg) -> dict:
    pr = c.prod.copy(); pr["bottleneck"] = pr.primary_bottleneck.fillna("None")
    unit_cost = f["unit_econ"].set_index("product_id").cogs_unit
    pr["reject_cost"] = pr.rejected_qty * pr.product_id.map(unit_cost).fillna(0)
    pr["month"] = pr.start_date.dt.to_period("M").dt.to_timestamp()
    b = pr[pr.bottleneck != "None"].groupby("bottleneck").agg(orders=("production_order_id", "count"), delay_days=("delay_days", "sum"), avg_delay=("delay_days", "mean"),
                                                             overtime_hours=("overtime_hours", "sum"), avg_efficiency=("efficiency_pct", "mean"), reject_cost=("reject_cost", "sum")).reset_index()
    b["share_of_delay"] = safe_div(b.delay_days, b.delay_days.sum())
    lines = pr.groupby("line_id").agg(orders=("production_order_id", "count"), efficiency=("efficiency_pct", "mean"), delay=("delay_days", "mean"),
                                      reject_rate=("rejected_qty", "sum"), produced=("produced_qty", "sum"), overtime=("overtime_hours", "sum"), reject_cost=("reject_cost", "sum")).reset_index()
    lines["reject_rate"] = safe_div(lines.reject_rate, lines.produced)
    monthly = pr.groupby("month").agg(efficiency=("efficiency_pct", "mean"), delay=("delay_days", "mean"), orders=("production_order_id", "count"),
                                      rejected=("rejected_qty", "sum"), produced=("produced_qty", "sum"), overtime=("overtime_hours", "sum")).reset_index()
    monthly["reject_rate"] = safe_div(monthly.rejected, monthly.produced)
    dt = c.dt.copy(); dt["unplanned"] = ~dt.planned.fillna(False).astype(bool)
    dm = dt.groupby("machine_id").agg(events=("downtime_id", "count"), hours=("downtime_hours", "sum"), unplanned_hours=("downtime_hours", lambda x: x[dt.loc[x.index, "unplanned"]].sum()),
                                      business_area=("business_area", "first")).reset_index().sort_values("unplanned_hours", ascending=False)
    reasons = dt[dt.unplanned].groupby("reason").agg(hours=("downtime_hours", "sum"), events=("downtime_id", "count")).sort_values("hours", ascending=False).reset_index()
    r6, p6 = window(dt, "date", c.as_of, 180), window(dt, "date", c.as_of, 360, 180)
    d_tr = pd.concat([r6[r6.unplanned].groupby("machine_id").downtime_hours.sum().rename("recent"), p6[p6.unplanned].groupby("machine_id").downtime_hours.sum().rename("previous")], axis=1).fillna(0).reset_index()
    d_tr["change_pct"] = safe_div(d_tr.recent - d_tr.previous, d_tr.previous)
    pb = c.prt.copy()
    pm = pb.groupby("machine_id").agg(batches=("print_batch_id", "count"), printed=("printed_qty", "sum"), good=("good_qty", "sum"), rejected=("rejected_qty", "sum"),
                                      reprint=("reprint_qty", "sum"), rework_cost=("rework_cost_egp", "sum"), consumables=("ink_or_consumable_cost_egp", "sum")).reset_index()
    pm["yield"] = safe_div(pm.good, pm.printed); pm["reject_rate"] = safe_div(pm.rejected, pm.printed)
    hrs = dt.groupby("machine_id").downtime_hours.sum()
    pm["downtime_hours"] = pm.machine_id.map(hrs).fillna(0)
    pdefects = pb[pb.defect_type.fillna("None") != "None"].groupby("defect_type").agg(rework_cost=("rework_cost_egp", "sum"), rejected=("rejected_qty", "sum")).sort_values("rework_cost", ascending=False).reset_index()
    ops = c.ops.copy()
    mm = pd.concat([dt[dt.unplanned].groupby(dt.date.dt.to_period("M")).downtime_hours.sum().rename("down"), pr.groupby(pr.start_date.dt.to_period("M")).agg(delay=("delay_days", "mean"), eff=("efficiency_pct", "mean"))], axis=1).dropna()
    rho = float(mm.down.corr(mm.delay)) if len(mm) >= 12 else None
    area = dt[dt.unplanned].groupby("business_area").downtime_hours.sum()
    bn = pr[pr.bottleneck != "None"].groupby("bottleneck").delay_days.sum()
    link = pd.concat([area.rename("unplanned_downtime_hours"), bn.rename("bottleneck_delay_days")], axis=1).fillna(0).reset_index().rename(columns={"index": "stage"})
    link["stage"] = link.iloc[:, 0]
    downtime_link = dict(months=int(len(mm)), correlation=num(rho, 2), stages=link[["stage", "unplanned_downtime_hours", "bottleneck_delay_days"]].to_dict("records"),
                         verdict=("Unplanned downtime and production delays do not move together month to month (correlation near zero). Maintenance alone is unlikely to fix delays." if rho is not None and abs(rho) < 0.3 else
                                  ("Months with more unplanned downtime tend to have longer production delays." if rho is not None and rho >= 0.3 else "Not enough months to compare downtime with delays.")),
                         note="Compare stages: the stage with the most downtime is not always the stage that causes the delays.")
    recs = []
    # bottleneck recommendation (priced where the data allows: rejected production at cost)
    if len(b):
        t = b.sort_values("delay_days", ascending=False).iloc[0]
        recs.append(make_rec("operations", "FIX_BOTTLENECK", f"Fix the {t.bottleneck} bottleneck", "One production stage causes the largest share of delays",
                             [f"{t.bottleneck} is the primary bottleneck in {int(t.orders)} orders and {t.share_of_delay:.0%} of all bottleneck delay days",
                              f"{t.overtime_hours:,.0f} overtime hours and {egp(t.reject_cost)} of rejected output (at cost) sit on these orders"],
                             f"Add capacity / re-sequence work at {t.bottleneck}; review line balancing", "loss_avoided", float(t.reject_cost) * 0.3, float(t.reject_cost), 0.5, "MEDIUM",
                             entity_type="process", entity_id=t.bottleneck, department="Production",
                             evidence=dict(basis="30% of rejected-output cost on bottleneck orders (scenario); overtime cost in EGP is not in the data", unpriced=["overtime hours", "delay days"])))
    for _, r in d_tr[(d_tr.change_pct >= 0.25) & (d_tr.recent >= 20)].sort_values("recent", ascending=False).head(3).iterrows():
        mrow = pm[pm.machine_id == r.machine_id]
        rw = float(mrow.rework_cost.iloc[0]) if len(mrow) else 0.0
        recs.append(make_rec("operations", "MAINTAIN_MACHINE", f"Machine {r.machine_id}: unplanned downtime up {r.change_pct:.0%}", "Unplanned downtime is rising",
                             [f"{r.recent:.0f} unplanned downtime hours in the last 6 months vs {r.previous:.0f} before",
                              "EGP cost of downtime is not in the data; priced only through printing rework when the machine is a printer"],
                             f"Schedule preventive maintenance on {r.machine_id} and review the top failure reasons", "loss_avoided", rw * 0.1, rw, 0.45, "MEDIUM",
                             entity_type="machine", entity_id=r.machine_id, department="Production", evidence=dict(unpriced=["downtime hours"], basis="10% of the machine's printing rework cost (scenario)")))
    return dict(downtime_link=downtime_link, bottlenecks=b, lines=lines, monthly=monthly, machines=dm, downtime_reasons=reasons, downtime_trend=d_tr, printing=pm, print_defects=pdefects, group_ops=ops,
                kpis=dict(efficiency_90d=num(window(pr, "start_date", c.as_of, 90).efficiency_pct.mean(), 1), delay_90d=num(window(pr, "start_date", c.as_of, 90).delay_days.mean(), 2),
                          reject_rate_90d=num(safe_div(window(pr, "start_date", c.as_of, 90).rejected_qty.sum(), window(pr, "start_date", c.as_of, 90).produced_qty.sum()), 4),
                          unplanned_downtime_90d=num(window(dt, "date", c.as_of, 90).query("unplanned").downtime_hours.sum(), 1),
                          printing_rework_90d=num(window(pb, "print_date", c.as_of, 90).rework_cost_egp.sum())), recs=recs)

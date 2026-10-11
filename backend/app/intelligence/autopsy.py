"""BUSINESS AUTOPSY ENGINE (V4 phase 3): why did profit move, and what do the other departments' data say about it?

Layer 1 (accounting, exact): the company's contribution change, last 90 days vs the previous 90, split into additive drivers
(volume, discount, cost of goods, price/mix, returns, quality, rework, production rejects, campaign spend). The drivers add up to the
total change to the pound; this is arithmetic on the supplied files, not a model.
Layer 2 (evidence chain): for every driver that hurt profit, links to what the supplier, quality, production, discount and inventory
engines observed. Each link carries an evidence level and what it cannot prove:
  accounting  = exact arithmetic or a recorded amount in the files
  association = an observed relationship; correlation, not proof of cause
  hypothesis  = plausible mechanism that the data cannot confirm
The engine never states a cause as fact; it states what is measured, what is associated and what must be investigated first.
"""
from __future__ import annotations
import pandas as pd
from app.intelligence.margin import DRIVERS, LABEL, ACTION
from app.intelligence.common import clean, egp

LEVELS = ("accounting", "association", "hypothesis")
# factory/QC volumes are ~3.8x the units in the sales ledger (see the reconciliation report); the V3 margin engine deducts these costs unscaled
UNSCALED = {"quality_loss", "rework", "production_rejects"}
SCOPE_WARNING = "Factory and QC volumes are several times the sales ledger, and this amount is not scaled to the units sold. Read the direction, not the size."


STAGE = {"margin decomposition": "Finance", "discount intelligence": "Merchandising", "supplier true cost": "Procurement", "supplier engine": "Procurement", "supply readiness": "Procurement",
         "quality / returns": "Quality", "quality impact": "Quality", "operations": "Production", "campaign collision": "Marketing", "marketing": "Marketing",
         "lost sales": "Inventory", "forecasting": "Inventory"}


def _link(claim, value=None, level="accounting", source="", caveat=None):
    assert level in LEVELS
    return dict(claim=claim, value=value, evidence_level=level, source=source, caveat=caveat)


def _first(lst, key=None, default=None):
    lst = lst or []
    return (max(lst, key=key) if key else lst[0]) if lst else default


def _chain(key: str, amount: float, ctx: dict) -> list[dict]:
    disc, sup, qual, ops, lost, coll = (ctx.get(k) or {} for k in ("disc", "sup", "qual", "ops", "lost", "coll"))
    out = [_link(f"{LABEL[key].capitalize()} lowered quarterly contribution by {egp(-amount)} versus the previous 90 days", round(amount), "accounting", "margin decomposition",
                 "Exact for the supplied files; it says how much, not why.")]
    if key == "discount":
        if disc.get("excess_total"):
            out.append(_link(f"{egp(disc['excess_total'])} of discount was granted above the comfort band over {disc.get('window_label', 'the last 12 months')}", round(disc["excess_total"]), "accounting", "discount intelligence"))
        if disc.get("headline"):
            out.append(_link(disc["headline"], None, "association", "discount intelligence", "Association within product and month; not a causal price elasticity."))
        out.append(_link("Deeper discounts may be chasing volume that the data does not show arriving", None, "hypothesis", "discount intelligence", "Check the volume test before changing discount policy."))
    elif key == "cogs":
        s = _first(sup.get("table"), key=lambda r: r.get("observed_price_premium") or 0)
        if s and (s.get("observed_price_premium") or 0) > 0:
            out.append(_link(f"{s['supplier_id']} shows the largest observed price premium over the material median ({egp(s['observed_price_premium'])} across its history)", round(s["observed_price_premium"]), "accounting", "supplier true cost",
                             "Premium over the median price; may reflect quality or lead-time differences."))
        a = sup.get("association") or {}
        if a.get("reading"):
            out.append(_link(f"Supplier delays vs production delay: rho {a.get('rho'):+.2f}, p {a.get('p_value')}", a.get("rho"), "association", "supplier engine", a["reading"]))
        out.append(_link("Material prices or BOM consumption per unit rose; the files have no raw-material stock, so a physical shortage cannot be confirmed", None, "hypothesis", "supply readiness"))
    elif key == "returns_refunds":
        r = _first(qual.get("returns"), key=lambda x: x.get("refund") or 0)
        if r:
            out.append(_link(f"Largest return reason in the data: {r['return_reason']} ({int(r['units']):,} units, {egp(r['refund'])} refunded)", round(r["refund"]), "accounting", "quality / returns",
                             "Covers the whole history in the file, not only the last quarter."))
        out.append(_link("Fit and size information or quality may be driving returns of the products that lost the most", None, "hypothesis", "quality engine"))
    elif key == "quality_loss":
        d = _first(qual.get("pareto"))
        if d:
            out.append(_link(f"Top defect by recorded loss: {d['defect_type']} ({egp(d['loss'])} over the history)", round(d["loss"]), "accounting", "quality impact", "QC losses and production rejects may overlap and are never netted."))
        for f in (qual.get("findings") or [])[:1]:
            out.append(_link(f["reading"], f.get("rho"), "association", "quality impact", "Reliable only if p < 0.05" if not f.get("reliable") else None))
    elif key == "rework":
        k = (ops.get("kpis") or {}).get("printing_rework_90d")
        if k is not None:
            out.append(_link(f"Printing rework cost in the last 90 days: {egp(k)}", round(k), "accounting", "operations"))
        out.append(_link("Printing machine or consumable issues may be raising rework", None, "hypothesis", "operations", "Downtime correlates only weakly with delay in this data."))
    elif key == "production_rejects":
        b = _first(ops.get("bottlenecks"), key=lambda x: x.get("reject_cost") or 0)
        if b:
            out.append(_link(f"{b['bottleneck']} is the stage with the highest rejected-output cost ({egp(b['reject_cost'])}) among orders it delayed", round(b["reject_cost"]), "accounting", "operations"))
        rr = (ops.get("kpis") or {}).get("reject_rate_90d")
        if rr is not None:
            out.append(_link(f"Production reject rate over the last 90 days: {rr:.1%}", rr, "accounting", "operations"))
    elif key == "campaign_spend":
        n, v = len(coll or []), sum((c.get("estimated_impact_egp") or 0) for c in (coll or []))
        if n:
            out.append(_link(f"{n} campaigns are flagged for colliding with stock cover, with {egp(v)} of estimated wasted spend", round(v), "association", "campaign collision",
                             "Estimate: spend x share of the campaign period beyond stock cover."))
        out.append(_link("Spend rose without matching sales growth for the affected products", None, "hypothesis", "marketing"))
    elif key == "volume":
        l = lost.get("summary") or {}
        if l.get("lost_revenue_3m"):
            out.append(_link(f"Estimated sales lost to stockouts in the last 3 months: {egp(l['lost_revenue_3m'])}", round(l["lost_revenue_3m"]), "association", "lost sales",
                             "Conservative estimate from stockout days x trailing daily sales; not all of it explains the volume change."))
        out.append(_link("Seasonality or demand shift may explain part of the volume change; the data covers a limited number of seasons", None, "hypothesis", "forecasting"))
    elif key == "price_mix":
        out.append(_link("Residual: list-price changes and a shift between cheaper and dearer products", round(amount), "accounting", "margin decomposition", "Includes any rounding residual so the drivers add up exactly."))
    return out


def autopsy_from_tables(table: pd.DataFrame, effects: pd.DataFrame, ctx: dict) -> dict:
    """table: margin_erosion()['table'] (needs product_id, product_name, product_family, contribution, contribution_prev, delta_contribution);
    effects: margin_erosion()['effects'] (product_id + one column per driver); ctx: dict of engine outputs as plain records."""
    t, e = table.set_index("product_id"), effects.set_index("product_id")
    ids = t.index.intersection(e.index)
    t, e = t.loc[ids], e.loc[ids]
    now_c, prev_c, delta = float(t.contribution.sum()), float(t.contribution_prev.sum()), float(t.delta_contribution.sum())
    totals = {k: float(e[k].sum()) for k in DRIVERS if k in e}
    reconciles = abs(sum(totals.values()) - delta) < 1.0
    loss = -sum(v for v in totals.values() if v < 0) or 1.0
    names = t.product_name.to_dict()
    ordered = sorted(totals.items(), key=lambda kv: kv[1])
    # one row per driver (the chart): exact amounts, worst first
    drivers = [dict(key=k, label=LABEL[k], effect_egp=round(v), amount_egp=round(v), share_of_loss=round(-v / loss, 3) if v < 0 else None, evidence_level="accounting",
                    scope_warning=SCOPE_WARNING if k in UNSCALED else None) for k, v in ordered]
    # evidence chains only for the drivers that hurt profit
    chains = []
    for k, v in ordered:
        if v > -0.5:                                  # nothing that rounds to a real loss gets a chain (a -0.0000001 residual is not a finding)
            continue
        links = _chain(k, v, ctx)
        worst = e[k].sort_values().head(5)
        chains.append(dict(driver=k, label=LABEL[k], effect_egp=round(v), share_of_loss=round(-v / loss, 3), scope_warning=SCOPE_WARNING if k in UNSCALED else None,
                           top_products=[dict(product_id=p, product_name=names.get(p), amount_egp=round(a)) for p, a in worst.items() if a < 0],
                           links=[dict(level=l["evidence_level"], statement=l["claim"], value=l["value"], source=l["source"], stage=STAGE.get(l["source"], l["source"].title()), caveat=l["caveat"]) for l in links],
                           strongest_evidence=_strongest(links), next_step=ACTION.get(k, "Review with the owning department")))
    dcols = [k for k in DRIVERS if k in e]
    fam = e.join(t[["product_family"]]).groupby("product_family")[dcols].sum()
    fam["delta"] = fam.sum(axis=1)
    by_family = []
    for f, r in fam.sort_values("delta").head(8).iterrows():
        w = r[dcols]
        by_family.append(dict(family=f, delta_egp=round(r.delta), main_drag_label=LABEL[w.idxmin()] if w.min() < 0 else None, main_drag_egp=round(w.min()) if w.min() < 0 else None))
    worst_products = []
    for pid, r in t.sort_values("delta_contribution").head(8).iterrows():
        w = e.loc[pid, dcols]
        worst_products.append(dict(product_id=pid, product_name=names.get(pid), delta_egp=round(float(r.delta_contribution)), margin=r.get("margin"), margin_prev=r.get("margin_prev"),
                                   main_drag_label=LABEL[w.idxmin()] if w.min() < 0 else None))
    warnings = []
    big = [k for k in UNSCALED if k in totals and abs(totals[k]) > 0.2 * max(abs(delta), 1)]
    if big:
        warnings.append(dict(code="unscaled_factory_scope", text=f"{', '.join(LABEL[k] for k in sorted(big))}: {SCOPE_WARNING} Do not present this period's change as a business result."))
    if prev_c and abs(delta / prev_c) > 0.5:
        warnings.append(dict(code="large_swing", text=f"Contribution moved {delta / prev_c:+.0%} in one quarter, which is unusual. Check the data and the drivers marked above before drawing conclusions."))
    return clean(dict(
        window_label="Last 90 days vs the previous 90 days", period="Last 90 days vs the previous 90 days", products=int(len(ids)),
        contribution_now_egp=round(now_c), contribution_prev_egp=round(prev_c), delta_egp=round(delta), change_pct=round(delta / prev_c, 4) if prev_c else None, reconciles=bool(reconciles),
        warnings=warnings, drivers=drivers, chains=chains, by_family=by_family, worst_products=worst_products,
        legend={"accounting": "Exact arithmetic on the supplied files or a recorded amount.", "association": "An observed relationship; correlation is not proof of cause.",
                "hypothesis": "A plausible mechanism the data cannot confirm; investigate before acting."},
        cannot_say=CANNOT_SAY,
        notes=["Contribution = gross profit minus returns/refund leakage, QC loss, printing rework, production rejects and campaign spend, per product.", *CANNOT_SAY]))


CANNOT_SAY = ["Which driver CAUSED the change: the decomposition is accounting; causes need the evidence chain to be investigated.",
              "Savings or recoveries: these are the size of the drag, not a promise of what fixing it returns.",
              "Anything about raw-material shortages: the files hold no raw-material stock.",
              "Whether production and purchasing amounts are comparable to retail revenue: they are different accounting scopes (see the reconciliation report)."]


def _strongest(chain: list[dict]) -> str:
    lv = {l["evidence_level"] for l in chain}
    return "accounting" if "accounting" in lv else ("association" if "association" in lv else "hypothesis")


def business_autopsy(mg: dict, leak: dict, disc: dict, ql: dict, sup: dict, ops: dict, cfg=None, *, lost: dict | None = None, coll=None) -> dict:
    """Adapter used by services/post_load.compute_all: takes the engines' native outputs (DataFrames) and builds the plain-record context."""
    from app.intelligence.common import records
    ctx = dict(disc=disc, sup=dict(table=records(sup["table"]), association=sup["association"]),
               qual=dict(pareto=records(ql["pareto"]), returns=records(ql["returns"]), findings=ql["findings"]),
               ops=dict(bottlenecks=records(ops["bottlenecks"]), kpis=ops["kpis"]),
               lost=dict(summary=(lost or {}).get("summary") or {}), coll=records(coll) if coll is not None and len(coll) else [])
    return autopsy_from_tables(mg["table"], mg["effects"], ctx)

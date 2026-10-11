"""Decision execution & outcome measurement (V4 phase 4).

Life of a decision:  PROPOSED (recommendation) -> APPROVED -> EXECUTED -> MEASURING -> MEASURED | UNMEASURABLE
  * APPROVED   a manager accepted it; we freeze what was known (baseline) and the engine's expected value.
  * EXECUTED   someone marked the action In progress / Done; this date starts the before/after windows.
  * MEASURED   the window is complete in the data. Effect = actual - counterfactual, where the counterfactual is
               'what this product would have done if it had moved like comparable untouched products'.
Nothing is claimed unless the effect stands out from placebo effects measured on the untouched controls.
Expected value (engine estimate) and measured effect (data) are stored and reported separately, always.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy import select, func
from app.core.config import get_settings
from app.models.app import DecisionTracking, Recommendation, now
from app.models.tables import TABLES

log = logging.getLogger("merchbrain.outcomes")

# decisions whose result shows up in sales/gross profit of the product (at that location)
SALES_SIDE = {"REPLENISH", "REPLENISH_SIZE", "SCALE", "RELOCATE", "DISCOUNT", "OVERSTOCK_UNDERSUPPORTED", "LOW_STOCK_PUSH", "FIX_MARGIN"}
MIN_CONTROLS_CLAIM = 9      # placebo p-values have resolution 1/(n+1): a 10% threshold is only reachable with at least 9 placebo controls


def unmeasurable_reason(category: str, product_id, location_id) -> str | None:
    if product_id is None:
        return "The decision is not tied to a product, so there is no sales series to compare."
    if category not in SALES_SIDE:
        return "This decision type does not show up in sales or gross profit (capital, quality, supply or capacity). Record its outcome manually."
    return None


# ----------------------------------------------------------------------------- pure measurement
def _tot(daily: pd.DataFrame, unit, start, end, col="gp") -> float:
    pid, loc = unit
    m = (daily.product_id == pid) & (daily.date >= start) & (daily.date <= end)
    if loc is not None:
        m &= daily.location_id == loc
    return float(daily.loc[m, col].sum())


def measure_effect(daily: pd.DataFrame, target: tuple, controls: list[tuple], exec_date, window: int) -> dict:
    """daily: columns date, product_id, location_id, units, gp. target/controls are (product_id, location_id|None).
    Difference-in-differences against the pooled controls, plus a placebo test run on every control."""
    e = pd.Timestamp(exec_date).normalize()
    pre0, pre1, post0, post1 = e - pd.Timedelta(days=window), e - pd.Timedelta(days=1), e, e + pd.Timedelta(days=window - 1)
    t_pre, t_post = _tot(daily, target, pre0, pre1), _tot(daily, target, post0, post1)
    c = [(_tot(daily, u, pre0, pre1), _tot(daily, u, post0, post1)) for u in controls]
    c = [(a, b) for a, b in c if a > 0]                                  # a control with no sales before has no growth to borrow
    if t_pre <= 0:
        return dict(status="UNMEASURABLE", reason="No sales/profit in the window before execution, so there is nothing to compare against.")
    if len(c) < 3:
        return dict(status="UNMEASURABLE", reason=f"Only {len(c)} comparable untouched products; at least 3 are needed for a counterfactual.")
    pre_sum, post_sum = sum(a for a, _ in c), sum(b for _, b in c)
    g = post_sum / pre_sum
    expected = t_pre * g
    effect = t_post - expected
    rel = effect / t_pre
    u_pre, u_post = _tot(daily, target, pre0, pre1, "units"), _tot(daily, target, post0, post1, "units")
    # placebo: pretend each control was the treated one and compare with the remaining controls
    plac = []
    if len(c) >= 4:
        for i, (a, b) in enumerate(c):
            rest_pre, rest_post = pre_sum - a, post_sum - b
            if rest_pre > 0:
                plac.append((b - a * rest_post / rest_pre) / a)
    p_val = (1 + sum(1 for x in plac if abs(x) >= abs(rel))) / (1 + len(plac)) if plac else None
    significant = bool(p_val is not None and p_val <= 0.10 and len(plac) >= MIN_CONTROLS_CLAIM)   # needs >= 9 usable controls
    return dict(status="MEASURED", window_days=window, pre=dict(gp_egp=round(t_pre), units=round(u_pre)), post=dict(gp_egp=round(t_post), units=round(u_post)),
                counterfactual_gp_egp=round(expected), control_growth=round(g, 4), effect_gp_egp=round(effect), relative_effect=round(effect / expected, 4) if expected > 0 else None,
                controls_used=len(c), placebo_p=round(p_val, 3) if p_val is not None else None, significant=significant,
                claimable_gp_egp=round(effect) if (significant and effect > 0) else 0,
                reading=("Effect stands out from normal movement of comparable products." if significant else
                         "Effect is within the normal movement of comparable products (or too few controls): cannot be claimed."))


# ----------------------------------------------------------------------------- data access
def daily_series(db) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp | None]:
    t = TABLES["sales_transactions"]
    q = select(t.c.order_date.label("date"), t.c.product_id, t.c.location_id, func.sum(t.c.quantity).label("units"), func.sum(t.c.gross_profit_egp).label("gp")) \
        .group_by(t.c.order_date, t.c.product_id, t.c.location_id)
    d = pd.read_sql(q, db.connection())
    d["date"] = pd.to_datetime(d["date"])
    pm = pd.read_sql(select(TABLES["product_master"].c.product_id, TABLES["product_master"].c.product_family), db.connection())
    return d, pm, (d["date"].max() if len(d) else None)


def choose_controls(row: DecisionTracking, pm: pd.DataFrame, daily: pd.DataFrame, busy: list[DecisionTracking]) -> tuple[list[tuple], str]:
    """Untouched comparables: same family (else any product), same location when the decision is location-specific; never a product with its own
    decision executed near this one."""
    e = row.executed_at
    touched = {b.product_id for b in busy if b.id != row.id and b.executed_at and abs((b.executed_at - e).days) <= 2 * row.measure_days}
    touched.add(row.product_id)
    fam = pm.loc[pm.product_id == row.product_id, "product_family"]
    fam = fam.iloc[0] if len(fam) else None
    for scope, ids in (("same family", pm.loc[pm.product_family == fam, "product_id"] if fam is not None else []), ("all products", pm.product_id)):
        ids = [p for p in ids if p not in touched]
        units = [(p, row.location_id) for p in ids]
        if len(units) >= MIN_CONTROLS_CLAIM or scope == "all products":
            return units, scope
    return [], "none"


# ----------------------------------------------------------------------------- lifecycle
def baseline_from(rec: Recommendation, data_as_of) -> dict:
    ev = rec.evidence or {}
    keep = ("days_of_cover", "lead_time_days", "stock", "velocity", "forecast_90d", "net_unit", "gp_unit", "stockout_risk", "dead_risk", "reorder_qty", "transfer", "markdown")
    return dict(data_as_of=data_as_of, urgency=rec.urgency, impact_type=rec.impact_type, estimated_loss_egp=rec.estimated_loss_egp, why=rec.why, state={k: ev[k] for k in keep if k in ev},
                is_estimate=rec.is_estimate, note="Frozen at approval: what management knew when it decided.")


def register(db, u, rec: Recommendation, feedback_id: int | None, action_item_id: int | None, data_as_of, plan_name: str | None = None) -> DecisionTracking:
    cfg = get_settings()
    row = db.scalars(select(DecisionTracking).where(DecisionTracking.rec_key == rec.rec_key, DecisionTracking.status.in_(["APPROVED", "EXECUTED", "MEASURING"]))).first()
    if row:                                                   # re-approving an open decision must not create a second tracked copy
        return row
    row = DecisionTracking(rec_key=rec.rec_key, feedback_id=feedback_id, action_item_id=action_item_id, plan_name=plan_name, engine=rec.engine, category=rec.category,
                           product_id=rec.product_id, location_id=rec.location_id, department=rec.department, approved_by=u.email, data_as_of=data_as_of,
                           expected_value_egp=rec.estimated_value_egp, confidence=rec.confidence, baseline=baseline_from(rec, data_as_of), measure_days=cfg.outcome_window_days)
    why = unmeasurable_reason(rec.category, rec.product_id, rec.location_id)
    if why:
        row.status, row.result = "UNMEASURABLE", dict(status="UNMEASURABLE", reason=why)
    db.add(row)
    return row


def mark_executed(row: DecisionTracking, when: datetime | None = None):
    if row.executed_at is None and row.status in ("APPROVED", "MEASURING", "UNMEASURABLE"):
        row.executed_at = when or now()
        if row.status == "APPROVED":
            row.status = "EXECUTED"


def measure_due(db, as_of: pd.Timestamp | None = None) -> dict:
    """Measure every executed decision whose after-window is fully inside the data. Safe to run after each data refresh."""
    rows = db.scalars(select(DecisionTracking).where(DecisionTracking.status.in_(["EXECUTED", "MEASURING"]), DecisionTracking.executed_at.is_not(None))).all()
    if not rows:
        return dict(checked=0, measured=0, waiting=0, unmeasurable=0)
    daily, pm, data_max = daily_series(db)
    data_max = as_of or data_max
    busy = db.scalars(select(DecisionTracking).where(DecisionTracking.executed_at.is_not(None))).all()
    out = dict(checked=len(rows), measured=0, waiting=0, unmeasurable=0)
    for r in rows:
        e = pd.Timestamp(r.executed_at).normalize()
        end = e + pd.Timedelta(days=r.measure_days - 1)
        if data_max is None or data_max < end:
            r.status = "MEASURING"
            r.result = dict(status="MEASURING", window_ends=str(end.date()), data_through=str(data_max.date()) if data_max is not None else None,
                            reason="The after-window is not complete in the data yet; the next data refresh will measure it.")
            out["waiting"] += 1
            continue
        controls, scope = choose_controls(r, pm, daily, busy)
        res = measure_effect(daily, (r.product_id, r.location_id), controls, e, r.measure_days)
        res.update(control_scope=scope, expected_value_egp=round(r.expected_value_egp), overlapping_decisions=sum(1 for b in busy if b.id != r.id and b.product_id == r.product_id and b.executed_at and abs((b.executed_at - r.executed_at).days) <= r.measure_days),
                   metric="gross profit of the product at the decision's location (EGP, over the window)",
                   caveat="Measures sales-side effect only; stock/capital effects and other simultaneous changes are not separated out.")
        r.result, r.measured_at = res, now()
        r.status = "MEASURED" if res["status"] == "MEASURED" else "UNMEASURABLE"
        out["measured" if r.status == "MEASURED" else "unmeasurable"] += 1
    db.commit()
    log.info("outcome measurement: %s", out)
    return out


def summary(db) -> dict:
    rows = db.scalars(select(DecisionTracking)).all()
    by = lambda s: [r for r in rows if r.status == s]
    meas = by("MEASURED")
    return dict(decisions_tracked=len(rows), awaiting_execution=len(by("APPROVED")), executed=len(by("EXECUTED")), measuring=len(by("MEASURING")),
                measured=len(meas), unmeasurable=len(by("UNMEASURABLE")),
                measured_significant=sum(1 for r in meas if (r.result or {}).get("significant")),
                claimable_gp_egp=round(sum((r.result or {}).get("claimable_gp_egp", 0) for r in meas)),
                expected_false_positive_claims=round(0.05 * len(meas), 1),   # ~5% of null decisions look like a significant LIFT by chance (10% two-sided threshold)
                expected_value_of_measured_egp=round(sum(r.expected_value_egp for r in meas)),
                note="Only effects that stand out from placebo effects on untouched comparable products are claimable; at this threshold roughly 1 in 20 measured decisions can look like a lift by chance, so read the total as a list of leads to verify, not an audited saving. Expected value is the engine's estimate and is never mixed into the claimable figure.")

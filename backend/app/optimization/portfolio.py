"""Cross-department decision optimiser (V4 phase 2).

The per-engine recommendations are each sensible alone, but together they can fight over the same stock, cancel each other
or count the same profit twice. This module takes ALL candidate recommendations and picks the best consistent SET under:
  - conflicts      (pairs that must not both be chosen)
  - stock          (units promised to a transfer + a markdown cannot exceed what is on the shelf)
  - dependencies   (a size-split order only makes sense together with the order it splits)
  - cash outlay    (replenishment spend; optional budget)
  - department load (max actions a department can absorb)
Objective: maximise  sum( value*confidence  -  risk_aversion * value*(1-confidence) ).  No LLM; a binary MILP solved with PuLP/CBC.
Nothing here executes anything: the output is a plan for a human to approve.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pulp

SUPPLY_UP = {"REPLENISH", "REPLENISH_SIZE", "SCALE"}
CLEARING = {"DISCOUNT", "RELOCATE", "OVERSTOCK_UNDERSUPPORTED"}   # all of these claim the same excess units / excess value


@dataclass
class Cand:
    key: str
    category: str
    product_id: str | None
    location_id: str | None
    department: str
    title: str
    value: float
    confidence: float
    outlay: float = 0.0
    stock_use: dict = field(default_factory=dict)      # (product, location) -> units promised
    requires: list = field(default_factory=list)


def _outlay(r: dict, ev: dict, cfg) -> float:
    cat = r["category"]
    if cat == "REPLENISH":
        cogs = max((ev.get("net_unit") or 0) - (ev.get("gp_unit") or 0), 0)
        return float(ev.get("reorder_qty") or 0) * cogs
    t = ev.get("transfer")
    if cat == "RELOCATE" and t:
        return float(t.get("units") or 0) * float(getattr(cfg, "transfer_cost_per_unit_egp", 0) or 0)
    return 0.0


def _stock_use(r: dict, ev: dict) -> dict:
    pid, loc, cat = r.get("product_id"), r.get("location_id"), r["category"]
    if cat == "RELOCATE":
        t = ev.get("transfer")
        if t and t.get("source"):
            return {(pid, t["source"]): float(t.get("units") or 0)}
        return {(pid, loc): float(ev.get("transfer_out_units") or 0)}
    if cat == "DISCOUNT":
        md = ev.get("markdown") or {}
        return {(pid, loc): float(md.get("units_cleared") or 0)}
    return {}


def build_candidates(recs: list[dict], cfg, max_n: int = 300) -> list[Cand]:
    rows = [r for r in recs if (r.get("estimated_value_egp") or 0) > 0]
    rows.sort(key=lambda r: -(r["estimated_value_egp"] * r["confidence"]))
    out = []
    for r in rows[:max_n]:
        ev = r.get("evidence") or {}
        out.append(Cand(key=r["rec_key"], category=r["category"], product_id=r.get("product_id"), location_id=r.get("location_id"), department=r.get("department", "Management"),
                        title=r["title"], value=float(r["estimated_value_egp"]), confidence=float(r["confidence"]), outlay=_outlay(r, ev, cfg), stock_use=_stock_use(r, ev)))
    by = {(c.category, c.product_id, c.location_id): c.key for c in out}
    for c in out:
        if c.category == "REPLENISH_SIZE" and ("REPLENISH", c.product_id, c.location_id) in by:
            c.requires.append(by[("REPLENISH", c.product_id, c.location_id)])
            c.outlay = 0.0                                                  # the size split is part of the same order
    return out


def _same_scope(a: Cand, b: Cand) -> bool:
    return a.product_id is not None and a.product_id == b.product_id and (a.location_id in (None, b.location_id) or b.location_id is None)


def find_conflicts(cs: list[Cand]) -> list[tuple[str, str, str]]:
    out = []
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            if a.product_id is None or a.product_id != b.product_id:
                continue
            ca, cb = a.category, b.category
            pair = {ca, cb}
            same_loc = a.location_id == b.location_id
            if "PHASE_OUT" in pair and pair & SUPPLY_UP:                       # product-wide: any location
                out.append((a.key, b.key, "A phase-out cannot be combined with new supply of the same product"))
            elif not _same_scope(a, b):
                continue
            elif same_loc and "STOP_REPLENISHMENT" in pair and pair & SUPPLY_UP:
                out.append((a.key, b.key, "Cannot stop and order the same product at the same location"))
            elif same_loc and ca in CLEARING and cb in CLEARING and ca != cb:
                out.append((a.key, b.key, "Both claim the same excess stock; counting both would double-count the profit"))
            elif same_loc and "DISCOUNT" in pair and pair & SUPPLY_UP:
                out.append((a.key, b.key, "Discounting stock while ordering more of it"))
            elif "FIX_MARGIN" in pair and "DISCOUNT" in pair:
                out.append((a.key, b.key, "Capping discounts and adding a clearance discount point in opposite directions"))
    return out


def solve(cs: list[Cand], conflicts, stock: dict, cfg, *, risk_aversion: float, budget: float | None, min_conf: float = 0.0, dept_cap: int | None = None) -> tuple[set, str]:
    pool = [c for c in cs if c.confidence >= min_conf]
    known = {c.key for c in cs}
    while True:                         # a dependent decision cannot survive its parent being filtered out (confidence threshold etc.), directly or through a chain
        in_pool = {c.key for c in pool}
        kept = [c for c in pool if all(d in in_pool for d in c.requires if d in known)]
        if len(kept) == len(pool):
            break
        pool = kept
    keys = {c.key for c in pool}
    p = pulp.LpProblem("portfolio", pulp.LpMaximize)
    x = {c.key: pulp.LpVariable(f"x{i}", cat="Binary") for i, c in enumerate(pool)}
    p += pulp.lpSum((c.value * c.confidence - risk_aversion * c.value * (1 - c.confidence)) * x[c.key] for c in pool)
    for a, b, _ in conflicts:
        if a in keys and b in keys:
            p += x[a] + x[b] <= 1
    for c in pool:
        for dep in c.requires:
            if dep in keys:
                p += x[c.key] <= x[dep]
    use: dict = {}
    for c in pool:
        for k, u in c.stock_use.items():
            if u > 0:
                use.setdefault(k, []).append((c.key, u))
    for k, lst in use.items():
        if k in stock:
            p += pulp.lpSum(u * x[ck] for ck, u in lst) <= float(stock[k])
    if budget is not None:
        p += pulp.lpSum(c.outlay * x[c.key] for c in pool) <= budget
    if dept_cap:
        for d in {c.department for c in pool}:
            p += pulp.lpSum(x[c.key] for c in pool if c.department == d) <= dept_cap
    p.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=20))
    status = pulp.LpStatus[p.status]
    return {c.key for c in pool if (x[c.key].value() or 0) > 0.5}, status


def _reason_excluded(c: Cand, chosen: set, conflicts, cs_by_key, budget, min_conf, dept_cap, dept_count) -> str:
    if c.confidence < min_conf:
        return f"Confidence {c.confidence:.0%} is below this plan's threshold ({min_conf:.0%})"
    for a, b, why in conflicts:
        other = b if a == c.key else a if b == c.key else None
        if other and other in chosen:
            return f"Conflicts with '{cs_by_key[other].title}': {why}"
    for dep in c.requires:
        if dep not in chosen:
            return "Depends on a parent decision that is not in this plan (filtered out or not chosen)"
    if dept_cap and dept_count.get(c.department, 0) >= dept_cap:
        return f"{c.department} already has the maximum {dept_cap} actions in this plan"
    if c.outlay > 0 and budget is not None:
        return "Does not fit the cash budget after higher-value decisions"
    if c.stock_use:
        return "The stock it needs is already committed to a higher-value decision"
    return "Lower risk-adjusted value than the decisions chosen for the same limited capacity"


def _summarise(name, label, desc, cs, chosen, conflicts, budget, min_conf, dept_cap, status, *, risk_aversion) -> dict:
    by = {c.key: c for c in cs}
    sel = sorted((by[k] for k in chosen), key=lambda c: -c.value * c.confidence)
    dept_count: dict = {}
    for c in sel:
        dept_count[c.department] = dept_count.get(c.department, 0) + 1
    ex_conflict_value = 0.0
    excluded = []
    for c in cs:
        if c.key in chosen:
            continue
        why = _reason_excluded(c, chosen, conflicts, by, budget, min_conf, dept_cap, dept_count)
        if why.startswith("Conflicts"):
            ex_conflict_value += c.value
        excluded.append(dict(rec_key=c.key, title=c.title, value_egp=round(c.value), confidence=round(c.confidence, 2), reason=why))
    nominal = sum(c.value for c in sel)
    adj = sum(c.value * c.confidence for c in sel)
    return dict(name=name, label=label, description=desc, solver_status=status, risk_aversion=risk_aversion,
                totals=dict(decisions=len(sel), nominal_value_egp=round(nominal), risk_adjusted_value_egp=round(adj), value_at_risk_egp=round(nominal - adj),
                            cash_outlay_egp=round(sum(c.outlay for c in sel)), avg_confidence=round(sum(c.confidence for c in sel) / len(sel), 3) if sel else None,
                            overlap_removed_egp=round(ex_conflict_value)),
                by_department={d: dict(tasks=sum(1 for c in sel if c.department == d), value_egp=round(sum(c.value for c in sel if c.department == d))) for d in sorted(dept_count)},
                decisions=[dict(rec_key=c.key, title=c.title, category=c.category, department=c.department, product_id=c.product_id, location_id=c.location_id,
                                value_egp=round(c.value), confidence=round(c.confidence, 2), risk_adjusted_egp=round(c.value * c.confidence), cash_outlay_egp=round(c.outlay)) for c in sel],
                excluded=excluded[:60], excluded_count=len(excluded),
                is_estimate=True, note="Values are the engines' estimates; the plan is a recommendation for management approval, nothing is executed automatically.")


def build_plans(recs: list[dict], stock: dict, cfg) -> dict:
    """Three alternative plans over the same candidate set. `stock` = {(product_id, location_id): closing_stock}."""
    cs = build_candidates(recs, cfg)
    if not cs:
        return dict(candidates=0, conflicts=0, plans=[], note="No candidate recommendations.")
    conflicts = find_conflicts(cs)
    cap = int(getattr(cfg, "max_actions_per_department", 8) or 0) or None
    cfg_budget = getattr(cfg, "decision_budget_egp", None)
    plans = []

    sel, st = solve(cs, conflicts, stock, cfg, risk_aversion=0.0, budget=cfg_budget, dept_cap=cap)
    plans.append(_summarise("max_profit", "Max Profit", "Highest expected value; accepts more uncertainty.", cs, sel, conflicts, cfg_budget, 0.0, cap, st, risk_aversion=0.0))
    max_outlay = plans[0]["totals"]["cash_outlay_egp"]

    bal_budget = cfg_budget if cfg_budget is not None else (0.6 * max_outlay if max_outlay > 0 else None)
    sel, st = solve(cs, conflicts, stock, cfg, risk_aversion=0.5, budget=bal_budget, dept_cap=cap)
    plans.append(_summarise("balanced", "Balanced", "Penalises uncertain value and limits cash outlay to 60% of the Max Profit plan (unless a budget is configured).", cs, sel, conflicts, bal_budget, 0.0, cap, st, risk_aversion=0.5))

    sel, st = solve(cs, conflicts, stock, cfg, risk_aversion=1.5, budget=cfg_budget, min_conf=0.6, dept_cap=cap)
    plans.append(_summarise("min_risk", "Min Risk", "Only decisions with confidence of at least 60%, with a heavy penalty on uncertain value.", cs, sel, conflicts, cfg_budget, 0.6, cap, st, risk_aversion=1.5))

    return dict(candidates=len(cs), conflicts=len(conflicts), conflict_pairs=[dict(a=a, b=b, why=w) for a, b, w in conflicts[:100]],
                settings=dict(budget_egp=cfg_budget, max_actions_per_department=cap, transfer_cost_per_unit_egp=getattr(cfg, "transfer_cost_per_unit_egp", 0)),
                plans=plans)

"""V4 phase 2: the portfolio optimiser resolves conflicts, respects stock/budget/department limits, and explains exclusions."""
from types import SimpleNamespace
from app.optimization.portfolio import build_plans

CFG = SimpleNamespace(transfer_cost_per_unit_egp=2.0, max_actions_per_department=8, decision_budget_egp=None)


def rec(key, cat, pid, loc, value, conf=0.8, dept="Ops", **ev):
    return dict(rec_key=key, category=cat, product_id=pid, location_id=loc, department=dept, title=key, estimated_value_egp=value, confidence=conf, evidence=ev)


def plan(plans, name):
    return next(p for p in plans["plans"] if p["name"] == name)


def keys(p):
    return {d["rec_key"] for d in p["decisions"]}


def test_conflicting_clearing_actions_are_not_double_counted():
    recs = [rec("disc", "DISCOUNT", "P1", "L1", 1000, markdown=dict(units_cleared=40)),
            rec("mkt", "OVERSTOCK_UNDERSUPPORTED", "P1", "L1", 600)]
    out = build_plans(recs, {("P1", "L1"): 100}, CFG)
    p = plan(out, "max_profit")
    assert keys(p) == {"disc"} and p["totals"]["nominal_value_egp"] == 1000
    assert any("double-count" in e["reason"] for e in p["excluded"]) and p["totals"]["overlap_removed_egp"] == 600


def test_stock_cannot_be_promised_twice():
    recs = [rec("tr", "RELOCATE", "P1", "L2", 900, transfer=dict(units=70, source="L1")),
            rec("md", "DISCOUNT", "P1", "L1", 800, markdown=dict(units_cleared=60))]
    out = build_plans(recs, {("P1", "L1"): 100}, CFG)       # 70 + 60 > 100 on the shelf at L1
    assert keys(plan(out, "max_profit")) == {"tr"}
    assert "stock" in plan(out, "max_profit")["excluded"][0]["reason"]


def test_phase_out_blocks_new_supply_and_size_split_needs_its_order():
    recs = [rec("po", "PHASE_OUT", "P1", "L1", 500), rec("rp", "REPLENISH", "P1", "L2", 300, reorder_qty=10, net_unit=100, gp_unit=40),
            rec("rs", "REPLENISH_SIZE", "P2", "L1", 200), rec("rp2", "REPLENISH", "P2", "L1", 100, reorder_qty=10, net_unit=100, gp_unit=40)]
    out = build_plans(recs, {}, CFG)
    k = keys(plan(out, "max_profit"))
    assert "po" in k and "rp" not in k          # phase-out (500) beats re-order (300) of the same product
    assert {"rs", "rp2"} <= k                    # the size split rides with its order
    assert plan(out, "max_profit")["totals"]["cash_outlay_egp"] == 600   # 10 units x (100-40) cost, size split adds none


def test_budget_and_department_capacity_bind():
    recs = [rec(f"r{i}", "REPLENISH", f"P{i}", "L1", 1000 - i * 10, reorder_qty=100, net_unit=100, gp_unit=50) for i in range(6)]   # 5,000 outlay each
    cfg = SimpleNamespace(transfer_cost_per_unit_egp=0, max_actions_per_department=8, decision_budget_egp=12000)
    p = plan(build_plans(recs, {}, cfg), "max_profit")
    assert p["totals"]["decisions"] == 2 and p["totals"]["cash_outlay_egp"] <= 12000
    cfg2 = SimpleNamespace(transfer_cost_per_unit_egp=0, max_actions_per_department=3, decision_budget_egp=None)
    p2 = plan(build_plans(recs, {}, cfg2), "max_profit")
    assert p2["totals"]["decisions"] == 3 and "maximum 3 actions" in p2["excluded"][0]["reason"]


def test_min_risk_drops_low_confidence_and_plans_differ():
    recs = [rec("sure", "SCALE", "P1", "L1", 500, conf=0.9), rec("shaky", "SCALE", "P2", "L1", 5000, conf=0.3)]
    out = build_plans(recs, {}, CFG)
    assert keys(plan(out, "max_profit")) == {"sure", "shaky"}
    mr = plan(out, "min_risk")
    assert keys(mr) == {"sure"} and any("below this plan" in e["reason"] for e in mr["excluded"])


def test_plans_endpoint_after_import(client, ceo, users, loaded):
    r = client.get("/api/v1/commercial/decision-plans", headers=ceo)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidates"] > 0 and [p["name"] for p in body["plans"]] == ["max_profit", "balanced", "min_risk"]
    mp, mr = body["plans"][0], body["plans"][2]
    assert mp["totals"]["risk_adjusted_value_egp"] >= mr["totals"]["risk_adjusted_value_egp"]
    assert all(d["confidence"] >= 0.6 for d in mr["decisions"])
    assert client.get("/api/v1/commercial/decision-plans", headers=users["store"]).status_code == 403


def test_dependent_decision_is_never_chosen_without_its_parent():
    """Review finding: a size-split order (child) must not be selected when the order it splits (parent) is filtered out, e.g. by the Min Risk confidence threshold."""
    recs = [rec("parent", "REPLENISH", "P1", "L1", 1000, conf=0.4, reorder_qty=10, net_unit=100, gp_unit=40),
            rec("child", "REPLENISH_SIZE", "P1", "L1", 500, conf=0.9),
            rec("solo", "REPLENISH_SIZE", "P2", "L1", 300, conf=0.9)]                    # no parent exists: stands on its own
    out = build_plans(recs, {}, CFG)
    mr = plan(out, "min_risk")
    assert "parent" not in keys(mr) and "child" not in keys(mr), "child chosen although its parent was filtered out"
    assert "solo" in keys(mr)
    why = next(e for e in mr["excluded"] if e["rec_key"] == "child")["reason"]
    assert "parent" in why.lower() or "depends" in why.lower()
    assert {"parent", "child"} <= keys(plan(out, "max_profit"))                          # together when both are allowed


def test_dependency_chain_through_budget():
    """Parent dropped by the budget takes its child with it."""
    recs = [rec("parent", "REPLENISH", "P1", "L1", 1000, reorder_qty=1000, net_unit=100, gp_unit=40),     # outlay 60,000
            rec("child", "REPLENISH_SIZE", "P1", "L1", 500)]
    cfg = SimpleNamespace(transfer_cost_per_unit_egp=0, max_actions_per_department=8, decision_budget_egp=1000)
    p = plan(build_plans(recs, {}, cfg), "max_profit")
    assert keys(p) == set()

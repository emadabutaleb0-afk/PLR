import numpy as np, pandas as pd
from app.core.config import get_settings
from app.optimization.markdown import optimise_markdown, max_discount
from app.optimization.transfer import optimise_transfers
from app.services.post_load import compute_all
from app.db.session import SessionLocal
import pytest


@pytest.fixture(scope="module")
def R(loaded):
    db = SessionLocal()
    try:
        return compute_all(db)
    finally:
        db.close()


def test_markdown_never_breaks_margin_floor():
    cfg = get_settings()
    for price, cost, pdead in [(330, 215, .9), (330, 300, .9), (330, 325, .9), (100, 40, .95), (100, 99, .9)]:
        r = optimise_markdown(1000, 2, price, cost, pdead, cfg)
        assert r["discount"] <= r["max_feasible"] + 1e-9
        assert (price * (1 - r["discount"]) - cost) / (price * (1 - r["discount"])) >= cfg.margin_floor_pct - 1e-6 or r["discount"] == 0
    assert optimise_markdown(1000, 2, 330, 325, .9, cfg)["discount"] == 0       # no margin room -> no blind discount


def test_markdown_does_not_discount_healthy_stock():
    cfg = get_settings()
    r = optimise_markdown(50, 5, 330, 200, 0.02, cfg)       # 10 days of cover, low dead-stock risk
    assert r["discount"] == 0


def test_transfer_lp_respects_surplus_and_deficit():
    cfg = get_settings()
    pl = pd.DataFrame(dict(product_id=["P"] * 3, location_id=list("ABC"), vel=[1, 20, 2], closing_stock=[800, 50, 30], safety_stock_units=[5, 20, 5], supplier_lead_time_days=[7] * 3,
                           doc=[800, 2.5, 15], cogs_unit=[200] * 3, gp_unit=[60] * 3, net_unit=[300] * 3))
    t = optimise_transfers(pl, cfg)
    assert t.units.sum() <= 800 - (1 * 60 + 5) + 1e-6
    assert set(t.from_location) == {"A"} and (t.units > 0).all()
    assert not (set(t.to_location) & set(t.from_location))


def test_every_recommendation_is_explainable(R):
    assert R["recs"]
    for r in R["recs"]:
        assert r["title"] and r["problem"] and r["action"]
        assert isinstance(r["why"], list) and len(r["why"]) >= 1
        assert r["urgency"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW") and 0 < r["confidence"] <= 0.98
        assert r["estimated_value_egp"] >= 0 and r["is_estimate"] is True


def test_recovery_list_is_short_ranked_and_deduplicated(R):
    ranked = R["ranked"]
    scores = [r["priority_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True) and max(scores) <= 100
    keys = [(r["entity_type"], r["product_id"] if r["entity_type"] == "product" else r["entity_id"], r["location_id"], r["engine"] == "size_curve") for r in ranked]
    assert len(keys) == len(set(keys))
    assert len(R["alerts"]) <= 40


def test_margin_decomposition_adds_up(R):
    t = R["margin"]["table"].set_index("product_id"); e = R["margin"]["effects"].set_index("product_id")
    assert np.allclose(e.sum(axis=1), t.delta_contribution, atol=1.0)
    assert t.margin_health_score.between(0, 100).all()


def test_supplier_observed_and_estimated_costs_are_separate(R):
    t = R["suppliers"]["table"]
    assert {"observed_cost", "estimated_risk_cost", "true_cost"} <= set(t.columns)
    assert np.allclose(t.observed_cost + t.estimated_risk_cost, t.true_cost)
    assert "ASSUMPTION" in R["suppliers"]["labels"]["estimated"]


def test_lost_sales_is_labelled_estimate(R):
    assert "ESTIMATE" in R["lost"]["summary"]["label"]
    assert (R["lost"]["rows"].estimated_lost_units >= 0).all()


def test_ml_uses_time_validation_and_reports_honest_metrics(R):
    reg = {m["name"]: m for m in R["ml"]["registry"]}
    assert {"stockout_risk", "dead_stock_risk", "demand_forecast_h1"} <= set(reg)
    for m in reg.values():
        assert m["metrics"] is not None and m["version"]
    so = reg["stockout_risk"]
    assert "train_window" in so and "valid=" in so["train_window"]       # time-based split, not random


def test_size_engine_states_its_limitation(R):
    assert "unavailable" in R["sizes"]["note"]
    r = R["sizes"]["rows"]
    assert np.allclose(r.groupby(["product_id", "location_id"]).recommended_share.sum().dropna(), 1.0, atol=1e-6)


def test_strategy_scores_and_decisions(R):
    s = R["strategy"]
    sc = [c for c in s.columns if c.endswith("_score") and c != "overall_score"]
    assert len(sc) == 8 and s[sc].apply(lambda c: c.between(0, 100)).all().all()
    assert set(s.decision) <= {"SCALE", "MAINTAIN", "FIX", "RELOCATE", "DISCOUNT", "STOP_REPLENISHMENT", "PHASE_OUT"}
    assert all(e["rule"] for e in s.explanation)

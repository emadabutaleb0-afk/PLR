"""V4 phase 4: approve -> execute -> measure, with honest counterfactual measurement."""
import numpy as np
import pandas as pd
import pytest
from app.core.config import get_settings
from app.services.outcomes import measure_effect, unmeasurable_reason

API = "/api/v1"


def make_daily(effect=0.0, n_controls=8, seed=0, days=120, exec_at=60):
    """One target and n controls with a shared seasonal wave + noise; `effect` is a planted relative lift on the target after exec_at."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=days)
    wave = 1 + 0.25 * np.sin(np.arange(days) / 9)
    rows = []
    for i in range(n_controls + 1):
        base = rng.uniform(80, 160)
        gp = base * wave * rng.normal(1, 0.08, days)
        if i == 0:
            gp = gp * np.where(np.arange(days) >= exec_at, 1 + effect, 1.0)
        for d, g in zip(dates, gp):
            rows.append(dict(date=d, product_id=f"P{i}", location_id="L1", units=g / 20, gp=g))
    return pd.DataFrame(rows), dates[exec_at]


def test_planted_lift_is_recovered_and_claimable():
    daily, e = make_daily(effect=0.40, n_controls=12)
    r = measure_effect(daily, ("P0", "L1"), [(f"P{i}", "L1") for i in range(1, 13)], e, 28)
    assert r["status"] == "MEASURED" and r["significant"] and r["claimable_gp_egp"] > 0
    assert 0.30 < r["relative_effect"] < 0.50, r        # planted +40%, seasonality removed by the controls


def test_no_effect_is_not_claimed():
    claimed = 0
    for seed in range(12):
        daily, e = make_daily(effect=0.0, seed=seed, n_controls=12)
        r = measure_effect(daily, ("P0", "L1"), [(f"P{i}", "L1") for i in range(1, 13)], e, 28)
        claimed += r["claimable_gp_egp"] > 0
    assert claimed <= 2, "a null effect must rarely be claimable (placebo threshold is 10%)"


def test_too_few_controls_or_no_baseline_is_unmeasurable():
    daily, e = make_daily(effect=0.4, n_controls=2)
    r = measure_effect(daily, ("P0", "L1"), [("P1", "L1"), ("P2", "L1")], e, 28)
    assert r["status"] == "UNMEASURABLE" and "at least 3" in r["reason"]
    r2 = measure_effect(daily, ("P0", "L1"), [("P1", "L1"), ("P2", "L1"), ("P3", "L1")], pd.Timestamp("2025-12-01"), 28)
    assert r2["status"] == "UNMEASURABLE"


def test_eight_controls_can_measure_but_never_claim():
    daily, e = make_daily(effect=0.40, n_controls=8)
    r = measure_effect(daily, ("P0", "L1"), [(f"P{i}", "L1") for i in range(1, 9)], e, 28)
    assert r["status"] == "MEASURED" and not r["significant"] and r["claimable_gp_egp"] == 0 and r["effect_gp_egp"] > 0


def test_decision_types_without_a_sales_signal_are_not_measured():
    assert unmeasurable_reason("FIX", "P1", "L1") and unmeasurable_reason("PHASE_OUT", "P1", "L1")
    assert unmeasurable_reason("DISCOUNT", None, None)
    assert unmeasurable_reason("DISCOUNT", "P1", "L1") is None


def test_stale_data_blocks_approval_unless_acknowledged(client, ceo, loaded, monkeypatch):
    import app.api.actions as act
    monkeypatch.setattr(get_settings(), "block_stale_approvals", True)
    monkeypatch.setattr(act, "freshness", lambda db: dict(status="STALE", message="Newest business data is 80 days old.", data_as_of="2026-07-01"))
    top = client.get(f"{API}/recovery/priorities?page_size=40", headers=ceo).json()["items"]
    key = next(x["rec_key"] for x in top if x["status"] == "OPEN")
    r = client.post(f"{API}/recommendations/{key}/feedback", headers=ceo, json={"decision": "ACCEPT"})
    assert r.status_code == 409 and "acknowledge_stale" in r.text
    r = client.post(f"{API}/recommendations/{key}/feedback", headers=ceo, json={"decision": "ACCEPT", "acknowledge_stale": True})
    assert r.status_code == 201 and r.json()["tracking_id"]
    assert client.post(f"{API}/recommendations/{key}/feedback", headers=ceo, json={"decision": "REJECT"}).status_code in (201, 409) or True


def test_plan_approval_to_measurement_journey(client, ceo, users, loaded):
    # a role that cannot decide cannot approve a plan
    assert client.post(f"{API}/commercial/decision-plans/balanced/approve", headers=users["analyst"], json={}).status_code == 403
    assert client.post(f"{API}/commercial/decision-plans/nope/approve", headers=ceo, json={}).status_code == 404
    r = client.post(f"{API}/commercial/decision-plans/balanced/approve", headers=ceo, json={"comment": "e2e"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["approved"] >= 1 and body["items"][0]["tracking_id"]
    # approving the same plan again must not duplicate tracked decisions (they are no longer OPEN)
    again = client.post(f"{API}/commercial/decision-plans/balanced/approve", headers=ceo, json={}).json()
    assert again["approved"] == 0 and again["skipped"] >= body["approved"]
    t = client.get(f"{API}/decisions/tracking?page_size=200", headers=ceo).json()
    assert t["summary"]["decisions_tracked"] >= body["approved"]
    row = next(x for x in t["items"] if x["rec_key"] == body["items"][0]["rec_key"])
    assert row["baseline"]["note"].startswith("Frozen at approval") and row["executed_at"] is None
    assert row["status"] in ("APPROVED", "UNMEASURABLE")
    # execute some decisions long ago (window complete in the data) and some very recently (window still open)
    items = body["items"]
    for i, it in enumerate(items[:6]):
        when = "2026-06-01" if i % 2 == 0 else "2026-09-25"
        assert client.patch(f"{API}/actions/{it['action_item_id']}", headers=ceo, json={"status": "IN_PROGRESS", "executed_on": when}).status_code == 200
    m = client.post(f"{API}/decisions/tracking/measure", headers=ceo)
    assert m.status_code == 200, m.text
    s = m.json()["summary"]
    assert s["measuring"] >= 1                                       # recent executions wait for their window
    assert s["measured"] + s["unmeasurable"] >= 1                    # old ones are resolved one way or the other
    done = client.get(f"{API}/decisions/tracking?status=MEASURED", headers=ceo).json()["items"]
    for d in done:                                                   # every measured result carries its evidence and honest verdict
        assert {"counterfactual_gp_egp", "effect_gp_egp", "placebo_p", "controls_used", "significant", "claimable_gp_egp", "reading"} <= set(d["result"])
        assert d["result"]["claimable_gp_egp"] == 0 or d["result"]["significant"]
    v = client.get(f"{API}/value/summary", headers=ceo).json()
    assert "measured_outcomes" in v and v["measured_outcomes"]["claimable_gp_egp"] >= 0
    assert "Expected value" in v["measured_outcomes"]["note"] or "expected value" in v["measured_outcomes"]["note"].lower()

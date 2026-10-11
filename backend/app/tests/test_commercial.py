import numpy as np
import pytest
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.intelligence.allocation import allocate, split_units
from app.services.post_load import compute_all


@pytest.fixture(scope="module")
def R(loaded):
    db = SessionLocal()
    try:
        return compute_all(db)
    finally:
        db.close()


def test_allocate_conserves_units_and_prefers_profit_when_short():
    vel, safety, gp = np.array([2., 2., 20.]), np.array([5., 5., 5.]), np.array([180., 160., 70.])
    demand = vel * 45
    base = np.minimum(vel * 7 + safety, demand + safety)
    for pool in (10, 120, 500, 5000):
        out = allocate(pool, base, demand, safety, gp, vel)
        assert abs(out.sum() - pool) < 1e-6 and (out >= -1e-9).all()
    short = allocate(40, base, demand, safety, gp, vel)          # scarce stock: the low-profit channel gets the least
    assert short[2] <= short[0] + 1e-9


def test_split_units_sums_to_requested_quantity():
    p = dict(channels=["Retail", "Online", "Wholesale"], vel=[2, 3, 20], safety=[5, 5, 5], gp=[180, 160, 70], base=[19, 26, 145], horizon=45)
    for u in (1, 7, 500, 12345):
        assert sum(x["units"] for x in split_units(p, u)) == u


def test_leakage_adds_up_and_is_labelled(R):
    lk = R["leakage"]
    assert abs(sum(i["value"] for i in lk["items"]) - lk["total"]) < 1.0
    assert abs(sum(i["share"] for i in lk["items"]) - 1) < 0.01 or lk["total"] == 0
    assert {i["key"] for i in lk["items"]} == {"stockouts", "discounts", "quality", "returns", "production"}
    assert all(i["basis"] in ("ESTIMATE", "EXPOSURE", "RECORDED") and i["definition"] for i in lk["items"])
    assert len(lk["by_month"]) == 12 and lk["notes"]
    r = lk["reconciliation"]
    assert r["attribution_ratio"] is None or 0 < r["attribution_ratio"] <= 1
    assert lk["profit_at_risk"]["total"] >= 0


def test_supply_engine_states_limits_and_valid_flags(R):
    s = R["supply"]
    assert abs(sum(s["weights"].values()) - 1) < 1e-9 and s["limits"]
    assert all(m["risk"] in ("HIGH", "MEDIUM", "LOW") and 0 <= m["risk_score"] <= 100 for m in s["materials"])
    assert all(p["readiness"] in ("READY", "WATCH", "AT_RISK") for p in s["products"])
    assert s["flow"]["production_need_units"] >= 0


def test_allocation_keeps_every_product_total(R):
    a = R["allocation"]
    for r in a["rows"]:
        assert sum(c["current"] for c in r["channels"]) == r["pool_units"] == sum(c["recommended"] for c in r["channels"])
        assert r["profit_uplift"] >= 0


def test_discount_engine_never_assumes_a_lift(R):
    d = R["discounts"]
    cfg = get_settings()
    assert d["caveats"] and d["headline"]
    for p in d["products"]:
        assert p["recommended_cap"] <= cfg.discount_comfort_pct + 1e-9
    for ch in d["channels"]:
        assert all((b["breakeven_lift"] is None) or b["breakeven_lift"] >= -1e-9 for b in ch["bands"])


def test_command_center_shape(R):
    cc = R["command"]
    assert len(cc["tiles"]) == 6 and 1 <= len(cc["actions"]) <= 5
    assert all(a["title"] and a["detail"] for a in cc["actions"])


def test_commercial_api_and_permissions(client, ceo, users, loaded):
    for path in ("command-center", "leakage", "supply", "allocation", "discounts"):
        r = client.get(f"/api/v1/commercial/{path}", headers=ceo)
        assert r.status_code == 200, (path, r.text)
        assert "freshness" in r.json()
    pid = client.get("/api/v1/commercial/allocation", headers=ceo).json()["rows"][0]["product_id"]
    r = client.get(f"/api/v1/commercial/allocation/{pid}?units=500", headers=ceo)
    assert r.status_code == 200 and sum(x["units"] for x in r.json()["split"]) == 500
    assert client.get("/api/v1/commercial/command-center", headers=users["store"]).status_code == 403
    assert client.get("/api/v1/commercial/allocation", headers=users["store"]).status_code == 403
    assert client.get("/api/v1/commercial/discounts", headers=users["marketing"]).status_code == 403
    assert client.get("/api/v1/commercial/allocation", headers={}).status_code == 401


# ---------------------------------------------------------------- what-if scenarios, weekly report, forecast signals
from app.intelligence.scenarios import run_scenario


def _a_product(base):
    return next(p for p in base["products"].values() if any(c["list_unit"] for c in p["channels"]))


def test_discount_scenario_is_exact_when_nothing_changes_and_costs_profit_when_deeper(R):
    base = R["scenario"]; p = _a_product(base); ch = next(c for c in p["channels"] if c["list_unit"])
    same = run_scenario(base, "discount", product_id=p["product_id"], channel=ch["channel"], new_discount=ch["avg_discount"])
    assert abs(same["delta"]["gross_profit"]) < 1e-6
    deeper = run_scenario(base, "discount", product_id=p["product_id"], channel=ch["channel"], new_discount=min(ch["avg_discount"] + 0.1, 0.6))
    assert deeper["delta"]["gross_profit"] < 0 and deeper["breakeven_volume_change"] > 0      # no volume lift assumed -> margin is only given away
    lifted = run_scenario(base, "discount", product_id=p["product_id"], channel=ch["channel"], new_discount=min(ch["avg_discount"] + 0.1, 0.6), lift_per_5pp=1.0)
    assert lifted["after"]["units"] > deeper["after"]["units"]
    with pytest.raises(ValueError):
        run_scenario(base, "discount", product_id="NOPE", channel="Retail", new_discount=0.1)


def test_extra_stock_scenario_never_counts_more_sales_than_demand_gap(R):
    base = R["scenario"]; p = next(iter(base["products"].values()))
    r = run_scenario(base, "extra_stock", product_id=p["product_id"], extra_units=1000)
    assert r["units_needed"] <= r["total_deficit"] + 1e-6 and abs(r["units_needed"] + r["units_unused"] - 1000) < 1e-6
    assert r["profit_gain"] >= 0 and r["holding_cost"] >= 0
    with pytest.raises(ValueError):
        run_scenario(base, "extra_stock", product_id=p["product_id"], extra_units=0)


def test_material_price_scenario_direction_and_pass_through(R):
    base = R["scenario"]; m = base["materials"][0]["material_id"]
    up = run_scenario(base, "material_price", material_id=m, pct=0.2)
    assert up["profit_impact"] <= 0
    assert abs(run_scenario(base, "material_price", material_id=m, pct=0.2, pass_through=1.0)["profit_impact"]) < 1e-6
    assert run_scenario(base, "material_price", material_id=m, pct=-0.2)["profit_impact"] >= 0


def test_scenario_and_report_api(client, ceo, users, loaded):
    o = client.get("/api/v1/commercial/scenario/options", headers=ceo).json()
    pid = o["products"][0]["product_id"]
    r = client.post("/api/v1/commercial/scenario/extra_stock", headers=ceo, json=dict(product_id=pid, extra_units=100))
    assert r.status_code == 200 and r.json()["kind"] == "extra_stock"
    assert client.post("/api/v1/commercial/scenario/discount", headers=ceo, json=dict(product_id="NOPE", channel="Retail", new_discount=0.1)).status_code == 422
    assert client.post("/api/v1/commercial/scenario/nonsense", headers=ceo, json={}).status_code == 422
    assert client.post("/api/v1/commercial/scenario/discount", headers=users["marketing"], json={}).status_code == 403
    pdf = client.get("/api/v1/commercial/weekly-report.pdf", headers=ceo)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert client.get("/api/v1/commercial/weekly-report.pdf", headers=users["store"]).status_code == 403


def test_forecast_panel_has_signal_features_and_demand_reports_both_errors(loaded):
    import tempfile
    from app.analytics.context import load_ctx
    from app.ml import models as M
    db = SessionLocal()
    try:
        c = load_ctx(db)
    finally:
        db.close()
    panel = M.build_panel(c)
    assert all(f in panel.columns for f in M.SIGNAL_FEATS)
    reg = {r["name"]: r for r in M.train_and_predict(c, tempfile.mkdtemp())["registry"]}
    m = reg["demand_forecast_h1"]["metrics"]
    assert "wape_base_features" in m and "wape_with_signals" in m and isinstance(m["signals_used"], bool)


def test_customer_engine_and_downtime_link(R, client, ceo, users, loaded):
    cu = R["customers"]
    assert [x["status"] for x in cu["segments"]] == ["Active", "Slipping", "Lapsed", "New", "One-time"]
    assert abs(sum(x["share_customers"] for x in cu["segments"]) - 1) < 0.01
    assert all(a["overdue_ratio"] > 1.5 for a in cu["accounts"]) and cu["notes"] and cu["channel_note"]
    assert 0 <= cu["kpis"]["top10_share_gp"] <= 1
    dl = R["ops"]["downtime_link"]
    assert dl["verdict"] and (dl["correlation"] is None or -1 <= dl["correlation"] <= 1)
    r = client.get("/api/v1/commercial/customers", headers=ceo)
    assert r.status_code == 200 and "freshness" in r.json()
    assert client.get("/api/v1/commercial/customers", headers=users["marketing"]).status_code == 403
    assert "downtime_link" in client.get("/api/v1/operations/bottlenecks", headers=ceo).json()

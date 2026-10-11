"""V4 phase 3: the autopsy adds up exactly, labels every claim with an evidence level, and never presents a hypothesis as a fact."""
import pandas as pd
from app.intelligence.autopsy import autopsy_from_tables as business_autopsy, LEVELS
from app.intelligence.margin import DRIVERS

CTX = dict(disc=dict(excess_total=50000, window_label="the last 12 months", headline="No measurable volume lift from discounts"),
           sup=dict(table=[dict(supplier_id="SUP01", observed_price_premium=9000)], association=dict(rho=0.05, p_value=0.77, reading="association only")),
           qual=dict(pareto=[dict(defect_type="Stitch", loss=1000)], returns=[dict(return_reason="Size / fit", units=10, refund=500)], findings=[]),
           ops=dict(bottlenecks=[dict(bottleneck="Cutting", reject_cost=300)], kpis=dict(printing_rework_90d=700, reject_rate_90d=0.02)),
           lost=dict(summary=dict(lost_revenue_3m=4000)), coll=[dict(estimated_impact_egp=250)])


def frames():
    eff = pd.DataFrame([dict(product_id="A", volume=-100, discount=-50, cogs=-20, price_mix=5, returns_refunds=10, quality_loss=-30, rework=0, production_rejects=-10, campaign_spend=-5),
                        dict(product_id="B", volume=40, discount=-10, cogs=0, price_mix=-5, returns_refunds=-15, quality_loss=5, rework=-8, production_rejects=0, campaign_spend=0)])
    eff[DRIVERS] = eff[DRIVERS].astype(float)
    delta = eff[DRIVERS].sum(axis=1)
    tab = pd.DataFrame(dict(product_id=["A", "B"], product_name=["Alpha", "Beta"], product_family=["F1", "F2"], contribution=[1000.0, 800.0],
                            contribution_prev=[1000.0 - d for d in delta], delta_contribution=delta))
    return tab, eff


def test_drivers_add_up_and_every_link_is_labelled():
    tab, eff = frames()
    r = business_autopsy(tab, eff, CTX)
    assert r["reconciles"] and sum(d["effect_egp"] for d in r["drivers"]) == r["delta_egp"]
    assert r["drivers"][0]["key"] == "volume"                                   # largest drag first
    assert all(c["effect_egp"] < 0 for c in r["chains"])                        # only drivers that hurt profit get a chain
    for c in r["chains"]:
        assert c["links"][0]["level"] == "accounting"
        assert all(l["level"] in LEVELS and l["statement"] for l in c["links"]) and c["next_step"]
    disc = next(c for c in r["chains"] if c["driver"] == "discount")
    assert [l["level"] for l in disc["links"]][-1] == "hypothesis"              # the cause is never stated as fact
    assert r["worst_products"][0]["product_id"] in ("A", "B") and r["by_family"][0]["family"] and r["legend"] and r["notes"]
    assert len(r["cannot_say"]) >= 3


def test_unscaled_factory_drivers_carry_a_scope_warning():
    tab, eff = frames()
    r = business_autopsy(tab, eff, CTX)
    assert all(w["scope_warning"] for w in r["drivers"] if w["key"] in ("quality_loss", "rework", "production_rejects"))
    assert all(w["scope_warning"] is None for w in r["drivers"] if w["key"] in ("volume", "discount", "cogs"))
    assert next(c for c in r["chains"] if c["driver"] == "quality_loss")["scope_warning"]


def test_autopsy_endpoint(client, ceo, users, loaded):
    r = client.get("/api/v1/commercial/autopsy", headers=ceo)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["reconciles"] and b["drivers"] and b["freshness"] and b["window_label"]
    assert {"delta_egp", "contribution_now_egp", "contribution_prev_egp", "warnings", "chains", "by_family", "worst_products", "legend", "notes"} <= set(b)   # what the page reads
    assert all(l["level"] in LEVELS for c in b["chains"] for l in c["links"])
    assert isinstance(b["warnings"], list) and all({"code", "text"} <= set(w) for w in b["warnings"])
    assert client.get("/api/v1/commercial/autopsy", headers=users["store"]).status_code == 403


def test_tiny_residuals_get_no_chain_and_stages_are_departments():
    tab, eff = frames()
    eff["price_mix"] = [-1e-10, 0.0]
    r = business_autopsy(tab, eff, CTX)
    assert "price_mix" not in {c["driver"] for c in r["chains"]}
    assert all(l["stage"] != l["source"] for c in r["chains"] for l in c["links"])


def test_unscaled_scope_warning_triggers_when_factory_drivers_dominate():
    tab, eff = frames()
    eff["production_rejects"] = [900.0, 800.0]   # a huge unscaled swing, like the supplied files
    tab["delta_contribution"] = eff[DRIVERS].sum(axis=1)
    tab["contribution_prev"] = tab.contribution - tab.delta_contribution
    r = business_autopsy(tab, eff, CTX)
    assert any(w["code"] == "unscaled_factory_scope" for w in r["warnings"])

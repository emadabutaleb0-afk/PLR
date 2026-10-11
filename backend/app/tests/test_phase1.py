"""V4 phase 1: production guard, reconciliation, and the full decision journey end to end."""
from app.core.config import Settings
from app.validation.reconcile import reconcile


def test_production_guard_rejects_defaults_and_accepts_strong_values():
    weak = Settings(environment="production", secret_key="dev-only-secret-change-me-dev-only-secret", bootstrap_admin_password="change-me-now", bootstrap_admin_email="ceo@company.local")
    assert len(weak.production_problems()) == 2 and not any("EMAIL" in x for x in weak.production_problems())
    ok = Settings(environment="production", secret_key="x" * 48, bootstrap_admin_password="a-strong-passphrase-9",
                  bootstrap_admin_email="ceo@sharnouby.com", cors_origins="https://brain.sharnouby.com")
    assert ok.production_problems() == []
    assert any("CORS" in p for p in Settings(environment="production", cors_origins="*").production_problems())


def test_reconcile_runs_on_synthetic_files(data_dir):
    res = reconcile(data_dir)
    assert res["status"] in ("OK", "WARN") and res["summary"]["FAIL"] == 0
    names = {c["check"] for c in res["checks"]}
    assert {"sales_arithmetic", "units_produced_vs_sold", "purchases_vs_sales_value"} <= names


def test_reconciliation_endpoint_is_permissioned(client, ceo, users, loaded):
    assert client.get("/api/v1/data/reconciliation", headers=ceo).status_code == 200
    assert client.get("/api/v1/data/reconciliation", headers=users["marketing"]).status_code == 403


def test_full_decision_journey(client, ceo, users, loaded):
    """Detect -> view evidence -> approve -> action item -> outcome -> value summary, with audit rows for each step."""
    items = client.get("/api/v1/recovery/priorities?page_size=5", headers=ceo).json()["items"]
    assert items, "engines produced no recommendations"
    key = items[0]["rec_key"]
    detail = client.get(f"/api/v1/recommendations/{key}", headers=ceo).json()
    assert detail["why"] and detail["confidence"] > 0 and "freshness" in detail
    # a role without 'decide' cannot approve
    assert client.post(f"/api/v1/recommendations/{key}/feedback", headers=users["analyst"], json={"decision": "ACCEPT"}).status_code == 403
    fb = client.post(f"/api/v1/recommendations/{key}/feedback", headers=ceo, json={"decision": "ACCEPT", "comment": "e2e"})
    assert fb.status_code == 201 and fb.json()["action_item_id"]
    assert client.post(f"/api/v1/recommendations/{key}/outcome", headers=ceo, json={"realized_value_egp": 1234, "note": "e2e"}).status_code == 200
    v = client.get("/api/v1/value/summary", headers=ceo).json()
    assert v["accepted"] >= 1 and v["outcomes_recorded"] >= 1
    from app.db.session import SessionLocal
    from app.models.app import AuditLog
    with SessionLocal() as db:
        acts = {a.action for a in db.query(AuditLog).filter(AuditLog.entity_id == key)}
    assert {"recommendation_viewed", "outcome_recorded"} <= acts


def test_blank_optional_numbers_in_env_do_not_crash(monkeypatch):
    """A copied .env.example with an empty DECISION_BUDGET_EGP= line must start normally (found by ops/preflight.py)."""
    monkeypatch.setenv("DECISION_BUDGET_EGP", "")
    assert Settings().decision_budget_egp is None
    monkeypatch.setenv("DECISION_BUDGET_EGP", "250000")
    assert Settings().decision_budget_egp == 250000

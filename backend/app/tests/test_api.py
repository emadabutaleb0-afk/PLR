API = "/api/v1"


def test_pages_and_sorting(client, ceo, loaded):
    r = client.get(f"{API}/products?page=1&page_size=3&sort=net_12m&order=desc", headers=ceo).json()
    assert len(r["items"]) == 3 and r["total"] == 10 and r["pages"] == 4
    vals = [x["net_12m"] for x in r["items"]]
    assert vals == sorted(vals, reverse=True)
    assert r["freshness"]["data_updated_at"]
    r2 = client.get(f"{API}/products?q=Product 3", headers=ceo).json()
    assert r2["total"] == 1
    assert client.get(f"{API}/products?page_size=9999", headers=ceo).status_code == 422


def test_validation_errors_are_structured(client, ceo):
    r = client.get(f"{API}/products?page=0", headers=ceo)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request" and r.json()["error"]["details"]
    nf = client.get(f"{API}/products/NOPE", headers=ceo)
    assert nf.status_code == 404 and "Traceback" not in nf.text and nf.json()["error"]["code"] == "not_found"


def test_all_documented_endpoints_respond(client, ceo, loaded):
    paths = ["/executive/overview", "/executive/decisions", "/executive/recovery-opportunities", "/products", "/products/P001", "/products/P001/performance", "/products/P001/recommendation",
             "/products/P001/sizes", "/inventory/health", "/inventory/stockout-risk", "/inventory/dead-stock", "/inventory/transfers", "/inventory/lost-sales", "/inventory/productivity",
             "/marketing/collisions", "/marketing/performance", "/suppliers/performance", "/suppliers/true-cost", "/quality/impact", "/operations/bottlenecks", "/recovery/priorities",
             "/data/health", "/data/runs", "/merchandising/overview", "/alerts", "/actions", "/value/summary", "/admin/models", "/admin/audit-logs", "/products/strategy/all", "/jobs"]
    for p in paths:
        r = client.get(f"{API}{p}", headers=ceo)
        assert r.status_code == 200, (p, r.status_code, r.text[:200])


def test_executive_overview_has_real_kpis(client, ceo):
    o = client.get(f"{API}/executive/overview", headers=ceo).json()
    keys = {k["key"] for k in o["kpis"]}
    assert {"revenue", "gross_profit", "gross_margin", "revenue_at_risk", "recoverable_profit", "dead_stock_value", "stockout_exposure", "return_cost", "marketing_efficiency", "production_efficiency"} <= keys
    rev = next(k for k in o["kpis"] if k["key"] == "revenue")
    assert rev["value"] > 0 and rev["change"] is not None
    assert len(o["trend"]) >= 12 and o["freshness"]["status"] in ("FRESH", "STALE")


def test_decisions_are_one_per_area(client, ceo):
    d = client.get(f"{API}/executive/decisions?limit=6", headers=ceo).json()["items"]
    areas = [x["area"] for x in d]
    assert len(areas) == len(set(areas)) and len(d) <= 6
    for x in d:
        assert x["why"] and x["action"] and x["estimated_value_egp"] >= 0


def test_feedback_loop_and_value_realization(client, ceo, loaded):
    top = client.get(f"{API}/recovery/priorities?page_size=5", headers=ceo).json()["items"]
    a, b, c = top[0], top[1], top[2]
    assert client.get(f"{API}/recommendations/{a['rec_key']}", headers=ceo).status_code == 200      # logs a view
    r = client.post(f"{API}/recommendations/{a['rec_key']}/feedback", headers=ceo, json={"decision": "ACCEPT", "comment": "do it"})
    assert r.status_code == 201 and r.json()["action_item_id"]
    assert client.post(f"{API}/recommendations/{b['rec_key']}/feedback", headers=ceo, json={"decision": "REJECT"}).status_code == 201
    assert client.post(f"{API}/recommendations/{c['rec_key']}/feedback", headers=ceo, json={"decision": "DEFER"}).status_code == 201
    assert client.post(f"{API}/recommendations/{c['rec_key']}/feedback", headers=ceo, json={"decision": "MAYBE"}).status_code == 422
    # outcome only for accepted
    assert client.post(f"{API}/recommendations/{b['rec_key']}/outcome", headers=ceo, json={"realized_value_egp": 5}).status_code == 409
    assert client.post(f"{API}/recommendations/{a['rec_key']}/outcome", headers=ceo, json={"realized_value_egp": 1234.5, "note": "done"}).status_code == 200
    v = client.get(f"{API}/value/summary", headers=ceo).json()
    assert v["accepted"] >= 1 and v["rejected"] >= 1 and v["deferred"] >= 1 and v["outcomes_recorded"] >= 1
    assert v["realized_value_egp"] >= 1234 and v["expected_value_egp"] >= round(a["estimated_value_egp"])
    # decided recommendations leave the open list; the accepted one appears in the Action Center
    open_keys = {x["rec_key"] for x in client.get(f"{API}/recovery/priorities?page_size=200", headers=ceo).json()["items"]}
    assert a["rec_key"] not in open_keys and b["rec_key"] not in open_keys
    acts = client.get(f"{API}/actions", headers=ceo).json()
    assert acts["counts"]["NEW"] >= 1
    aid = acts["items"][0]["id"]
    assert client.patch(f"{API}/actions/{aid}", headers=ceo, json={"status": "IN_PROGRESS"}).json()["status"] == "IN_PROGRESS"
    assert client.patch(f"{API}/actions/{aid}", headers=ceo, json={"status": "BOGUS"}).status_code == 422


def test_decisions_survive_a_data_refresh(client, ceo, loaded):
    before = client.get(f"{API}/value/summary", headers=ceo).json()["accepted"]
    assert client.post(f"{API}/data/import?wait=true", headers=ceo).status_code == 202
    assert client.get(f"{API}/value/summary", headers=ceo).json()["accepted"] == before


def test_audit_trail_records_business_actions_without_secrets(client, ceo):
    logs = client.get(f"{API}/admin/audit-logs?page_size=200", headers=ceo).json()["items"]
    actions = {l["action"] for l in logs}
    assert {"login", "data_import", "recommendation_viewed", "recommendation_accepted"} <= actions or {"login", "data_import", "recommendation_viewed"} <= actions
    assert "password" not in str(logs).lower() or "password_hash" not in str(logs)
    assert "ceo-password-123" not in str(logs)


def test_alerts_read_resolve(client, ceo):
    al = client.get(f"{API}/alerts", headers=ceo).json()
    assert al["items"] and {a["severity"] for a in al["items"]} <= {"CRITICAL", "WARNING", "OPPORTUNITY"}
    aid = al["items"][0]["id"]
    assert client.patch(f"{API}/alerts/{aid}", headers=ceo, json={"status": "READ"}).json()["status"] == "READ"
    assert client.patch(f"{API}/alerts/{aid}", headers=ceo, json={"status": "RESOLVED"}).json()["status"] == "RESOLVED"
    assert aid not in [a["id"] for a in client.get(f"{API}/alerts", headers=ceo).json()["items"]]


def test_exports_and_restricted_fields(client, ceo, users):
    r = client.get(f"{API}/export/products?format=csv", headers=ceo)
    assert r.status_code == 200 and "product_name" in r.text and "gp_12m" in r.text
    m = client.get(f"{API}/export/products?format=csv", headers=users["marketing"])
    assert m.status_code == 200 and "gp_12m" not in m.text and "margin_12m" not in m.text
    assert client.get(f"{API}/export/suppliers?format=csv", headers=users["marketing"]).status_code == 403
    x = client.get(f"{API}/export/recommendations?format=xlsx", headers=ceo)
    assert x.status_code == 200 and x.content[:2] == b"PK"
    p = client.get(f"{API}/export/executive-summary?format=pdf", headers=ceo)
    assert p.status_code == 200 and p.content[:4] == b"%PDF"
    assert client.get(f"{API}/export/products?format=csv", headers=users["store"]).status_code == 403   # store managers cannot export


def test_search(client, ceo, users):
    r = client.get(f"{API}/search?q=Test Product", headers=ceo).json()["results"]
    assert any(x["type"] == "Product" for x in r)
    assert any(x["type"] == "Location" for x in client.get(f"{API}/search?q=Store", headers=ceo).json()["results"])
    assert any(x["type"] == "Invoice" for x in client.get(f"{API}/search?q=INV00000", headers=ceo).json()["results"])


def test_security_headers_and_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert b"merch_http_requests_total" in client.get("/metrics").content


def test_import_requires_data_folder(client, ceo, data_dir, tmp_path, monkeypatch):
    from app.core.config import get_settings
    # data_dir normally auto-detects the real folder; force it to point at nothing for this check
    monkeypatch.setattr(type(get_settings()), "data_dir", property(lambda self: str(tmp_path / "nothing-here")))
    r = client.post(f"{API}/data/import?wait=true", headers=ceo)
    assert r.status_code == 422 and "folder" in r.json()["error"]["message"]

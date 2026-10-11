"""V5 workspace read models: real data only, role scopes, location isolation, no write side effects."""


def test_notifications_are_real_and_role_filtered(client, ceo, users, loaded):
    n = client.get("/api/v1/workspace/notifications", headers=ceo).json()
    assert n["total"] == sum(n["totals"].values())
    assert all(i["entity"]["url"].startswith("/") for i in n["items"])
    opens = client.get("/api/v1/recovery/priorities?page_size=200", headers=ceo).json()
    mk = client.get("/api/v1/workspace/notifications", headers=users["marketing"]).json()
    assert "data_quality" not in mk["totals"] and "outcome" not in mk["totals"] or mk["totals"].get("data_quality", 0) == 0
    assert client.get("/api/v1/workspace/notifications").status_code == 401
    assert isinstance(opens, dict)


def test_network_edges_reference_existing_nodes_only(client, ceo, loaded):
    r = client.get("/api/v1/workspace/network?limit=10", headers=ceo)
    assert r.status_code == 200, r.text
    d = r.json(); ids = {n["id"] for n in d["nodes"]}
    assert d["edges"] and all(e["source"] in ids and e["target"] in ids for e in d["edges"])
    kinds = {n["kind"] for n in d["nodes"]}
    assert {"product", "location"} <= kinds
    assert d["shown_products"] <= 10
    rels = {e["rel"] for e in d["edges"]}
    assert rels <= {"stocked_at", "uses", "supplied_by", "concerns", "at_location"}
    assert not any(e for e in d["edges"] if e["source"].startswith("unit:") or e["target"].startswith("unit:")), "business units have no real links"


def test_network_respects_location_isolation_and_procurement_scope(client, users, loaded):
    d = client.get("/api/v1/workspace/network?limit=10", headers=users["store"]).json()
    locs = {n["ref"] for n in d["nodes"] if n["kind"] == "location"}
    assert locs <= {"LOC001"}
    assert not {n["kind"] for n in d["nodes"]} & {"supplier", "material", "unit"}
    mk = client.get("/api/v1/workspace/network?limit=10", headers=users["marketing"]).json()
    assert not {n["kind"] for n in mk["nodes"]} & {"supplier", "material"}


def test_timeline_reports_unavailable_history_and_hides_cost_for_marketing(client, ceo, users, loaded):
    d = client.get("/api/v1/workspace/timeline", headers=ceo).json()
    assert d["months"] and "net_sales_egp" in d["coverage"] and d["notes"]
    assert all("gross_profit_egp" not in m for m in client.get("/api/v1/workspace/timeline", headers=users["marketing"]).json()["months"])
    one = client.get("/api/v1/workspace/timeline?since=2999-01&until=2999-12", headers=ceo).json()
    assert one["months"] == [] and len(one["unavailable"]) >= 5
    assert client.get("/api/v1/workspace/timeline?product_id=NOPE", headers=ceo).status_code == 404
    assert client.get("/api/v1/workspace/timeline?location_id=LOC002", headers=users["store"]).status_code == 403


def test_product_context_and_scopes(client, ceo, users, loaded):
    pid = client.get("/api/v1/products?page_size=1", headers=ceo).json()["items"][0]["product_id"]
    d = client.get(f"/api/v1/workspace/products/{pid}/context", headers=ceo).json()
    assert "inventory_history" in d and "procurement" in d and "decision_history" in d
    m = client.get(f"/api/v1/workspace/products/{pid}/context", headers=users["marketing"]).json()
    assert "procurement" not in m
    assert client.get("/api/v1/workspace/products/NOPE/context", headers=ceo).status_code == 404


def test_board_lanes_and_transitions_follow_role(client, ceo, users, loaded):
    b = client.get("/api/v1/workspace/board", headers=ceo).json()
    assert [l["key"] for l in b["lanes"]][0] == "open" and b["can_decide"] is True
    assert sum(l["total"] for l in b["lanes"]) >= 1
    a = client.get("/api/v1/workspace/board", headers=users["analyst"]).json()
    assert a["can_decide"] is False and a["transitions"] == {}


def test_decision_history_and_reports_catalogue(client, ceo, users, loaded):
    key = client.get("/api/v1/workspace/board", headers=ceo).json()["lanes"][0]["cards"][0]["rec_key"]
    h = client.get("/api/v1/workspace/decisions/history", params={"rec_key": key}, headers=ceo).json()
    assert h["events"][0]["kind"] == "detected"
    rep = client.get("/api/v1/workspace/reports", headers=ceo).json()
    assert rep["reports"] and any("NOT implemented" in x for x in rep["requirements"])
    assert all(r["id"] != "suppliers" for r in client.get("/api/v1/workspace/reports", headers=users["marketing"]).json()["reports"])


def test_workspace_is_read_only(client, ceo, loaded):
    before = client.get("/api/v1/workspace/board", headers=ceo).json()
    for path in ("notifications", "network", "timeline", "board", "reports"):
        assert client.get(f"/api/v1/workspace/{path}", headers=ceo).status_code == 200
        assert client.post(f"/api/v1/workspace/{path}", headers=ceo).status_code in (404, 405)
    assert client.get("/api/v1/workspace/board", headers=ceo).json()["lanes"] == before["lanes"]


def test_workspace_sentences_have_arabic(client, ceo, loaded):
    ar = {**ceo, "Accept-Language": "ar"}
    n = client.get("/api/v1/workspace/network?limit=5", headers=ar).json()
    assert all(any("؀" <= ch <= "ۿ" for ch in x) for x in n["notes"])
    r = client.get("/api/v1/workspace/reports", headers=ar).json()
    assert all(any("؀" <= ch <= "ۿ" for ch in x) for x in r["requirements"])
    t = client.get("/api/v1/workspace/timeline", headers=ar).json()
    assert all(any("؀" <= ch <= "ۿ" for ch in x) for x in t["notes"])
    key = client.get("/api/v1/workspace/board", headers=ceo).json()["lanes"][0]["cards"][0]["rec_key"]
    h = client.get("/api/v1/workspace/decisions/history", params={"rec_key": key}, headers=ar).json()
    assert any("؀" <= ch <= "ۿ" for ch in h["events"][0]["text"])

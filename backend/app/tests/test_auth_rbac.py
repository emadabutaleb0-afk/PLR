import jwt, pytest
from app.core.config import get_settings

API = "/api/v1"


def test_login_failure_and_protected_routes(client, loaded):
    assert client.post(f"{API}/auth/login", json={"email": "ceo@test.local", "password": "wrong"}).status_code == 401
    r = client.get(f"{API}/executive/overview")
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"
    assert client.get(f"{API}/executive/overview", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_and_token_types(client, loaded):
    tok = client.post(f"{API}/auth/login", json={"email": "ceo@test.local", "password": "ceo-password-123"}).json()
    ok = client.post(f"{API}/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert ok.status_code == 200 and ok.json()["access_token"]
    # a refresh token must never work as an access token, and vice versa
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok['refresh_token']}"}).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tok["access_token"]}).status_code == 401


def test_expired_token_rejected(client, loaded):
    s = get_settings()
    from datetime import datetime, timedelta, timezone
    old = jwt.encode({"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, s.secret_key, algorithm="HS256")
    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old}"})
    assert r.status_code == 401 and "expired" in r.json()["error"]["message"]


def test_passwords_are_hashed(client, users):
    from app.db.session import SessionLocal
    from app.models.app import User
    from sqlalchemy import select
    db = SessionLocal()
    try:
        for u in db.scalars(select(User)):
            assert u.password_hash.startswith("$2") and "password" not in u.password_hash
    finally:
        db.close()


def test_only_admin_can_create_users(client, users):
    r = client.post(f"{API}/auth/users", headers=users["exec"], json=dict(email="x@test.local", password="a-long-password-1", role="ANALYST"))
    assert r.status_code == 403


def test_marketing_cannot_see_procurement(client, users):
    for path in ("/suppliers/performance", "/suppliers/true-cost", "/quality/impact", "/operations/bottlenecks", "/executive/overview", "/data/import"):
        m = "post" if "import" in path else "get"
        assert getattr(client, m)(f"{API}{path}", headers=users["marketing"]).status_code == 403, path
    recs = client.get(f"{API}/recovery/priorities?page_size=200", headers=users["marketing"])
    assert recs.status_code == 403   # recovery scope is not granted to marketing
    items = client.get(f"{API}/executive/recovery-opportunities", headers=users["marketing"])
    assert items.status_code == 403


def test_cost_fields_hidden_from_roles_without_cost_scope(client, users, ceo):
    ceo_rows = client.get(f"{API}/products?page_size=50", headers=ceo).json()["items"]
    mk_rows = client.get(f"{API}/products?page_size=50", headers=users["marketing"]).json()["items"]
    assert "gp_12m" in ceo_rows[0] and "margin_12m" in ceo_rows[0]
    assert "gp_12m" not in mk_rows[0] and "margin_12m" not in mk_rows[0]
    assert client.get(f"{API}/inventory/productivity", headers=users["marketing"]).status_code == 403
    r = client.get(f"{API}/products/P001", headers=users["marketing"]).json()
    assert "gp" not in str(r["performance"][0]) and "margin" not in r["kpis"]


def test_store_manager_data_isolation(client, users, ceo):
    r = client.get(f"{API}/inventory/stockout-risk?level=LOW&page_size=200", headers=users["store"]).json()
    assert r["total"] > 0 and {x["location_id"] for x in r["items"]} == {"LOC001"}
    h = client.get(f"{API}/inventory/health", headers=users["store"]).json()
    assert {x["location_id"] for x in h["locations"]} == {"LOC001"} and {x["location_id"] for x in h["heatmap"]} == {"LOC001"}
    d = client.get(f"{API}/products/P001", headers=users["store"]).json()
    assert {x["location_id"] for x in d["locations"]} == {"LOC001"}
    full = client.get(f"{API}/products/P001", headers=ceo).json()
    assert d["kpis"]["units_12m"] < full["kpis"]["units_12m"]            # aggregates are location-scoped too
    assert client.get(f"{API}/executive/overview", headers=users["store"]).status_code == 403
    assert client.get(f"{API}/suppliers/performance", headers=users["store"]).status_code == 403
    # search must not reveal other locations' invoices or supplier names
    s = client.get(f"{API}/search?q=Supplier", headers=users["store"]).json()["results"]
    assert not [x for x in s if x["type"] == "Supplier"]


def test_store_manager_cannot_act_on_other_locations(client, users, ceo):
    recs = client.get(f"{API}/recovery/priorities?page_size=200", headers=ceo).json()["items"]
    other = next(r for r in recs if r["location_id"] and r["location_id"] != "LOC001")
    r = client.post(f"{API}/recommendations/{other['rec_key']}/feedback", headers=users["store"], json={"decision": "ACCEPT"})
    assert r.status_code == 403


def test_production_manager_scope(client, users):
    assert client.get(f"{API}/operations/bottlenecks", headers=users["production"]).status_code == 200
    assert client.get(f"{API}/marketing/performance", headers=users["production"]).status_code == 403

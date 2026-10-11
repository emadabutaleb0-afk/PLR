"""User administration, password change, system status and Arabic rendering."""
API = "/api/v1"


def _login(client, email, pw):
    return client.post(f"{API}/auth/login", json={"email": email, "password": pw})


def test_system_status_for_any_user(client, ceo, loaded):
    r = client.get(f"{API}/system/status", headers=ceo)
    assert r.status_code == 200 and r.json()["has_data"] is True and r.json()["importing"] is False


def test_admin_can_edit_disable_and_reset(client, ceo, loaded):
    u = client.post(f"{API}/auth/users", headers=ceo, json=dict(email="temp@test.local", password="first-password-1", role="ANALYST", full_name="Temp")).json()
    r = client.patch(f"{API}/auth/users/{u['id']}", headers=ceo, json=dict(role="MARKETING_MANAGER", full_name="Temp 2", password="second-password-2"))
    assert r.status_code == 200 and r.json()["role"] == "MARKETING_MANAGER"
    assert _login(client, "temp@test.local", "first-password-1").status_code == 401
    assert _login(client, "temp@test.local", "second-password-2").status_code == 200
    assert client.patch(f"{API}/auth/users/{u['id']}", headers=ceo, json=dict(is_active=False)).json()["is_active"] is False
    assert _login(client, "temp@test.local", "second-password-2").status_code == 401


def test_cannot_remove_last_ceo_and_store_manager_needs_location(client, ceo, loaded):
    me = client.get(f"{API}/auth/me", headers=ceo).json()
    assert client.patch(f"{API}/auth/users/{me['id']}", headers=ceo, json=dict(is_active=False)).status_code == 409
    assert client.patch(f"{API}/auth/users/{me['id']}", headers=ceo, json=dict(role="ANALYST")).status_code == 409
    u = client.post(f"{API}/auth/users", headers=ceo, json=dict(email="sm@test.local", password="store-password-1", role="ANALYST")).json()
    assert client.patch(f"{API}/auth/users/{u['id']}", headers=ceo, json=dict(role="STORE_MANAGER")).status_code == 422


def test_non_admin_cannot_manage_users(client, users):
    assert client.get(f"{API}/auth/users", headers=users["analyst"]).status_code == 403
    assert client.patch(f"{API}/auth/users/1", headers=users["analyst"], json=dict(is_active=False)).status_code == 403


def test_change_password(client, ceo, loaded):
    client.post(f"{API}/auth/users", headers=ceo, json=dict(email="pw@test.local", password="old-password-123", role="ANALYST"))
    h = {"Authorization": f"Bearer {_login(client, 'pw@test.local', 'old-password-123').json()['access_token']}"}
    assert client.post(f"{API}/auth/change-password", headers=h, json=dict(current_password="wrong-password", new_password="brand-new-pass-1")).status_code == 422
    assert client.post(f"{API}/auth/change-password", headers=h, json=dict(current_password="old-password-123", new_password="brand-new-pass-1")).status_code == 200
    assert _login(client, "pw@test.local", "brand-new-pass-1").status_code == 200


def test_arabic_responses_and_english_default(client, ceo, loaded):
    en = client.get(f"{API}/executive/decisions?limit=6", headers=ceo).json()["items"]
    ar = client.get(f"{API}/executive/decisions?limit=6", headers={**ceo, "Accept-Language": "ar"}).json()["items"]
    assert en and len(en) == len(ar)
    assert any(a["problem"] != e["problem"] for a, e in zip(ar, en))
    assert all(a["rec_key"] == e["rec_key"] for a, e in zip(ar, en))
    err = client.post(f"{API}/auth/login", json=dict(email="x@y.z", password="nope"), headers={"Accept-Language": "ar"})
    assert err.status_code == 401 and "غير صحيحة" in err.json()["error"]["message"]


def test_translator_unit():
    from app.core.i18n_ar import tr
    assert tr("Stock is in the wrong place") == "المخزون في المكان الخطأ"
    assert "ج.م" in tr("Estimated quality loss in the last 180 days: EGP 12,000")
    assert tr("A sentence nobody wrote a rule for") == "A sentence nobody wrote a rule for"

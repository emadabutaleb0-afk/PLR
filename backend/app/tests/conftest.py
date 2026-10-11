import os, tempfile, shutil
_tmp = tempfile.mkdtemp(prefix="smb_test_")
os.environ.update(DATABASE_URL=os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db"), DATA_DIRECTORY=f"{_tmp}/data", MODEL_DIRECTORY=f"{_tmp}/models", ENVIRONMENT="test",
                  RATE_LIMIT_PER_MINUTE="0", BOOTSTRAP_ADMIN_EMAIL="ceo@test.local", BOOTSTRAP_ADMIN_PASSWORD="ceo-password-123", SECRET_KEY="test-secret-test-secret-test-secret-123", BLOCK_STALE_APPROVALS="false")
os.environ.pop("REDIS_URL", None)
import pytest
from fastapi.testclient import TestClient
from app.tests.synth import generate


@pytest.fixture(scope="session")
def data_dir():
    generate(f"{_tmp}/data")
    return f"{_tmp}/data"


@pytest.fixture(scope="session")
def client(data_dir):
    from app.main import app
    with TestClient(app) as c:
        yield c


def _login(client, email, pw):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def ceo(client):
    return _login(client, "ceo@test.local", "ceo-password-123")


@pytest.fixture(scope="session")
def loaded(client, ceo):
    r = client.post("/api/v1/data/import?wait=true", headers=ceo)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "SUCCESS", body
    return body


@pytest.fixture(scope="session")
def users(client, ceo, loaded):
    out = {}
    specs = {"marketing": ("MARKETING_MANAGER", None), "store": ("STORE_MANAGER", ["LOC001"]), "production": ("PRODUCTION_MANAGER", None), "analyst": ("ANALYST", None), "exec": ("EXECUTIVE", None)}
    for k, (role, locs) in specs.items():
        r = client.post("/api/v1/auth/users", headers=ceo, json=dict(email=f"{k}@test.local", password="a-long-password-1", role=role, allowed_locations=locs, full_name=k))
        assert r.status_code == 201, r.text
        out[k] = _login(client, f"{k}@test.local", "a-long-password-1")
    return out

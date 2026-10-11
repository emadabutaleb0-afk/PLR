#!/usr/bin/env python3
"""End-to-end smoke test against a RUNNING stack (Docker or local). Standard library only.
Usage:  python ops/smoke.py [--base http://localhost:3000] [--email ...] [--password ...] [--import]
  --base      the frontend (it proxies /api) or the API itself, e.g. http://localhost:8000
  --import    also queue a data import and wait for the worker to finish it (this is what proves Redis + Celery)
Exit code 0 only when every check passes. The admin password is read from .env when not passed."""
import argparse, json, sys, time, urllib.error, urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://localhost:3000")
ap.add_argument("--email"); ap.add_argument("--password"); ap.add_argument("--import", dest="do_import", action="store_true")
a = ap.parse_args()
env = {}
f = Path(__file__).resolve().parents[1] / ".env"
if f.exists():
    for line in f.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1); env[k.strip()] = v.strip()
email, pw = a.email or env.get("BOOTSTRAP_ADMIN_EMAIL"), a.password or env.get("BOOTSTRAP_ADMIN_PASSWORD")
B, results = a.base.rstrip("/") + "/api/v1", []


def call(path, method="GET", body=None, tok=None, timeout=60):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b"{}")
        except Exception: return e.code, {}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def check(name, ok, detail=""):
    results.append(ok); print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  - {detail}" if detail else ""))


s, t = call("/auth/login", "POST", {"email": email, "password": pw})
check("login", s == 200 and "access_token" in t, f"status {s}")
if s != 200:
    sys.exit(1)
tok = t["access_token"]
if a.do_import:
    s, j = call("/data/import", "POST", None, tok)
    check("import queued", s == 202, f"status {s}, job {j.get('id')}")
    t0, st = time.time(), None
    while time.time() - t0 < 900:
        _, r = call(f"/jobs/{j.get('id')}", tok=tok); st = r.get("status")
        if st in ("SUCCESS", "FAILED"): break
        time.sleep(3)
    check("worker finished the import", st == "SUCCESS", f"{st} after {time.time() - t0:.0f}s")
for path, key in [("/data/health", None), ("/data/reconciliation", "checks"), ("/commercial/command-center", "tiles"), ("/commercial/decision-plans", "plans"),
                  ("/commercial/autopsy", "drivers"), ("/recovery/priorities?page_size=5", "items"), ("/decisions/tracking", "items"), ("/value/summary", "measured_outcomes")]:
    s, r = call(path, tok=tok)
    check(f"GET {path}", s == 200 and (key is None or key in r), f"status {s}")
s, p = call("/commercial/decision-plans", tok=tok)
check("plans have 3 alternatives", s == 200 and [x["name"] for x in p.get("plans", [])] == ["max_profit", "balanced", "min_risk"])
s, pr = call("/recovery/priorities?page_size=1", tok=tok)
if s == 200 and pr.get("items"):
    k = pr["items"][0]["rec_key"]
    s, d = call(f"/recommendations/{k}", tok=tok)
    check("recommendation detail has reasons and confidence", s == 200 and d.get("why") and d.get("confidence") is not None)
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)

#!/usr/bin/env python3
"""Pre-flight check before the first run or after moving the project to a new machine.
Usage:  python ops/preflight.py        (from the project root; exits non-zero when something blocks a run)
Checks: Python version, every package in backend/requirements.txt is importable at the pinned version (pulp, lightgbm, ...),
the 20 company files, .env safety, optional Redis and Postgres reachability."""
import importlib.metadata as md
import os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD, WARN, OK = [], [], []
sys.path.insert(0, str(ROOT / "backend"))

# 1. python
(OK if sys.version_info >= (3, 11) else BAD).append(f"Python {sys.version.split()[0]} (needs 3.11+)")

# 2. packages
for line in (ROOT / "backend" / "requirements.txt").read_text().splitlines():
    m = re.match(r"^([A-Za-z0-9_.\-]+)==(.+)$", line.strip())
    if not m:
        continue
    name, want = m.groups()
    try:
        have = md.version(name)
        (OK if have == want else WARN).append(f"{name} {have}" + ("" if have == want else f" (pinned {want})"))
    except md.PackageNotFoundError:
        BAD.append(f"{name} is NOT installed  ->  pip install -r backend/requirements.txt")

# 3. data
need = ["Sales_Transactions", "Inventory_History", "Product_Master", "Locations", "Purchase_Orders", "Production_Orders", "Quality", "Marketing", "Suppliers", "Materials", "Product_BOM",
        "Customers", "Customer_Service", "Machine_Downtime", "Printing_Batches", "Web_Traffic_Daily", "Group_Operations", "Business_Units", "Case_Briefs", "Data_Dictionary"]
data = ROOT / "data" / "private"
missing = [n for n in need if not (data / f"{n}.csv").exists()]
(BAD if len(missing) == len(need) else WARN if missing else OK).append(f"company files: {len(need) - len(missing)}/{len(need)} in data/private" + (f" (missing: {', '.join(missing)})" if missing else ""))

# 4. configuration safety
env_file = ROOT / ".env"
if not env_file.exists():
    BAD.append(".env missing  ->  python ops/gen_env.py")
else:
    try:
        from app.core.config import get_settings
        s = get_settings()
        prob = s.production_problems()
        (WARN if prob else OK).append("production guard: " + ("; ".join(prob) + "  (fine for local use, blocks ENVIRONMENT=production; fix with ops/gen_env.py)" if prob else "passes"))
        if os.environ.get("SECRET_KEY") is None and s.secret_key.startswith("dev-only"):
            WARN.append("SECRET_KEY is the development default")
    except Exception as e:  # noqa: BLE001
        BAD.append(f"configuration could not be loaded: {type(e).__name__}: {e}")

# 5. optional services
for label, var, default in (("Redis", "REDIS_URL", None), ("Postgres", "DATABASE_URL", None)):
    url = os.environ.get(var, default)
    if not url:
        OK.append(f"{label}: not configured (local mode uses {'in-process cache and threaded jobs' if label == 'Redis' else 'a SQLite file'})")
        continue
    try:
        if label == "Redis":
            import redis
            redis.Redis.from_url(url, socket_connect_timeout=3).ping()
        else:
            from sqlalchemy import create_engine, text
            with create_engine(url).connect() as c:
                c.execute(text("select 1"))
        OK.append(f"{label}: reachable")
    except Exception as e:  # noqa: BLE001
        BAD.append(f"{label} configured but not reachable: {type(e).__name__}")

for t, lst in (("OK", OK), ("WARN", WARN), ("BLOCKER", BAD)):
    for x in lst:
        print(f"[{t:7}] {x}")
print(f"\n{len(OK)} ok, {len(WARN)} warnings, {len(BAD)} blockers")
sys.exit(1 if BAD else 0)

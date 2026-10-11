#!/usr/bin/env bash
# Starts the full Docker stack (Postgres + Redis + API + Celery worker + frontend), waits until it answers, and runs the smoke test including a queued import.
# Usage: bash ops/verify_stack.sh        Stop afterwards with: docker compose down
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || python3 ops/gen_env.py
python3 ops/preflight.py || { echo "Fix the blockers above first."; exit 1; }
docker compose up -d --build
echo "Waiting for the app to answer on http://localhost:3000 ..."
for i in $(seq 1 90); do curl -fs -o /dev/null http://localhost:3000/login && break || sleep 4; done
docker compose ps
python3 ops/smoke.py --base http://localhost:3000 --import
echo "Worker log (last lines):"; docker compose logs --tail=8 worker || true

#!/usr/bin/env bash
# Linux / macOS launcher:  ./run.sh   (needs python3.11+ and node 20+)
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt
[ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)
[ -f frontend/.next/BUILD_ID ] || (cd frontend && npm run build)
(cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BE=$!
trap "kill $BE 2>/dev/null" EXIT
cd frontend && npm start

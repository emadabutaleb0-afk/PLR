#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================================"
echo "       BUSINESS GATE - Decision & Profit Intelligence"
echo "                Offline Standalone Package"
echo "========================================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is required but not installed."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "[ERROR] node is required but not installed."
    exit 1
fi

if [ ! -d "backend/.venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate
    pip install -q -r backend/requirements.txt
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "[SETUP] Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

echo "[1/3] Starting Backend API on http://127.0.0.1:8000..."
cd backend && ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

echo "[2/3] Starting Frontend on http://localhost:3000..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo "[3/3] Waiting for servers to initialize..."
sleep 4

echo ""
echo "========================================================"
echo " Business Gate is now running!"
echo " URL:         http://localhost:3000"
echo " Credentials: ceo@company.local / change-this-first-password"
echo "========================================================"
echo ""

if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
elif command -v open &> /dev/null; then
    open http://localhost:3000
fi

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

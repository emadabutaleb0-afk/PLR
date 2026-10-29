@echo off
cd /d "%~dp0"
if not exist "backend\.venv" (
    echo Creating virtual environment...
    python -m venv backend\.venv
)
echo Checking dependencies...
call backend\.venv\Scripts\activate.bat
pip install -q -r backend\requirements.txt
if not exist "frontend\node_modules" (
    echo Installing frontend packages...
    cd frontend && npm install && cd ..
)
echo Starting Backend API on http://127.0.0.1:8000...
start "Business Gate Backend" cmd /k "cd /d "%~dp0backend" && ..\backend\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo Starting Frontend on http://localhost:3000...
start "Business Gate Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo Both servers launched!

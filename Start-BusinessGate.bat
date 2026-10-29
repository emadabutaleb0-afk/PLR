@echo off
title Business Gate - Offline Launcher
color 0B
echo ========================================================
echo        BUSINESS GATE - Decision & Profit Intelligence
echo                 Offline Standalone Package
echo ========================================================
echo.
cd /d "%~dp0"

:: 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

:: 2. Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js was not found in your system PATH!
    echo Please install Node.js (LTS version) from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: 3. Setup backend virtual environment if not present
if not exist "backend\.venv" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv backend\.venv
    call backend\.venv\Scripts\activate.bat
    echo [SETUP] Installing backend dependencies...
    pip install -q -r backend\requirements.txt
)

:: 4. Setup frontend packages if not present
if not exist "frontend\node_modules" (
    echo [SETUP] Installing frontend packages...
    cd frontend && call npm install && cd ..
)

echo [1/3] Starting Business Gate Backend API on http://127.0.0.1:8000...
start "Business Gate Backend" cmd /c "cd /d "%~dp0backend" && ..\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting Business Gate Frontend on http://localhost:3000...
start "Business Gate Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo [3/3] Waiting for servers to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ========================================================
echo  Business Gate is now running!
echo  URL:         http://localhost:3000
echo  Credentials: admin / password
echo ========================================================
echo.
echo Opening browser...
start http://localhost:3000

echo.
echo System is active. To stop both servers, double-click Stop-BusinessGate.bat
pause

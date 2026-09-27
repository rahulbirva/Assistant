@echo off
:: ─────────────────────────────────────────────────────────────
:: START_JARVIS.bat — 1-Click Master Power ON
:: Starts: Jarvis Python backend + HUD interface
:: ─────────────────────────────────────────────────────────────
setlocal
cd /d "%~dp0"

echo ========================================================
echo   TURNING ON JARVIS // INITIALIZING SYSTEMS
echo ========================================================

:: 1. Check if backend is already running
tasklist /fi "imagename eq pythonw.exe" 2>nul | find /i "pythonw.exe" >nul
if not errorlevel 1 (
    echo [INFO] Jarvis background service is already running.
) else (
    echo [1/2] Starting Jarvis Voice Core ^& Neural Brain...
    start "" /B "%~dp0.venv\Scripts\pythonw.exe" "%~dp0jarvis_service.py"
    timeout /t 3 /nobreak >nul
)

:: 2. Launch Localhost Website HUD
echo [2/2] Launching Tactical HUD Website on http://localhost:7788...
start "" "http://localhost:7788"

echo [READY] Jarvis is ONLINE.
exit /b 0

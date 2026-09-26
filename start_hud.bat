@echo off
:: ─────────────────────────────────────────────────────────────
:: start_hud.bat — Launch the JARVIS Electron HUD overlay
:: Run this alongside jarvis_service.py (or jarvis.py)
:: ─────────────────────────────────────────────────────────────
setlocal
cd /d "%~dp0\hud"

if not exist node_modules (
    echo [HUD] First run — installing Electron dependencies...
    call npm install --prefer-offline
    if errorlevel 1 (
        echo [HUD] npm install failed. Make sure Node.js is installed.
        pause
        exit /b 1
    )
)

echo [HUD] Starting JARVIS HUD overlay...
call npm start

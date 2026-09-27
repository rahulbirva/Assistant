@echo off
:: ─────────────────────────────────────────────────────────────
:: jarvis_launch.bat — Silent startup launcher (registered in Task Scheduler)
:: Starts: Python backend (hud_server + voice loop) + Electron HUD
:: No console window shown. Both processes are independent.
:: ─────────────────────────────────────────────────────────────
setlocal
cd /d "%~dp0"

:: ── 1. Start the Python backend silently (no window) ─────────
start "" /B "%~dp0.venv\Scripts\pythonw.exe" "%~dp0jarvis_service.py"

:: Brief pause to let backend bind WebSocket port 7789
timeout /t 4 /nobreak >nul

:: ── 2. Open the Tactical HUD Website on localhost:7788 ────────────
start "" "http://localhost:7788"

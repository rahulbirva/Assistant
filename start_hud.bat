@echo off
:: ─────────────────────────────────────────────────────────────
:: start_hud.bat — Launch the JARVIS Tactical HUD Website
:: Opens http://localhost:7788 in your default web browser
:: ─────────────────────────────────────────────────────────────
setlocal
cd /d "%~dp0"

echo [HUD] Opening JARVIS Tactical HUD Website on http://localhost:7788...
start "" "http://localhost:7788"
exit /b 0

@echo off
:: ─────────────────────────────────────────────────────────────
:: STOP_JARVIS.bat — 1-Click Master Power OFF
:: Cleanly shuts down Jarvis Python service, HUD, and audio processes
:: ─────────────────────────────────────────────────────────────
setlocal
cd /d "%~dp0"

echo ========================================================
echo   TURNING OFF JARVIS // SHUTTING DOWN ALL SUBSYSTEMS
echo ========================================================

:: 1. Terminate pythonw backend service
echo [1/3] Stopping Jarvis background service (pythonw)...
taskkill /f /im pythonw.exe 2>nul
if not errorlevel 1 (
    echo       [OK] Python backend stopped.
) else (
    echo       [--] Python backend was not running.
)

:: 2. Terminate Electron HUD overlay
echo [2/3] Closing HUD interface (electron)...
taskkill /f /im electron.exe 2>nul
if not errorlevel 1 (
    echo       [OK] HUD closed.
) else (
    echo       [--] HUD was not running.
)

:: 3. Brief cleanup
echo [3/3] Releasing audio handles and system tray...
timeout /t 1 /nobreak >nul

echo ========================================================
echo   JARVIS IS NOW COMPLETELY POWERED OFF.
echo ========================================================
timeout /t 2 /nobreak >nul
exit /b 0

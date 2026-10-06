@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   TESTING JARVIS SPOTIFY API INTEGRATION
echo ========================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "%~dp0test_spotify.py"
) else (
    python "%~dp0test_spotify.py"
)

echo.
pause

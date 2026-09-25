@echo off
cd /d "%~dp0"
echo Starting JARVIS...
call .venv\Scripts\python.exe jarvis.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Jarvis exited with error code %ERRORLEVEL%.
    pause
)

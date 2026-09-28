@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   JARVIS AI ASSISTANT — 1-CLICK INSTALLATION WIZARD
echo ========================================================
echo.

:: 1. Verify Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3.10 or 3.11 from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo       Found: %%i

:: 2. Create virtual environment
echo.
echo [2/4] Setting up Python virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    echo       [OK] Virtual environment created in .venv\
) else (
    echo       [OK] Existing virtual environment found.
)

:: 3. Install dependencies
echo.
echo [3/4] Installing Python packages from requirements.txt...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo [NOTICE] If dlib had an issue, install precompiled wheel:
    echo   .venv\Scripts\pip install dlib-bin
)

:: 4. Verify Ollama
echo.
echo [4/4] Checking Ollama AI model engine...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo       [!] Ollama was not detected on this device.
    echo           Please install Ollama from: https://ollama.ai
    echo           Then run: ollama pull llama3.2:3b
) else (
    echo       [OK] Ollama found. Downloading / updating llama3.2:3b model...
    ollama pull llama3.2:3b
)

echo.
echo ========================================================
echo   INSTALLATION COMPLETE!
echo.
echo   To launch JARVIS:
echo     1. Double-click START_JARVIS.bat
echo     2. Browser HUD will open at: http://localhost:7788
echo.
echo   To register auto-start on Windows boot:
echo     .venv\Scripts\python.exe register_startup.py
echo ========================================================
echo.
pause

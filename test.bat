@echo off
cd /d "%~dp0"
echo ============================================================
echo   JARVIS - FULL UNIFIED SYSTEM DIAGNOSTICS & BENCHMARK
echo   Testing Voice, Brain, Face Gate, and Computer Control
echo ============================================================
call .venv\Scripts\python.exe test_all.py %*
pause

@echo off
cd /d "%~dp0"
echo Running Jarvis Voice Diagnostics and Benchmarks...
call .venv\Scripts\python.exe test_voice.py %*
pause

@echo off
cd /d "%~dp0"
echo Starting Jarvis Biometric Face Enrollment...
call .venv\Scripts\python.exe enroll_face.py
pause

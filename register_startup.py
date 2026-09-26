"""
Windows Startup & Task Scheduler Registration Script for Jarvis (Phase 5).
Registers 'Jarvis-Startup' in Windows Task Scheduler to run automatically and silently
at user login using pythonw.exe (zero console window).
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TASK_NAME = "Jarvis-Startup"


def get_pythonw_path() -> Path:
    """Finds pythonw.exe in the virtual environment for windowless execution."""
    venv_pythonw = PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"
    if venv_pythonw.exists():
        return venv_pythonw
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def register_task() -> bool:
    """Registers the startup task in Windows Task Scheduler."""
    if sys.platform != "win32":
        print("Error: Task Scheduler registration is only supported on Windows.")
        return False

    pythonw = get_pythonw_path()
    service_script = PROJECT_ROOT / "jarvis_service.py"

    # Command to run: pythonw.exe jarvis_service.py
    task_run_cmd = f'"{pythonw}" "{service_script}"'

    print("=" * 65)
    print("  REGISTERING JARVIS STARTUP DAEMON IN WINDOWS TASK SCHEDULER")
    print("=" * 65)
    print(f"Task Name   : {TASK_NAME}")
    print(f"Executable  : {pythonw}")
    print(f"Target Script: {service_script}")
    print(f"Trigger     : On User Logon (Silent, Windowless)")
    print("-" * 65)

    # schtasks command
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", task_run_cmd,
        "/SC", "ONLOGON",
        "/RL", "LIMITED",
        "/F"  # Overwrite if exists
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] Task '{TASK_NAME}' registered successfully!")
            print("Jarvis will now automatically start in the background when you log in to Windows.")
            print("\nVerification Steps:")
            print(f"  - Check status: python register_startup.py --status")
            print(f"  - Test run now: python register_startup.py --run")
            print(f"  - Remove task : python register_startup.py --unregister")
            return True
        else:
            print(f"[ERROR] Failed to register task: {res.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] Subprocess error: {e}")
        return False


def unregister_task() -> bool:
    """Removes the task from Windows Task Scheduler."""
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] Task '{TASK_NAME}' removed from Windows Task Scheduler.")
            return True
        else:
            print(f"[ERROR] Failed to unregister task: {res.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] Subprocess error: {e}")
        return False


def query_task() -> bool:
    """Queries task status."""
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[STATUS] Task '{TASK_NAME}' is currently REGISTERED in Windows Task Scheduler:\n")
            print(res.stdout)
            return True
        else:
            print(f"[INFO] Task '{TASK_NAME}' is NOT registered.")
            return False
    except Exception as e:
        print(f"[ERROR] Subprocess error: {e}")
        return False


def run_task_now() -> bool:
    """Triggers the task immediately for testing."""
    cmd = ["schtasks", "/Run", "/TN", TASK_NAME]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] Task '{TASK_NAME}' triggered. Check your system tray for the Jarvis icon!")
            return True
        else:
            print(f"[ERROR] Failed to run task: {res.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] Subprocess error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Register Jarvis as Windows Startup Daemon")
    parser.add_argument("--register", action="store_true", help="Register Jarvis in Windows Task Scheduler (default)")
    parser.add_argument("--unregister", action="store_true", help="Remove Jarvis from Task Scheduler")
    parser.add_argument("--status", action="store_true", help="Check registration status in Task Scheduler")
    parser.add_argument("--run", action="store_true", help="Trigger the registered startup task immediately")
    args = parser.parse_args()

    if args.unregister:
        unregister_task()
    elif args.status:
        query_task()
    elif args.run:
        run_task_now()
    else:
        register_task()


if __name__ == "__main__":
    main()

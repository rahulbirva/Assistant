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


def _write_silent_vbs() -> Path:
    """
    Writes a tiny VBScript that runs jarvis_launch.bat with no visible window.
    Task Scheduler calls this VBS, which calls the BAT silently.
    """
    vbs_path = PROJECT_ROOT / "jarvis_silent_start.vbs"
    bat_path  = PROJECT_ROOT / "jarvis_launch.bat"
    vbs_path.write_text(
        f'Set sh = CreateObject("WScript.Shell")\n'
        f'sh.Run Chr(34) & "{bat_path}" & Chr(34), 0, False\n',
        encoding="utf-8",
    )
    return vbs_path


def register_task() -> bool:
    """Registers the startup task in Windows Task Scheduler."""
    if sys.platform != "win32":
        print("Error: Task Scheduler registration is only supported on Windows.")
        return False

    vbs_path    = _write_silent_vbs()
    wscript_exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe"

    # Run: wscript.exe jarvis_silent_start.vbs  (zero windows shown)
    task_run_cmd = f'"{wscript_exe}" "{vbs_path}"'

    print("=" * 65)
    print("  REGISTERING JARVIS AUTO-START IN WINDOWS TASK SCHEDULER")
    print("=" * 65)
    print(f"Task Name    : {TASK_NAME}")
    print(f"Launcher     : {vbs_path}")
    print(f"Trigger      : On User Logon (Silent, no console window)")
    print("-" * 65)

    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", task_run_cmd,
        "/SC", "ONLOGON",
        "/RL", "LIMITED",
        "/DELAY", "0000:10",   # 10-second delay after logon (GPU drivers settle)
        "/F",                   # Overwrite if already exists
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] Task '{TASK_NAME}' registered.")
            print("\nWhat happens at next login:")
            print("  1. Windows logs you in")
            print("  2. 10 seconds later, Jarvis backend starts silently")
            print("  3. 4 seconds later, Electron HUD appears (bottom-right)")
            print("  4. Jarvis speaks: 'Online and at your service, Sir.'")
            print("\nManagement commands:")
            print("  Status  : python register_startup.py --status")
            print("  Test now: python register_startup.py --run")
            print("  Remove  : python register_startup.py --unregister")
            return True
        else:
            print(f"[ERROR] {res.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
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
    """Queries registration status in both Task Scheduler and Registry."""
    print("=" * 55)
    print("  JARVIS STARTUP REGISTRATION STATUS")
    print("=" * 55)

    # ── 1. Task Scheduler ────────────────────────────────────
    sched_ok = False
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[Task Scheduler]  REGISTERED")
            sched_ok = True
        else:
            print(f"[Task Scheduler]  NOT registered")
    except Exception as e:
        print(f"[Task Scheduler]  ERROR: {e}")

    # ── 2. Windows Registry HKCU\Run ─────────────────────────
    reg_ok  = False
    reg_val = None
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        reg_val, _ = winreg.QueryValueEx(key, "Jarvis-Startup")
        winreg.CloseKey(key)
        reg_ok = True
        print(f"[Registry HKCU]   REGISTERED")
        print(f"                  Value: {reg_val}")
    except FileNotFoundError:
        print(f"[Registry HKCU]   NOT registered")
    except Exception as e:
        print(f"[Registry HKCU]   ERROR: {e}")

    print("-" * 55)
    if sched_ok or reg_ok:
        print("RESULT: Jarvis WILL auto-start at next login.")
        method = "Task Scheduler" if sched_ok else "Registry (HKCU\\Run)"
        print(f"        Active method: {method}")
    else:
        print("RESULT: Jarvis will NOT auto-start. Run:")
        print("        uv run python register_startup.py")
    print("=" * 55)
    return sched_ok or reg_ok


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


def registry_register() -> bool:
    """
    Registers Jarvis in HKCU\\Run — no admin required.
    Runs at every user login. Launches jarvis_silent_start.vbs via wscript.
    """
    try:
        import winreg
    except ImportError:
        print("[ERROR] winreg not available (not Windows?)")
        return False

    vbs_path    = _write_silent_vbs()
    wscript_exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe"
    cmd_value   = f'"{wscript_exe}" "{vbs_path}"'

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "Jarvis-Startup", 0, winreg.REG_SZ, cmd_value)
        winreg.CloseKey(key)
        print("[SUCCESS] Jarvis registered in Windows Registry (HKCU\\Run).")
        print("          No admin rights required. Active from next login.")
        print("\nWhat happens at next login:")
        print("  1. Windows logs you in")
        print("  2. Jarvis backend starts silently (no console window)")
        print("  3. 4 seconds later, Electron HUD appears (bottom-right)")
        print("  4. Jarvis speaks: 'Online and at your service, Sir.'")
        print("\nTo undo: python register_startup.py --unregister")
        return True
    except Exception as e:
        print(f"[ERROR] Registry write failed: {e}")
        return False


def registry_unregister() -> bool:
    """Remove Jarvis from HKCU\\Run registry key."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, "Jarvis-Startup")
        winreg.CloseKey(key)
        print("[SUCCESS] Jarvis removed from Registry startup.")
        return True
    except FileNotFoundError:
        print("[INFO] Jarvis was not in Registry startup.")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Register Jarvis as Windows Auto-Start")
    parser.add_argument("--register",   action="store_true", help="Register via Task Scheduler (needs admin)")
    parser.add_argument("--registry",   action="store_true", help="Register via Registry HKCU\\Run (no admin needed)")
    parser.add_argument("--unregister", action="store_true", help="Remove from Task Scheduler AND Registry")
    parser.add_argument("--status",     action="store_true", help="Check Task Scheduler registration status")
    parser.add_argument("--run",        action="store_true", help="Trigger the registered task immediately")
    args = parser.parse_args()

    if args.unregister:
        unregister_task()
        registry_unregister()
    elif args.status:
        query_task()
    elif args.run:
        run_task_now()
    elif args.registry:
        registry_register()
    else:
        # Try Task Scheduler first; fall back to Registry if access denied
        print("Attempting Task Scheduler (admin) registration...")
        ok = register_task()
        if not ok:
            print("\nTask Scheduler requires admin. Falling back to Registry (no admin needed)...\n")
            registry_register()


if __name__ == "__main__":
    main()

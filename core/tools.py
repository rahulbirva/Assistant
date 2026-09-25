"""
Tool definitions and execution layer for Jarvis (Phase 2 & Phase 4).
Supports function calling with safety gating for destructive actions.
"""
import os
import sys
import time
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple
from core.logger import logger
import config

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyautogui
except ImportError:
    pyautogui = None


# OpenAI/Ollama compatible tool definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get real-time system status including current time, date, battery level, CPU/memory usage, and running applications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["all", "time", "battery", "performance", "running_apps"],
                        "description": "Specific status category to retrieve. Defaults to 'all'."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch an application on Windows (e.g., notepad, chrome, spotify, calculator, vscode, explorer).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name or executable of the application to launch (e.g., 'notepad', 'chrome', 'spotify', 'calculator', 'code', 'explorer')."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Terminate or close a running application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the application or process to close (e.g., 'notepad', 'chrome', 'spotify')."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_control",
            "description": "Control system hardware and states: volume up/down/mute, lock workstation, sleep, shutdown, or restart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["volume_up", "volume_down", "mute", "unmute", "lock", "sleep", "shutdown", "restart"],
                        "description": "The system control action to perform."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_op",
            "description": "Perform file and folder operations: search, list directory, create file/folder, move, or delete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "search", "create_file", "create_dir", "move", "delete"],
                        "description": "File action to perform."
                    },
                    "path": {
                        "type": "string",
                        "description": "Target file or folder path."
                    },
                    "destination": {
                        "type": "string",
                        "description": "Optional destination path for move operations or content for create_file."
                    }
                },
                "required": ["action", "path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a safe shell command on Windows PowerShell and retrieve output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "PowerShell command to execute."
                    }
                },
                "required": ["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "keyboard_mouse",
            "description": "Automate keyboard typing, shortcut presses, or mouse clicks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["type", "press_key", "hotkey", "click"],
                        "description": "Action type: 'type' text, 'press_key' (e.g. enter, space), 'hotkey' (e.g. ['ctrl', 'c']), or 'click'."
                    },
                    "text_or_key": {
                        "type": "string",
                        "description": "The text to type or key name to press."
                    }
                },
                "required": ["action"]
            }
        }
    }
]


class ToolExecutor:
    """Executes validated tool calls on Windows with safety checks and auditing."""

    # Common Windows App Aliases
    APP_ALIASES = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "brave": "brave.exe",
        "spotify": "spotify.exe",
        "code": "code",
        "vscode": "code",
        "vs code": "code",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "files": "explorer.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
        "cmd": "cmd.exe",
        "task manager": "taskmgr.exe",
        "settings": "start ms-settings:",
    }

    @staticmethod
    def is_destructive(name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Non-negotiable safety guard:
        Returns (True, reason) if the requested action is destructive and requires spoken confirmation.
        """
        if name == "system_control":
            action = args.get("action", "")
            if action in ["shutdown", "restart"]:
                return True, f"shut down or restart your computer"

        elif name == "file_op":
            action = args.get("action", "")
            path = args.get("path", "")
            if action == "delete":
                return True, f"permanently delete the file or folder at {path}"

        elif name == "run_command":
            cmd = args.get("cmd", "").lower()
            safe_prefixes = ["dir", "echo", "whoami", "ipconfig", "get-date", "hostname", "ping"]
            if not any(cmd.strip().startswith(p) for p in safe_prefixes):
                return True, f"execute the shell command: '{cmd}'"

        return False, ""

    def execute(self, name: str, args: Dict[str, Any]) -> str:
        """Executes a tool and logs the action."""
        logger.log("ACTION", f"Executing tool '{name}' with args {args}")
        try:
            handler = getattr(self, f"_tool_{name}", None)
            if not handler:
                return f"Error: Tool '{name}' is not recognized."
            result = handler(args)
            logger.log("ACTION", f"Tool '{name}' completed successfully: {result}")
            return result
        except Exception as e:
            err = f"Failed to execute tool '{name}': {str(e)}"
            logger.log("ERROR", err)
            return err

    def _tool_get_status(self, args: Dict[str, Any]) -> str:
        category = args.get("category", "all")
        parts = []

        now = time.strftime("%I:%M %p, %A, %B %d, %Y")
        parts.append(f"Current Time: {now}")

        if category in ["all", "battery"]:
            if psutil and hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                if battery:
                    plugged = "charging" if battery.power_plugged else "on battery"
                    parts.append(f"Battery: {battery.percent}% ({plugged})")
                else:
                    parts.append("Battery: Desktop PC / Direct Power")

        if category in ["all", "performance"] and psutil:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            parts.append(f"CPU Usage: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024**2)}MB used)")

        if category in ["all", "running_apps"] and psutil:
            common_apps = ["chrome.exe", "brave.exe", "code.exe", "spotify.exe", "discord.exe", "notepad.exe"]
            running = set()
            for p in psutil.process_iter(["name"]):
                try:
                    pname = p.info["name"].lower() if p.info["name"] else ""
                    if pname in common_apps:
                        running.add(pname.replace(".exe", "").capitalize())
                except Exception:
                    pass
            if running:
                parts.append(f"Key Running Apps: {', '.join(sorted(running))}")

        return "; ".join(parts)

    def _tool_open_app(self, args: Dict[str, Any]) -> str:
        name = args.get("name", "").lower().strip()
        exe = self.APP_ALIASES.get(name, name)

        if exe.startswith("start "):
            os.system(exe)
            return f"Opened {name}."

        try:
            if shutil.which(exe):
                subprocess.Popen([exe], shell=True)
                return f"Successfully opened {name}."
            else:
                os.startfile(exe)
                return f"Successfully launched {name}."
        except Exception as e:
            # Try powershell start
            try:
                subprocess.Popen(["powershell", "-c", f"Start-Process '{name}'"], shell=True)
                return f"Launched {name} via PowerShell."
            except Exception:
                return f"Could not find or open application: {name}."

    def _tool_close_app(self, args: Dict[str, Any]) -> str:
        name = args.get("name", "").lower().strip()
        exe = self.APP_ALIASES.get(name, name)
        if not exe.endswith(".exe"):
            exe += ".exe"
        cmd = f"taskkill /IM {exe} /F"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return f"Closed {name}."
        return f"Application {name} was not running or could not be closed."

    def _tool_system_control(self, args: Dict[str, Any]) -> str:
        action = args.get("action", "")
        if action == "volume_up":
            if pyautogui:
                for _ in range(5):
                    pyautogui.press("volumeup")
            return "Volume increased."
        elif action == "volume_down":
            if pyautogui:
                for _ in range(5):
                    pyautogui.press("volumedown")
            return "Volume decreased."
        elif action in ["mute", "unmute"]:
            if pyautogui:
                pyautogui.press("volumemute")
            return f"Audio {'muted' if action == 'mute' else 'unmuted'}."
        elif action == "lock":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Workstation locked."
        elif action == "sleep":
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Putting computer to sleep."
        elif action == "shutdown":
            subprocess.run("shutdown /s /t 10", shell=True)
            return "System shutdown initiated."
        elif action == "restart":
            subprocess.run("shutdown /r /t 10", shell=True)
            return "System restart initiated."
        return f"Unknown system action: {action}"

    def _tool_file_op(self, args: Dict[str, Any]) -> str:
        action = args.get("action", "")
        path_str = args.get("path", "")
        dest_str = args.get("destination", "")
        p = Path(os.path.expandvars(path_str)).resolve()

        if action == "list":
            if not p.exists():
                return f"Path does not exist: {p}"
            if p.is_dir():
                items = [f.name + ("/" if f.is_dir() else "") for f in list(p.iterdir())[:15]]
                return f"Contents of {p.name}: {', '.join(items) if items else 'Empty directory'}"
            return f"{p.name} is a file ({p.stat().st_size} bytes)."

        elif action == "create_file":
            p.parent.mkdir(parents=True, exist_ok=True)
            content = dest_str or ""
            p.write_text(content, encoding="utf-8")
            return f"Created file at {p}."

        elif action == "create_dir":
            p.mkdir(parents=True, exist_ok=True)
            return f"Created directory at {p}."

        elif action == "delete":
            if not p.exists():
                return f"File does not exist: {p}"
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            return f"Deleted {p}."

        elif action == "move":
            if not dest_str:
                return "Destination path required for move operation."
            dest = Path(os.path.expandvars(dest_str)).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            return f"Moved {p.name} to {dest}."

        elif action == "search":
            search_dir = p if p.is_dir() else Path.home()
            pattern = f"*{dest_str or p.name}*"
            matches = [str(f) for f in search_dir.glob(pattern)][:5]
            return f"Found matches: {', '.join(matches)}" if matches else "No matching files found."

        return f"Unknown file action: {action}"

    def _tool_run_command(self, args: Dict[str, Any]) -> str:
        cmd = args.get("cmd", "")
        res = subprocess.run(["powershell", "-c", cmd], capture_output=True, text=True, timeout=15)
        out = res.stdout.strip() or res.stderr.strip() or "Command completed with no output."
        return out[:500]

    def _tool_keyboard_mouse(self, args: Dict[str, Any]) -> str:
        if not pyautogui:
            return "PyAutoGUI is not available."
        action = args.get("action", "")
        val = args.get("text_or_key", "")

        if action == "type":
            pyautogui.write(val, interval=0.03)
            return f"Typed text: '{val}'"
        elif action == "press_key":
            pyautogui.press(val)
            return f"Pressed key '{val}'"
        elif action == "click":
            pyautogui.click()
            return "Mouse clicked."
        return f"Unknown input action: {action}"

tool_executor = ToolExecutor()

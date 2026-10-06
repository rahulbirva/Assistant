"""
Tool definitions and execution layer for Jarvis (Phase 2 & Phase 4).
Supports function calling with safety gating for destructive actions and full computer control.
"""
import os
import re
import sys
import time
import shutil
import ctypes
import webbrowser
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from core.logger import logger
from core.spotify_client import spotify_controller
import config

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None


# OpenAI/Ollama compatible tool definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get real-time PC hardware and telemetry status: time, battery, CPU/RAM performance, Wi-Fi, and brightness. DO NOT use for definitions or general questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["all", "time", "battery", "performance", "network", "brightness", "running_apps"],
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
            "description": "Launch an application on Windows or open a website in the default browser (e.g. notepad, chrome, spotify, calculator, vscode, youtube, github, settings).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name or executable of the application, or website name/URL to launch (e.g. 'notepad', 'chrome', 'spotify', 'calculator', 'youtube', 'github', 'settings')."
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
                        "description": "Name of the application or process to close (e.g. 'notepad', 'chrome', 'spotify')."
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
            "description": "Control system hardware and states: volume up/down/mute, brightness up/down/set, lock workstation, sleep, shutdown, or restart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "volume_up", "volume_down", "mute", "unmute",
                            "brightness_up", "brightness_down", "brightness_set",
                            "lock", "sleep", "shutdown", "restart"
                        ],
                        "description": "The system control action to perform."
                    },
                    "value": {
                        "type": "string",
                        "description": "Optional numeric value for actions like 'brightness_set' (e.g., '70')."
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
                        "description": "Target file or folder path (supports ~ and environment variables)."
                    },
                    "destination": {
                        "type": "string",
                        "description": "Optional destination path for move operations, text content for create_file, or search query."
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
            "description": "Automate keyboard typing, shortcut key presses, mouse clicks, or scrolling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["type", "press_key", "hotkey", "click", "scroll"],
                        "description": "Action type: 'type' text, 'press_key' (e.g. enter, space), 'hotkey' (e.g. 'ctrl+c', 'win+d'), 'click', or 'scroll'."
                    },
                    "text_or_key": {
                        "type": "string",
                        "description": "The text to type or key/hotkey combination to press."
                    },
                    "value": {
                        "type": "string",
                        "description": "Optional scroll amount (e.g. '300' or '-300') or click target."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_on_text",
            "description": "Locate text visible on screen using computer vision OCR and click on it (e.g., 'click on search', 'click on videos', 'click on upload').",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_text": {
                        "type": "string",
                        "description": "The exact or partial text of the button, link, or label visible on screen to click."
                    }
                },
                "required": ["target_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_at_position",
            "description": "Click at specific screen pixel coordinates (X, Y) via mouse automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "The horizontal pixel coordinate."
                    },
                    "y": {
                        "type": "integer",
                        "description": "The vertical pixel coordinate."
                    }
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the active window or webpage up, down, left, or right.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right", "swipe_down", "swipe_up", "page_down", "page_up"],
                        "description": "Direction to scroll or swipe (e.g. 'down', 'up', 'page_down', 'page_up', 'swipe_down')."
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Number of scroll increments. Defaults to 2 for a full page view."
                    }
                },
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_control",
            "description": "Control music and media playback on Spotify or YouTube. Supports playing songs, pausing, resuming, skipping tracks, and querying what is playing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["spotify", "youtube"],
                        "description": "Target media platform: 'spotify' or 'youtube'."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["play", "search", "pause", "resume", "next", "previous", "current", "volume"],
                        "description": "Action to perform: 'play', 'search', 'pause', 'resume', 'next', 'previous', 'current' (what song is playing), or 'volume'."
                    },
                    "query": {
                        "type": "string",
                        "description": "The song title, artist, or YouTube video to play or search (required for play/search actions)."
                    },
                    "volume": {
                        "type": "integer",
                        "description": "Volume level (0 to 100) when action is 'volume'."
                    },
                    "index": {
                        "type": "integer",
                        "description": "Optional ordinal video number for YouTube (e.g. 1 for first video)."
                    }
                },
                "required": ["platform"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a Google search in browser ONLY when user explicitly asks to 'google <query>' or 'search Google for <query>'. NEVER use this for general questions or chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_screen",
            "description": "Inspect and describe all visible buttons, links, menus, and text options currently displayed on the user's screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "Optional focus area to inspect (e.g. 'all', 'options', 'buttons')."
                    }
                },
                "required": []
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
        "edge": "msedge.exe",
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
        "taskmgr": "taskmgr.exe",
        "settings": "start ms-settings:",
        "paint": "mspaint.exe",
    }

    WEB_SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "reddit": "https://www.reddit.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "gmail": "https://mail.google.com",
        "instagram": "https://www.instagram.com",
        "netflix": "https://www.netflix.com",
        "chatgpt": "https://chatgpt.com",
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
                return True, f"permanently delete the file or folder at '{path}'"

        elif name == "run_command":
            cmd = args.get("cmd", "").lower().strip()
            safe_prefixes = [
                "dir", "ls", "echo", "whoami", "ipconfig", "get-date",
                "hostname", "ping", "systeminfo", "get-process", "tasklist",
                "netsh", "pwd", "get-item"
            ]
            if not any(cmd.startswith(p) for p in safe_prefixes):
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

        # Time & Date
        if category in ["all", "time"]:
            now = time.strftime("%I:%M %p, %A, %B %d, %Y")
            parts.append(f"Current Time: {now}")

        # Battery
        if category in ["all", "battery"]:
            if psutil and hasattr(psutil, "sensors_battery"):
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        plugged = "charging" if battery.power_plugged else "on battery"
                        parts.append(f"Battery: {battery.percent}% ({plugged})")
                    else:
                        parts.append("Battery: Desktop PC / Direct Power")
                except Exception:
                    pass

        # CPU & Memory Performance
        if category in ["all", "performance"] and psutil:
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                parts.append(f"CPU Usage: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024**2)}MB used)")
            except Exception:
                pass

        # Network / Wi-Fi
        if category in ["all", "network"]:
            try:
                res = subprocess.run("netsh wlan show interfaces", shell=True, capture_output=True, text=True, timeout=5)
                output = res.stdout
                ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", output, re.MULTILINE)
                signal_match = re.search(r"^\s*Signal\s*:\s*(.+)$", output, re.MULTILINE)
                state_match = re.search(r"^\s*State\s*:\s*(.+)$", output, re.MULTILINE)

                if ssid_match and signal_match:
                    ssid = ssid_match.group(1).strip()
                    signal = signal_match.group(1).strip()
                    parts.append(f"Wi-Fi: Connected to '{ssid}' (Signal: {signal})")
                elif state_match:
                    parts.append(f"Wi-Fi State: {state_match.group(1).strip()}")
                else:
                    parts.append("Network: Connected")
            except Exception:
                parts.append("Network: Status unavailable")

        # Screen Brightness
        if category in ["all", "brightness"]:
            if sbc:
                try:
                    br = sbc.get_brightness()
                    if br:
                        level = br[0] if isinstance(br, list) else br
                        parts.append(f"Screen Brightness: {level}%")
                except Exception:
                    pass

        # Running Apps
        if category in ["all", "running_apps"] and psutil:
            common_apps = [
                "chrome.exe", "brave.exe", "msedge.exe", "code.exe",
                "spotify.exe", "discord.exe", "notepad.exe", "calc.exe", "calc.exe"
            ]
            running = set()
            try:
                for p in psutil.process_iter(["name"]):
                    try:
                        pname = p.info["name"].lower() if p.info and p.info["name"] else ""
                        if pname in common_apps:
                            running.add(pname.replace(".exe", "").capitalize())
                    except Exception:
                        pass
                if running:
                    parts.append(f"Key Running Apps: {', '.join(sorted(running))}")
            except Exception:
                pass

        return "; ".join(parts) if parts else "Status report unavailable."

    def _tool_open_app(self, args: Dict[str, Any]) -> str:
        name = args.get("name", "").lower().strip()
        if not name:
            return "Application name was not specified."

        # Check for web shortcuts or URLs
        if name in self.WEB_SHORTCUTS:
            url = self.WEB_SHORTCUTS[name]
            webbrowser.open(url)
            return f"Opened {name} in your browser."

        if name.startswith(("http://", "https://", "www.")) or any(name.endswith(ext) for ext in [".com", ".org", ".net", ".io", ".co"]):
            url = name if name.startswith("http") else f"https://{name}"
            webbrowser.open(url)
            return f"Opened {url} in your browser."

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
        except Exception:
            # Fallback to powershell Start-Process
            try:
                subprocess.Popen(["powershell", "-c", f"Start-Process '{name}'"], shell=True)
                return f"Launched {name} via Windows shell."
            except Exception as e:
                return f"Could not find or open application: {name}."

    def _tool_close_app(self, args: Dict[str, Any]) -> str:
        name = args.get("name", "").lower().strip()
        if not name:
            return "Application name was not specified."

        exe = self.APP_ALIASES.get(name, name)
        if not exe.endswith(".exe") and not exe.startswith("start "):
            exe += ".exe"

        cmd = f"taskkill /IM {exe} /F"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return f"Closed {name}."

        # Try matching via psutil if name didn't match directly
        if psutil:
            closed_count = 0
            for proc in psutil.process_iter(["name"]):
                try:
                    pname = proc.info["name"].lower() if proc.info and proc.info["name"] else ""
                    if name in pname:
                        proc.terminate()
                        closed_count += 1
                except Exception:
                    pass
            if closed_count > 0:
                return f"Terminated {closed_count} processes for {name}."

        return f"Application {name} was not running or could not be closed."

    def _tool_system_control(self, args: Dict[str, Any]) -> str:
        action = args.get("action", "").lower().strip()
        val_str = args.get("value", "")

        # Volume control using native Windows keybd_event (instant, zero failsafe triggers)
        VK_VOLUME_MUTE = 0xAD
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_UP = 0xAF

        if action == "volume_up":
            for _ in range(5):
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
            return "Volume increased."
        elif action == "volume_down":
            for _ in range(5):
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
            return "Volume decreased."
        elif action in ["mute", "unmute"]:
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            return f"Audio {'muted' if action == 'mute' else 'unmuted'}."

        # Brightness control
        elif action in ["brightness_up", "brightness_down", "brightness_set"]:
            if not sbc:
                return "Screen brightness control is not available on this display."
            try:
                curr_list = sbc.get_brightness()
                curr = curr_list[0] if isinstance(curr_list, list) and curr_list else 50
                if action == "brightness_up":
                    new_val = min(100, curr + 15)
                elif action == "brightness_down":
                    new_val = max(0, curr - 15)
                else:  # brightness_set
                    try:
                        new_val = max(0, min(100, int(val_str))) if val_str else curr
                    except ValueError:
                        new_val = curr
                sbc.set_brightness(new_val)
                return f"Screen brightness set to {new_val}%."
            except Exception as e:
                return f"Failed to adjust brightness: {e}"

        # Workstation Lock
        elif action == "lock":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Workstation locked."

        # Sleep
        elif action == "sleep":
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Putting computer to sleep."

        # Shutdown & Restart (destructively gated)
        elif action == "shutdown":
            subprocess.run("shutdown /s /t 15", shell=True)
            return "System shutdown initiated."
        elif action == "restart":
            subprocess.run("shutdown /r /t 15", shell=True)
            return "System restart initiated."

        return f"Unknown system action: {action}"

    def _tool_file_op(self, args: Dict[str, Any]) -> str:
        action = args.get("action", "").lower().strip()
        path_str = args.get("path", "").strip()
        dest_str = args.get("destination", "").strip()

        if not path_str:
            return "Error: File path is required."

        expanded_path = os.path.expanduser(os.path.expandvars(path_str))
        p = Path(expanded_path).resolve()

        if action == "list":
            if not p.exists():
                return f"Path does not exist: {p}"
            if p.is_dir():
                items = []
                for item in list(p.iterdir())[:20]:
                    if item.is_dir():
                        items.append(f"[DIR] {item.name}")
                    else:
                        size_kb = item.stat().st_size / 1024
                        items.append(f"{item.name} ({size_kb:.1f} KB)")
                return f"Contents of {p.name}: {', '.join(items) if items else 'Empty directory'}"
            return f"{p.name} is a file ({p.stat().st_size} bytes)."

        elif action == "create_file":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(dest_str, encoding="utf-8")
            return f"Created file at {p} with {len(dest_str)} characters."

        elif action == "create_dir":
            p.mkdir(parents=True, exist_ok=True)
            return f"Created directory at {p}."

        elif action == "delete":
            if not p.exists():
                return f"Path does not exist: {p}"
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            return f"Successfully deleted {p}."

        elif action == "move":
            if not dest_str:
                return "Destination path is required for move/rename."
            dest_p = Path(os.path.expanduser(os.path.expandvars(dest_str))).resolve()
            dest_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest_p))
            return f"Moved {p.name} to {dest_p}."

        elif action == "search":
            search_dir = p if p.is_dir() else Path.home()
            query = dest_str or p.name
            matches = [str(f.name) for f in search_dir.glob(f"*{query}*")][:10]
            return f"Found matches in {search_dir.name}: {', '.join(matches)}" if matches else f"No matches found for '{query}'."

        return f"Unknown file action: {action}"

    def _tool_run_command(self, args: Dict[str, Any]) -> str:
        cmd = args.get("cmd", "").strip()
        if not cmd:
            return "Command string is empty."
        try:
            res = subprocess.run(["powershell", "-c", cmd], capture_output=True, text=True, timeout=15)
            out = res.stdout.strip() or res.stderr.strip() or "Command completed with no output."
            return out[:500]
        except subprocess.TimeoutExpired:
            return "Command execution timed out after 15 seconds."
        except Exception as e:
            return f"Execution failed: {str(e)}"

    def _tool_keyboard_mouse(self, args: Dict[str, Any]) -> str:
        if not pyautogui:
            return "PyAutoGUI automation is not available."

        action = args.get("action", "").lower().strip()
        val = args.get("text_or_key", "").strip()
        extra_val = args.get("value", "").strip()

        if action == "type":
            if not val:
                return "No text provided to type."
            pyautogui.write(val, interval=0.02)
            return f"Typed: '{val}'"

        elif action == "press_key":
            if not val:
                return "No key specified to press."
            pyautogui.press(val.lower())
            return f"Pressed key '{val}'"

        elif action == "hotkey":
            if not val:
                return "No hotkey combination specified."
            # Split 'ctrl+c' or 'ctrl, c'
            keys = [k.strip().lower() for k in re.split(r"[+,]", val) if k.strip()]
            pyautogui.hotkey(*keys)
            return f"Triggered hotkey combination: {' + '.join(keys)}"

        elif action == "click":
            pyautogui.click()
            return "Mouse clicked."

        elif action == "scroll":
            try:
                clicks = int(extra_val or val or 300)
                pyautogui.scroll(clicks)
                return f"Scrolled mouse {'up' if clicks > 0 else 'down'} by {abs(clicks)} units."
            except ValueError:
                return "Invalid scroll value."

        return f"Unknown input action: {action}"

    def _tool_click_on_text(self, args: Dict[str, Any]) -> str:
        target = args.get("target_text", "").strip()
        if not target:
            return "No target text provided to click on."

        from core.screen_monitor import screen_monitor
        logger.log("ACTION", f"[SEEING] Searching screen for text: '{target}'...")
        match = screen_monitor.find_text(target)

        if match:
            cx, cy = match["center"]
            matched_txt = match["text"]
            logger.log("ACTION", f"[CLICKING] Found text '{matched_txt}' at position ({cx}, {cy}) — clicking.")
            if pyautogui:
                pyautogui.click(cx, cy)
            return f"Clicked on '{matched_txt}' at screen position ({cx}, {cy})."
        else:
            _, results, summary = screen_monitor.get_latest_data()
            items = [f"'{r['text']}'" for r in results[:8]]
            visible_str = f"Visible elements: {', '.join(items)}" if items else "No clear text detected."
            return f"I don't see '{target}' on the screen. {visible_str}"

    def _tool_click_at_position(self, args: Dict[str, Any]) -> str:
        try:
            x = int(args.get("x", 0))
            y = int(args.get("y", 0))
        except (ValueError, TypeError):
            return "Invalid X or Y coordinates provided."

        logger.log("ACTION", f"[CLICKING] Clicked at ({x}, {y})")
        if pyautogui:
            pyautogui.click(x, y)
        return f"Clicked at coordinates ({x}, {y})."

    def _tool_scroll(self, args: Dict[str, Any]) -> str:
        direction = args.get("direction", "down").lower().strip()
        try:
            amount = int(args.get("amount", 2))
        except (ValueError, TypeError):
            amount = 2

        if not pyautogui:
            return "PyAutoGUI is not available."

        # High-magnitude scroll (each increment is ~650 units for visible page movement)
        scroll_units = max(1, amount) * 650

        if direction in ("down", "page_down", "swipe_down", "swipe"):
            pyautogui.scroll(-scroll_units)
            if amount >= 2:
                pyautogui.press("pagedown")
            logger.log("ACTION", f"[SCROLLING] Scrolled down by {scroll_units} units")
            return f"Scrolled down the page."
        elif direction in ("up", "page_up", "swipe_up"):
            pyautogui.scroll(scroll_units)
            if amount >= 2:
                pyautogui.press("pageup")
            logger.log("ACTION", f"[SCROLLING] Scrolled up by {scroll_units} units")
            return f"Scrolled up the page."
        elif direction == "left":
            pyautogui.hscroll(-scroll_units)
            return "Scrolled left."
        elif direction == "right":
            pyautogui.hscroll(scroll_units)
            return "Scrolled right."
        else:
            pyautogui.scroll(-scroll_units)
            return f"Scrolled {direction}."

    def _tool_media_control(self, args: Dict[str, Any]) -> str:
        import threading
        import urllib.parse
        import urllib.request

        platform = args.get("platform", "youtube").lower().strip()
        query = args.get("query", "").strip()
        action = args.get("action", "play").lower().strip()
        try:
            target_idx = int(args.get("index", 1))
        except (ValueError, TypeError):
            target_idx = 1

        if "spotify" in platform:
            logger.log("ACTION", f"Processing Spotify media command: action={action}, query='{query}'")

            # 1. Playback Pause
            if action in ("pause", "stop"):
                if spotify_controller.is_configured():
                    return spotify_controller.pause()
                if pyautogui:
                    pyautogui.press("playpause")
                    return "Sent pause command to media player."
                return "Spotify pause command dispatched."

            # 2. Playback Resume
            if action == "resume":
                if spotify_controller.is_configured():
                    return spotify_controller.resume()
                if pyautogui:
                    pyautogui.press("playpause")
                    return "Sent resume command to media player."
                return "Spotify resume command dispatched."

            # 3. Next Track
            if action in ("next", "skip"):
                if spotify_controller.is_configured():
                    return spotify_controller.next_track()
                if pyautogui:
                    pyautogui.press("nexttrack")
                    return "Skipped to next track via media key."
                return "Next track command sent."

            # 4. Previous Track
            if action in ("previous", "prev", "back"):
                if spotify_controller.is_configured():
                    return spotify_controller.previous_track()
                if pyautogui:
                    pyautogui.press("prevtrack")
                    return "Skipped to previous track via media key."
                return "Previous track command sent."

            # 5. What's Playing (Current Track Info)
            if action in ("current", "info", "what"):
                if spotify_controller.is_configured():
                    info = spotify_controller.get_current_track()
                    return f"Currently playing on Spotify: {info}" if info else "No song currently playing on Spotify."
                return "Spotify API credentials required in config.py to query current track metadata."

            # 6. Volume Control
            if action == "volume":
                vol = args.get("volume", 50)
                if spotify_controller.is_configured():
                    return spotify_controller.set_volume(vol)
                return self._tool_system_control({"action": "set_volume", "level": vol})

            # 7. Play / Search Song
            if not query:
                if action == "play":
                    if spotify_controller.is_configured():
                        return spotify_controller.resume()
                    if pyautogui:
                        pyautogui.press("playpause")
                        return "Resumed Spotify playback."
                return "Please specify a song, artist, or playlist to play on Spotify."

            # If Spotify API is configured, use the Web API directly
            if spotify_controller.is_configured():
                return spotify_controller.play(query)

            # Fallback mode: Desktop app URI search + Enter
            encoded = urllib.parse.quote(query)
            try:
                subprocess.Popen(["powershell", "-c", f"Start-Process 'spotify:search:{encoded}'"], shell=True)
                if action == "play":
                    def _do_play_spotify():
                        time.sleep(1.8)
                        if pyautogui:
                            pyautogui.press("enter")
                    threading.Thread(target=_do_play_spotify, daemon=True).start()
                    return f"Playing '{query}' on Spotify desktop app. (Tip: add Spotify API keys in config.py for instant background control)."
                return f"Opened Spotify search for '{query}'."
            except Exception:
                webbrowser.open(f"https://open.spotify.com/search/{encoded}")
                return f"Opened Spotify search for '{query}' in browser."

        elif "youtube" in platform:
            logger.log("ACTION", f"Processing YouTube '{query}' (action={action}, index={target_idx})")
            if action == "play":
                # Instant direct playback: extract exact watch URL and launch
                watch_url = None
                try:
                    req = urllib.request.Request(
                        f"https://www.youtube.com/results?search_query={encoded}",
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    )
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        html = resp.read().decode("utf-8", errors="ignore")
                        video_ids = []
                        for vid in re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html):
                            if vid not in video_ids:
                                video_ids.append(vid)

                        if video_ids:
                            chosen_idx = max(0, min(len(video_ids) - 1, target_idx - 1))
                            chosen_id = video_ids[chosen_idx]
                            watch_url = f"https://www.youtube.com/watch?v={chosen_id}"
                except Exception as ex:
                    logger.log("WARN", f"Direct YouTube lookup error: {ex}")

                if watch_url:
                    webbrowser.open(watch_url)
                    ordinal = "first" if target_idx == 1 else f"number {target_idx}"
                    return f"Playing {ordinal} YouTube video for '{query}'."
                else:
                    # Fallback to search results + auto click
                    webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
                    def _do_click_first():
                        time.sleep(2.5)
                        from core.screen_monitor import screen_monitor
                        match = screen_monitor.find_text("first video")
                        if match and pyautogui:
                            cx, cy = match["center"]
                            pyautogui.click(cx, cy)
                    threading.Thread(target=_do_click_first, daemon=True).start()
                    return f"Searching YouTube for '{query}' and playing the top result."

            # action == "search"
            webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
            return f"Opened YouTube search results for '{query}'."

        return f"Unsupported platform: {platform}"

    def _tool_media_search(self, args: Dict[str, Any]) -> str:
        """Alias for backward compatibility with Ollama tool calling."""
        return self._tool_media_control(args)

    def _tool_web_search(self, args: Dict[str, Any]) -> str:
        import urllib.parse
        query = args.get("query", "").strip()
        if not query:
            return "No search query provided."
        encoded = urllib.parse.quote(query)
        webbrowser.open(f"https://www.google.com/search?q={encoded}")
        return f"Opened Google search for '{query}'."

    def _tool_read_screen(self, args: Dict[str, Any]) -> str:
        from core.screen_monitor import screen_monitor
        img, results = screen_monitor.capture_now()
        if not results:
            return "I could not detect any readable text on the screen right now."
        return screen_monitor.latest_summary


tool_executor = ToolExecutor()


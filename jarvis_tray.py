"""
System Tray Icon for Jarvis (Phase 5).
Manages tray icon states (IDLE, LISTENING, THINKING, SPEAKING, LOCKED, SEEING, PAUSED),
context menu actions, and launches GUI viewers in separate threads.
"""
import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable
from PIL import Image, ImageDraw

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import logger
import config

try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None


class JarvisTrayIcon:
    """Manages the Windows system tray icon and state indicators."""

    COLORS = {
        "IDLE": ("#4b5563", "#9ca3af"),       # Gray / Slate
        "LISTENING": ("#0284c7", "#38bdf8"),  # Cyan
        "THINKING": ("#d97706", "#facc15"),   # Yellow / Gold
        "SPEAKING": ("#16a34a", "#4ade80"),   # Lime Green
        "LOCKED": ("#dc2626", "#ef4444"),     # Crimson Red
        "SEEING": ("#9333ea", "#c084fc"),     # Purple
        "PAUSED": ("#6b7280", "#4b5563"),     # Dim Dark Gray
    }

    def __init__(
        self,
        on_pause: Optional[Callable[[], None]] = None,
        on_resume: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_quit = on_quit

        self.current_state = "IDLE"
        self.last_action = "System initialized"
        self.is_paused = False

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _create_icon_image(self, state: str) -> Image.Image:
        """Generates a 64x64 anti-aliased circular status icon with inner glow."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        dark_col, bright_col = self.COLORS.get(state, self.COLORS["IDLE"])

        # Outer glowing ring
        draw.ellipse([4, 4, size - 4, size - 4], fill=dark_col, outline=bright_col, width=3)
        # Inner core
        draw.ellipse([16, 16, size - 16, size - 16], fill=bright_col)
        # Center pip
        draw.ellipse([26, 26, size - 26, size - 26], fill="#ffffff")

        return img

    def _build_menu(self):
        """Constructs the right-click tray context menu."""
        return pystray.Menu(
            item("📌 Pause Listening", self._menu_pause, checked=lambda item: self.is_paused),
            item("▶️ Resume Listening", self._menu_resume, enabled=lambda item: self.is_paused),
            pystray.Menu.SEPARATOR,
            item("📋 Show Log", self._open_log_viewer),
            item("🖥️ Show Screen", self._open_screen_viewer),
            pystray.Menu.SEPARATOR,
            item("❌ Quit Jarvis", self._menu_quit)
        )

    def _menu_pause(self, icon=None, item=None):
        self.is_paused = True
        self.set_state("PAUSED", "Listening paused by user")
        if self.on_pause:
            self.on_pause()

    def _menu_resume(self, icon=None, item=None):
        self.is_paused = False
        self.set_state("IDLE", "Listening resumed")
        if self.on_resume:
            self.on_resume()

    def _menu_quit(self, icon=None, item=None):
        logger.log("ACTION", "Tray quit selected by user. Initiating graceful shutdown...")
        if self._icon:
            self._icon.stop()
        if self.on_quit:
            self.on_quit()

    def _open_log_viewer(self, icon=None, item=None):
        """Spawns the log viewer in a non-blocking process."""
        try:
            viewer_script = PROJECT_ROOT / "jarvis_log_viewer.py"
            python_exe = sys.executable
            subprocess.Popen([python_exe, str(viewer_script)])
        except Exception as e:
            logger.log("ERROR", f"Could not launch log viewer: {e}")

    def _open_screen_viewer(self, icon=None, item=None):
        """Spawns the screen vision viewer in a non-blocking process."""
        try:
            viewer_script = PROJECT_ROOT / "jarvis_screen_viewer.py"
            python_exe = sys.executable
            subprocess.Popen([python_exe, str(viewer_script)])
        except Exception as e:
            logger.log("ERROR", f"Could not launch screen viewer: {e}")

    def set_state(self, state: str, message: Optional[str] = None):
        """Thread-safe update of tray icon color and tooltip."""
        self.current_state = state.upper()
        if message:
            self.last_action = message

        if self._icon:
            try:
                new_img = self._create_icon_image(self.current_state)
                self._icon.icon = new_img
                tooltip = f"Jarvis: {self.current_state}\n{self.last_action[:50]}"
                self._icon.title = tooltip
            except Exception:
                pass

    def start(self):
        """Starts the pystray icon in a separate daemon thread."""
        if not pystray:
            logger.log("WARN", "pystray is not installed. System tray icon will not be displayed.")
            return

        def _run_tray():
            initial_img = self._create_icon_image(self.current_state)
            menu = self._build_menu()
            self._icon = pystray.Icon(
                name="JarvisAI",
                icon=initial_img,
                title="Jarvis — Offline AI Assistant (Ready)",
                menu=menu
            )
            # Default action on double-click
            self._icon.default_action = self._open_log_viewer
            self._icon.run()

        self._thread = threading.Thread(target=_run_tray, daemon=True, name="TrayIconThread")
        self._thread.start()
        logger.log("INFO", "System tray icon initialized and running.")

    def stop(self):
        """Stops the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass


# Global singleton
tray_icon = JarvisTrayIcon()

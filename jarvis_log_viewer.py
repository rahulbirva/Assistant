"""
Log Viewer Window for Jarvis (Phase 5).
Live-tails logs/jarvis_activity.log with colored state indicators in an always-on-top window.
"""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config

LOG_FILE = PROJECT_ROOT / "logs" / "jarvis_activity.log"


class JarvisLogViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JARVIS — Activity Log")
        self.root.geometry("520x380")
        self.root.configure(bg="#0d1117")
        self.root.attributes("-topmost", True)

        # Header bar
        header_frame = tk.Frame(root, bg="#161b22", height=36)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        title_lbl = tk.Label(
            header_frame,
            text="● JARVIS AUDIT LOG (LIVE TAIL)",
            font=("Consolas", 10, "bold"),
            fg="#58a6ff",
            bg="#161b22",
            padx=10,
            pady=8
        )
        title_lbl.pack(side=tk.LEFT)

        # Scrolled Text Widget
        self.text_area = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            bg="#0d1117",
            fg="#c9d1d9",
            font=("Consolas", 9),
            insertbackground="#58a6ff",
            selectbackground="#1f6feb",
            padx=8,
            pady=8,
            relief=tk.FLAT
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # Tag configurations for color-coded states
        self.text_area.tag_config("timestamp", foreground="#8b949e")
        self.text_area.tag_config("LISTENING", foreground="#38bdf8", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("THINKING", foreground="#facc15", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("SPEAKING", foreground="#4ade80", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("SEEING", foreground="#c084fc", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("CLICKING", foreground="#fb923c", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("SCROLLING", foreground="#67e8f9", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("ACTION", foreground="#34d399", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("SUCCESS", foreground="#22c55e", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("WARN", foreground="#fbbf24", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("ERROR", foreground="#f87171", font=("Consolas", 9, "bold"))
        self.text_area.tag_config("LOCKED", foreground="#ef4444", font=("Consolas", 9, "bold"))

        # Footer control frame
        footer = tk.Frame(root, bg="#161b22", height=32)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_lbl = tk.Label(footer, text="Auto-tail active (1.5s)", font=("Consolas", 8), fg="#8b949e", bg="#161b22")
        self.status_lbl.pack(side=tk.LEFT, padx=10, pady=4)

        refresh_btn = tk.Button(
            footer, text="Refresh", font=("Consolas", 8),
            bg="#21262d", fg="#c9d1d9", activebackground="#30363d",
            relief=tk.FLAT, command=self.load_log
        )
        refresh_btn.pack(side=tk.RIGHT, padx=6, pady=4)

        self.last_content = ""
        self.load_log()
        self.poll_log()

    def load_log(self):
        """Reads the last 30 lines of the log file and renders with syntax coloring."""
        if not LOG_FILE.exists():
            return

        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            recent_lines = lines[-25:] if len(lines) > 25 else lines
            content = "".join(recent_lines)

            if content == self.last_content:
                return
            self.last_content = content

            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete("1.0", tk.END)

            for line in recent_lines:
                self._insert_colored_line(line)

            self.text_area.see(tk.END)
            self.text_area.config(state=tk.DISABLED)
        except Exception as e:
            pass

    def _insert_colored_line(self, line: str):
        """Parses a log line and inserts with appropriate tag colors."""
        # Standard format: [14:32:05] [STATE    ] Message
        line_clean = line.rstrip("\n")
        parts = line_clean.split("] ", 2)

        if len(parts) >= 2 and parts[0].startswith("[") and parts[1].startswith("["):
            timestamp = parts[0] + "] "
            state_raw = parts[1].replace("[", "").replace("]", "").strip()
            msg = "] " + parts[2] if len(parts) > 2 else ""

            self.text_area.insert(tk.END, timestamp, "timestamp")
            self.text_area.insert(tk.END, f"[{state_raw:<8}]", state_raw)
            self.text_area.insert(tk.END, f" {parts[2] if len(parts) > 2 else ''}\n")
        else:
            self.text_area.insert(tk.END, line_clean + "\n")

    def poll_log(self):
        """Polls for log updates every 1.5 seconds."""
        self.load_log()
        self.root.after(1500, self.poll_log)


def show_log_viewer():
    """Entry point to launch the log viewer."""
    root = tk.Tk()
    app = JarvisLogViewer(root)
    root.mainloop()


if __name__ == "__main__":
    show_log_viewer()

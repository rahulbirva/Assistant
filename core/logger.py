"""
Logger module for Jarvis activity and performance tracking.
"""
import sys
import logging
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style

import config

init(autoreset=True)

class JarvisLogger:
    """Handles formatted console output and persistent file logging."""
    def __init__(self, log_file: Path = config.ACTIVITY_LOG_FILE):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure file logger
        self.logger = logging.getLogger("JarvisLogger")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            fh = logging.FileHandler(self.log_file, encoding="utf-8")
            fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

    def log(self, category: str, message: str, level: str = "INFO"):
        """Logs to file and console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Console colors
        color_map = {
            "IDLE": Fore.LIGHTBLACK_EX,
            "LISTENING": Fore.CYAN,
            "HEARD": Fore.GREEN,
            "THINKING": Fore.YELLOW,
            "SPEAKING": Fore.MAGENTA,
            "ACTION": Fore.BLUE,
            "WARN": Fore.LIGHTRED_EX,
            "ERROR": Fore.RED,
            "LATENCY": Fore.LIGHTGREEN_EX,
            "INFO": Fore.WHITE,
        }
        
        color = color_map.get(category.upper(), Fore.WHITE)
        prefix = f"[{timestamp}] [{category.upper():<9}]"
        print(f"{color}{prefix} {message}{Style.RESET_ALL}")
        
        # File log
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"[{category.upper()}] {message}")

    def log_latency(self, stt_ms: float, process_ms: float, tts_ms: float, total_ms: float):
        """Logs round-trip latency statistics."""
        msg = (
            f"Latency breakdown: STT: {stt_ms:.1f}ms | "
            f"Process: {process_ms:.1f}ms | "
            f"TTS start: {tts_ms:.1f}ms | "
            f"Total Round-Trip: {total_ms:.1f}ms"
        )
        self.log("LATENCY", msg)

logger = JarvisLogger()

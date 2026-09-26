"""
JARVIS Background Daemon & Windows Service Entry Point (Phase 5).
Manages silent background execution, hides console window, coordinates voice loop,
biometric face gate, screen monitor, and system tray status indicators.
"""
import os
import sys
import time
import signal
import ctypes
import argparse
import threading
from pathlib import Path
from typing import Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from core.logger import logger
from core.stt import STTEngine
from core.tts import TTSEngine
from core.audio import AudioRecorder
from core.llm import OllamaBrain
from core.tools import tool_executor
if not getattr(config, "FACE_GATE_BYPASS", False):
    from core.face_gate import face_gate
else:
    face_gate = None
from core.screen_monitor import screen_monitor
from jarvis_tray import tray_icon
import hud_server


class ServiceState:
    """Thread-safe state manager for the Jarvis background service."""

    def __init__(self):
        self.state = "IDLE"
        self.last_command = ""
        self.last_action = "Jarvis initialized"
        self.is_paused = False
        self._lock = threading.Lock()

    def update(self, state: str, message: Optional[str] = None):
        with self._lock:
            self.state = state.upper()
            if message:
                self.last_action = message
            tray_icon.set_state(self.state, self.last_action)
            hud_server.update_status(self.state, self.last_action)
            logger.log("ACTION", f"Service state: [{self.state}] {self.last_action}")


class JarvisDaemon:
    """Main background coordinator for all Jarvis subsystems."""

    def __init__(self, show_console: bool = False, enable_tray: bool = True):
        self.show_console = show_console
        self.enable_tray = enable_tray
        self.running = False
        self.service_state = ServiceState()

        # Hide console window if requested
        if not self.show_console and sys.platform == "win32":
            self._hide_console()

        logger.log("INFO", "Initializing Jarvis Service Core...")

        # 1. Voice Core
        self.tts = TTSEngine()
        self.stt = STTEngine()
        self.recorder = AudioRecorder()

        # 2. Local LLM Brain
        self.brain = OllamaBrain(model=config.OLLAMA_MODEL)

        # Wire Tray callbacks
        tray_icon.on_pause = self._on_pause
        tray_icon.on_resume = self._on_resume
        tray_icon.on_quit = self.stop

    def _hide_console(self):
        """Hides the Windows command prompt window."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
                logger.log("INFO", "Console window hidden for silent background operation.")
        except Exception as e:
            logger.log("WARN", f"Could not hide console window: {e}")

    def _on_pause(self):
        logger.log("INFO", "Voice listening paused via system tray.")
        self.service_state.is_paused = True

    def _on_resume(self):
        logger.log("INFO", "Voice listening resumed via system tray.")
        self.service_state.is_paused = False

    def start(self):
        """Starts all background worker threads and the main voice loop."""
        self.running = True
        logger.log("SUCCESS", "JARVIS Background Daemon is active and operational.")

        # Start HUD WebSocket bridge
        try:
            hud_server.start()
            hud_server.set_model(config.OLLAMA_MODEL)
        except Exception as e:
            logger.log("WARN", f"HUD server start notice: {e}")

        # Start Screen Monitor
        try:
            screen_monitor.start()
            hud_server.set_ocr_active(True)
        except Exception as e:
            logger.log("WARN", f"Screen monitor start notice: {e}")

        # Start Biometric Face Gate Scanner (skip if bypass is on)
        if getattr(config, "FACE_RECOGNITION_ENABLED", True) and not getattr(config, "FACE_GATE_BYPASS", False):
            try:
                face_gate.start_background_scanner()
            except Exception as e:
                logger.log("WARN", f"Face gate scanner start notice: {e}")
        elif getattr(config, "FACE_GATE_BYPASS", False):
            logger.log("INFO", "Face gate BYPASSED — webcam scanner disabled.")

        # Start System Tray Icon
        if self.enable_tray:
            try:
                tray_icon.start()
            except Exception as e:
                logger.log("WARN", f"Tray icon start notice: {e}")

        # Spoken greeting
        self.service_state.update("SPEAKING", "Jarvis online")
        self.tts.speak(f"{config.ASSISTANT_NAME} is online and at your service, {config.USER_NAME}.", wait=True)
        self.service_state.update("IDLE", "Standing by")

        # Start Main Voice Daemon Loop
        self._voice_loop()

    def _voice_loop(self):
        """Continuous listening and response cycle."""
        logger.log("INFO", "Listening for voice input...")

        while self.running:
            if self.service_state.is_paused:
                time.sleep(0.5)
                continue

            try:
                # 1. Listen for utterance via VAD
                audio_data = self.recorder.listen_utterance()
                if audio_data is None or len(audio_data) == 0:
                    continue

                if not self.running:
                    break

                # 2. State: LISTENING -> Transcribe Speech
                self.service_state.update("LISTENING", "Processing voice input...")
                text, stt_ms = self.stt.transcribe(audio_data)
                clean_text = text.strip()

                if not clean_text:
                    self.service_state.update("IDLE", "Standing by")
                    continue

                logger.log("USER", f"Heard: '{clean_text}' ({stt_ms:.1f}ms)")
                hud_server.add_conversation("user", clean_text)
                self.service_state.last_command = clean_text

                # Check wake word requirement if enabled
                if getattr(config, "REQUIRE_WAKE_WORD", False):
                    matched = any(clean_text.lower().startswith(w) for w in config.WAKE_WORDS)
                    if not matched:
                        self.service_state.update("IDLE", "Standing by")
                        continue

                # 3. Biometric Security Gate Check
                bypass = getattr(config, "FACE_GATE_BYPASS", False)
                is_auth = True if bypass else (
                    face_gate.is_authorized() if getattr(config, "FACE_RECOGNITION_ENABLED", True) else True
                )
                if not is_auth:
                    self.service_state.update("LOCKED", "Biometric authorization required")
                else:
                    # 4. Check if vision / screen analysis needed
                    vision_kws = ["screen", "click", "scroll", "see", "look", "button", "find"]
                    if any(kw in clean_text.lower() for kw in vision_kws):
                        self.service_state.update("SEEING", f"Analyzing screen for '{clean_text[:25]}'...")
                    else:
                        self.service_state.update("THINKING", f"Reasoning: '{clean_text[:25]}'...")

                # 5. LLM Reasoning & Tool Execution
                spoken_response, llm_ms = self.brain.think_and_respond(clean_text)
                logger.log("SUCCESS", f"Response generated ({llm_ms:.1f}ms): {spoken_response}")
                hud_server.add_conversation("jarvis", spoken_response)

                # 6. State: SPEAKING -> Read aloud
                self.service_state.update("SPEAKING", spoken_response[:40])
                self.tts.speak(spoken_response, wait=True)

                # Return to IDLE
                self.service_state.update("IDLE", "Standing by")

            except Exception as e:
                logger.log("ERROR", f"Error in voice daemon loop: {e}")
                self.service_state.update("IDLE", f"Recovered from error: {e}")
                time.sleep(1.0)

    def stop(self):
        """Gracefully shuts down all workers and handles."""
        if not self.running:
            return
        logger.log("ACTION", "Shutting down Jarvis Background Service...")
        self.running = False

        try:
            screen_monitor.stop()
        except Exception:
            pass

        try:
            face_gate.stop_scanner()
        except Exception:
            pass

        try:
            self.tts.stop()
        except Exception:
            pass

        try:
            tray_icon.stop()
        except Exception:
            pass

        logger.log("SUCCESS", "Jarvis service terminated cleanly.")
        sys.exit(0)


def setup_signal_handlers(daemon: JarvisDaemon):
    """Binds OS signals to graceful shutdown."""
    def _handler(sig, frame):
        daemon.stop()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def main():
    parser = argparse.ArgumentParser(description="Jarvis Background Service Daemon")
    parser.add_argument("--show-console", action="store_true", help="Keep the command prompt window visible")
    parser.add_argument("--no-tray", action="store_true", help="Disable the system tray icon")
    args = parser.parse_args()

    daemon = JarvisDaemon(show_console=args.show_console, enable_tray=not args.no_tray)
    setup_signal_handlers(daemon)
    daemon.start()


if __name__ == "__main__":
    main()

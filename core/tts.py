"""
Offline instant Text-to-Speech (TTS) using pyttsx3 and Windows SAPI5.
"""
import queue
import threading
import time
from typing import Callable, Optional
import pyttsx3

import config
from core.logger import logger

class TTSEngine:
    """Thread-safe Text-to-Speech worker using pyttsx3."""
    
    def __init__(
        self,
        rate: int = config.TTS_RATE,
        volume: float = config.TTS_VOLUME,
        voice_index: int = config.TTS_VOICE_INDEX,
        on_start_speaking: Optional[Callable[[], None]] = None,
        on_finish_speaking: Optional[Callable[[], None]] = None,
    ):
        self.rate = rate
        self.volume = volume
        self.voice_index = voice_index
        self.on_start = on_start_speaking
        self.on_finish = on_finish_speaking
        
        self.queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self.is_speaking = False
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True, name="TTS-Worker")
        self.worker_thread.start()

    def _run_loop(self):
        """Worker thread dedicated to pyttsx3 loop."""
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            
            voices = engine.getProperty("voices")
            if voices and self.voice_index < len(voices):
                engine.setProperty("voice", voices[self.voice_index].id)
                logger.log("INFO", f"TTS initialized with voice: {voices[self.voice_index].name}")
        except Exception as e:
            logger.log("ERROR", f"Failed to initialize pyttsx3 engine: {e}")
            return

        while not self._stop_event.is_set():
            try:
                task = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if task is None:
                self.queue.task_done()
                break

            text, done_event = task
            if text and text.strip():
                try:
                    self.is_speaking = True
                    logger.log("SPEAKING", text)
                    if self.on_start:
                        try:
                            self.on_start()
                        except Exception:
                            pass
                    
                    engine.say(text)
                    engine.runAndWait()
                except Exception as ex:
                    logger.log("ERROR", f"TTS speak error: {ex}")
                finally:
                    self.is_speaking = False
                    if self.on_finish:
                        try:
                            self.on_finish()
                        except Exception:
                            pass

            if done_event is not None:
                done_event.set()
            self.queue.task_done()

    def speak(self, text: str, wait: bool = True):
        """
        Enqueues text for spoken output.
        If wait=True, blocks until speech finishes.
        """
        if not text or not text.strip():
            return
            
        done_event = threading.Event() if wait else None
        self.queue.put((text.strip(), done_event))
        
        if wait and done_event is not None:
            done_event.wait()

    def stop(self):
        """Stops the TTS worker."""
        self._stop_event.set()
        self.queue.put(None)
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)

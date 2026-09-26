"""
Offline instant Text-to-Speech (TTS) using direct Windows SAPI5 COM and pyttsx3 fallback.
Resolves the notorious pyttsx3 SAPI5 runAndWait loop-freeze bug on Windows where subsequent
speech calls complete in 0.0s without producing any audio.
"""
import queue
import threading
import time
from typing import Callable, Optional

import config
from core.logger import logger

try:
    import pythoncom
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False


class TTSEngine:
    """
    Thread-safe Text-to-Speech worker.
    Uses native Windows SAPI.SpVoice COM interface for 100% reliable consecutive speech
    without dropped utterances, with automatic fallback to pyttsx3 if win32com is absent.
    """

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
        """Worker thread dedicated to audio output loop."""
        if HAS_WIN32COM:
            self._run_sapi_loop()
        else:
            self._run_pyttsx3_fallback_loop()

    def _run_sapi_loop(self):
        """Direct Windows SAPI5 COM worker loop — 100% reliable consecutive speech."""
        pythoncom.CoInitialize()
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")

            # Configure rate (-10 to +10, 200 WPM maps to 0)
            sapi_rate = max(-10, min(10, int((self.rate - 200) / 15)))
            speaker.Rate = sapi_rate

            # Configure volume (0 to 100)
            sapi_volume = max(0, min(100, int(self.volume * 100)))
            speaker.Volume = sapi_volume

            # Configure voice
            try:
                voices = speaker.GetVoices()
                if 0 <= self.voice_index < voices.Count:
                    speaker.Voice = voices.Item(self.voice_index)
                    logger.log("INFO", f"TTS initialized (native SAPI5): {speaker.Voice.GetDescription()}")
                else:
                    logger.log("INFO", f"TTS initialized (native SAPI5 default): {speaker.Voice.GetDescription()}")
            except Exception as e:
                logger.log("WARN", f"SAPI voice selection notice: {e}")

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

                        # Flag 0 = Synchronous speak (blocks until audio finishes playing)
                        speaker.Speak(text.strip(), 0)
                    except Exception as ex:
                        logger.log("ERROR", f"SAPI speak error: {ex}")
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

        except Exception as e:
            logger.log("ERROR", f"Failed to initialize native SAPI5 TTS engine: {e}")
        finally:
            pythoncom.CoUninitialize()

    def _run_pyttsx3_fallback_loop(self):
        """Fallback worker loop re-initializing pyttsx3 per utterance to avoid driver loop-freeze."""
        import pyttsx3

        logger.log("INFO", "TTS initialized via pyttsx3 fallback.")

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

                    # Re-init pyttsx3 each time to prevent SAPI5 driver state corruption
                    engine = pyttsx3.init("sapi5")
                    engine.setProperty("rate", self.rate)
                    engine.setProperty("volume", self.volume)
                    voices = engine.getProperty("voices")
                    if voices and 0 <= self.voice_index < len(voices):
                        engine.setProperty("voice", voices[self.voice_index].id)
                    engine.say(text.strip())
                    engine.runAndWait()
                    del engine
                except Exception as ex:
                    logger.log("ERROR", f"pyttsx3 fallback speak error: {ex}")
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
        If wait=True, blocks until speech finishes playing.
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
            self.worker_thread.join(timeout=1.5)

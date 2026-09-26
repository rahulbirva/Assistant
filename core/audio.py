"""
Microphone audio stream and Voice Activity Detection (VAD) using sounddevice.
"""
import time
import queue
import numpy as np
import sounddevice as sd
from collections import deque
from typing import Callable, Optional

import config
from core.logger import logger

class AudioRecorder:
    """
    Listens to the microphone continuously and yields speech audio segments
    delimited by silence.
    """
    def __init__(
        self,
        sample_rate: int = config.AUDIO_SAMPLE_RATE,
        block_duration_ms: int = config.AUDIO_BLOCK_DURATION_MS,
        silence_duration: float = config.AUDIO_SILENCE_DURATION,
        energy_threshold: float = config.AUDIO_ENERGY_THRESHOLD,
        on_listening_start: Optional[Callable[[], None]] = None,
        on_listening_end: Optional[Callable[[], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.block_size = int(sample_rate * (block_duration_ms / 1000.0))
        self.silence_blocks = int(silence_duration / (block_duration_ms / 1000.0))
        self.min_speech_blocks = int(config.AUDIO_MIN_SPEECH_DURATION / (block_duration_ms / 1000.0))
        self.energy_threshold = energy_threshold
        
        self.on_listening_start = on_listening_start
        self.on_listening_end = on_listening_end
        
        self.audio_queue = queue.Queue()
        self.stream = None
        self.is_running = False

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream."""
        if status:
            pass  # Overflow/underflow handled gracefully
        # indata has shape (frames, channels), squeeze to 1D
        self.audio_queue.put(indata[:, 0].copy())

    def calibrate_noise(self, duration: float = 1.0):
        """Records ambient sound to auto-calibrate energy threshold."""
        logger.log("INFO", f"Calibrating ambient noise floor ({duration:.1f}s)... Please remain quiet.")
        samples = int(duration * self.sample_rate)
        ambient_data = sd.rec(samples, samplerate=self.sample_rate, channels=1, dtype="float32")
        sd.wait()
        rms = float(np.sqrt(np.mean(ambient_data**2)))
        # Set threshold dynamically slightly above ambient noise floor with safe ceiling
        self.energy_threshold = max(0.006, min(0.012, rms * 1.8))
        logger.log("INFO", f"Noise floor RMS: {rms:.4f}. Dynamic threshold set to: {self.energy_threshold:.4f}")

    def listen_utterance(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Blocks until speech is detected and completed by silence.
        Returns the captured speech audio as a 1D float32 numpy array, or None if timed out.
        """
        # Pre-speech ring buffer (stores ~600ms of audio before trigger to capture soft initial consonants)
        pre_speech_blocks = int(0.60 / (config.AUDIO_BLOCK_DURATION_MS / 1000.0))
        pre_buffer = deque(maxlen=pre_speech_blocks)
        
        speech_buffer = []
        is_speaking = False
        silence_count = 0
        start_time = time.time()
        
        # Clear any leftover queue items
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        if self.stream is None or not self.stream.active:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.block_size,
                callback=self._audio_callback,
            )
            self.stream.start()

        while True:
            if timeout and (time.time() - start_time) > timeout:
                return None

            try:
                chunk = self.audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(chunk**2)))

            if not is_speaking:
                pre_buffer.append(chunk)
                if rms > self.energy_threshold:
                    is_speaking = True
                    silence_count = 0
                    if self.on_listening_start:
                        try:
                            self.on_listening_start()
                        except Exception:
                            pass
                    speech_buffer.extend(list(pre_buffer))
                    speech_buffer.append(chunk)
            else:
                speech_buffer.append(chunk)
                if rms < self.energy_threshold:
                    silence_count += 1
                    if silence_count >= self.silence_blocks:
                        # End of speech detected
                        if self.on_listening_end:
                            try:
                                self.on_listening_end()
                            except Exception:
                                pass
                        
                        # Validate minimum duration
                        if len(speech_buffer) >= self.min_speech_blocks:
                            audio = np.concatenate(speech_buffer)
                            return audio
                        else:
                            # Too short, discard and reset
                            speech_buffer = []
                            is_speaking = False
                            silence_count = 0
                else:
                    silence_count = 0

    def close(self):
        """Stops and closes the audio stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

"""
Offline Speech-to-Text (STT) engine using faster-whisper with CUDA acceleration.
"""
import os
import sys
import time
import numpy as np

# Automatically register CUDA & cuDNN DLL directories on Windows
if sys.platform == "win32":
    for path in sys.path:
        if "site-packages" in path:
            nvidia_root = os.path.join(path, "nvidia")
            if os.path.isdir(nvidia_root):
                for root, dirs, files in os.walk(nvidia_root):
                    if any(f.endswith(".dll") for f in files):
                        try:
                            os.add_dll_directory(root)
                        except Exception:
                            pass
                        if root not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")

from faster_whisper import WhisperModel
import config
from core.logger import logger

class STTEngine:
    """Wrapper around faster-whisper WhisperModel optimized for low latency."""
    
    def __init__(
        self,
        model_name: str = config.STT_MODEL_NAME,
        device: str = config.STT_DEVICE,
        compute_type: str = config.STT_COMPUTE_TYPE,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._load_model()

    def _load_model(self):
        """Loads faster-whisper model on CUDA with warm-up and graceful CPU fallback."""
        try:
            logger.log("INFO", f"Loading faster-whisper ({self.model_name}) on {self.device} ({self.compute_type})...")
            t0 = time.perf_counter()
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            # Warm up model to ensure cuBLAS/cuDNN DLLs are loaded
            dummy_audio = np.zeros(16000, dtype=np.float32)
            warmup_segs, _ = self.model.transcribe(dummy_audio, language="en")
            list(warmup_segs)
            
            load_time = (time.perf_counter() - t0) * 1000
            logger.log("INFO", f"faster-whisper loaded successfully in {load_time:.0f}ms on {self.device}.")
        except Exception as e:
            if self.device == "cuda":
                logger.log("WARN", f"CUDA initialization / cuBLAS failed ({e}). Falling back to CPU...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                )
                logger.log("INFO", "faster-whisper loaded on CPU fallback (int8).")
            else:
                raise e

    def transcribe(self, audio: np.ndarray, sample_rate: int = config.AUDIO_SAMPLE_RATE) -> tuple[str, float]:
        """
        Transcribes a 1D float32 numpy audio array.
        Returns: (transcribed_text, inference_time_ms)
        """
        if audio is None or len(audio) == 0:
            return "", 0.0

        # Ensure float32 normalized between -1.0 and 1.0
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / 32768.0

        t0 = time.perf_counter()
        try:
            segments, info = self.model.transcribe(
                audio,
                language="en",
                beam_size=1,            # 1 for fastest greedy decoding
                best_of=1,
                temperature=0.0,
                vad_filter=True,        # Built-in Silero VAD filtering
                vad_parameters=dict(min_silence_duration_ms=400),
            )
            text_segments = [s.text.strip() for s in segments]
            full_text = " ".join(text_segments).strip()
        except RuntimeError as ex:
            if self.device == "cuda":
                logger.log("WARN", f"CUDA transcribe error ({ex}). Switching to CPU fallback...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                return self.transcribe(audio, sample_rate)
            raise ex

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return full_text, elapsed_ms

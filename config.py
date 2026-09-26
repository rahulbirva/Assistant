"""
Configuration settings for JARVIS Voice Core & System
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
ACTIVITY_LOG_FILE = LOG_DIR / "jarvis_activity.log"

# Speech-To-Text (faster-whisper) Settings
STT_MODEL_NAME = "small.en"  # "small.en" (recommended, high accuracy), "base.en", or "tiny.en"
STT_MODEL_SIZE = STT_MODEL_NAME
STT_DEVICE = "cuda"          # "cuda" (RTX 5060) or "cpu" fallback
STT_COMPUTE_TYPE = "float16"  # "float16" on CUDA, "int8" on CPU
STT_SAMPLE_RATE = 16000      # 16kHz mono audio required by Whisper
STT_BEAM_SIZE = 3            # Beam search size (3 gives much higher accuracy than 1)
STT_INITIAL_PROMPT = "Jarvis, what time is it? Jarvis, how are you? System status, Sir."

# Audio Capture & Voice Activity Detection (VAD) Settings
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_RATE = 16000
AUDIO_BLOCK_DURATION_MS = 30   # Frame size in milliseconds
AUDIO_SILENCE_DURATION = 1.0   # Seconds of silence to trigger end-of-speech (prevents cutting off)
AUDIO_MIN_SPEECH_DURATION = 0.35 # Minimum duration in seconds to consider valid speech
AUDIO_ENERGY_THRESHOLD = 0.012 # RMS threshold for detecting voice activity
AUDIO_CALIBRATE_ON_START = True # Dynamically adapt to ambient room noise

# Text-To-Speech (pyttsx3) Settings
TTS_RATE = 195               # Speech speed (words per minute)
TTS_VOLUME = 1.0             # 0.0 to 1.0
TTS_VOICE_INDEX = 0          # 0 = default (usually David / male on Windows), 1 = Zira / female

# Wake Word & Conversation Settings
WAKE_WORDS = ["jarvis", "hey jarvis", "travis", "service", "jarves", "javis", "hello", "hey"]
REQUIRE_WAKE_WORD = False    # Set to False so Jarvis responds immediately to all spoken questions without needing 'Jarvis' every time!
CONVERSATION_TIMEOUT = 15.0  # Seconds to stay in active listening state after responding

# Assistant Persona
ASSISTANT_NAME = "Jarvis"
USER_NAME = "Sir"

# Ollama Local LLM Brain Settings (Phase 2)
USE_LLM_BRAIN = True
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"     # "llama3.2:3b" (ultra-fast) or "llama3.1:8b"
MAX_CONVERSATION_TURNS = 10

# Face Recognition Gate Settings (Phase 3)
FACE_RECOGNITION_ENABLED = True
FACE_GATE_BYPASS = True           # Set to True to bypass face gating for debugging
FACE_CHECK_INTERVAL = 4.0         # Seconds between background webcam face checks
FACE_TOLERANCE = 0.52             # Distance threshold (lower = stricter match)


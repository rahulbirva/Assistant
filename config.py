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
STT_MODEL_NAME = "tiny.en"  # "tiny.en" for lowest latency, "base.en" for higher accuracy
STT_DEVICE = "cuda"         # "cuda" (RTX 5060) or "cpu" fallback
STT_COMPUTE_TYPE = "float16" # "float16" on CUDA, "int8" on CPU
STT_SAMPLE_RATE = 16000     # 16kHz mono audio required by Whisper

# Audio Capture & Voice Activity Detection (VAD) Settings
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_RATE = 16000
AUDIO_BLOCK_DURATION_MS = 30  # Frame size in milliseconds
AUDIO_SILENCE_DURATION = 0.8  # Seconds of silence to trigger end-of-speech
AUDIO_MIN_SPEECH_DURATION = 0.4 # Minimum duration in seconds to consider valid speech
AUDIO_ENERGY_THRESHOLD = 0.012  # RMS threshold for detecting voice activity
AUDIO_CALIBRATE_ON_START = True # Dynamically adapt to ambient room noise

# Text-To-Speech (pyttsx3) Settings
TTS_RATE = 195              # Speech speed (words per minute)
TTS_VOLUME = 1.0            # 0.0 to 1.0
TTS_VOICE_INDEX = 0         # 0 = default (usually David / male on Windows), 1 = Zira / female

# Wake Word & Conversation Settings
WAKE_WORDS = ["jarvis", "hey jarvis"]
REQUIRE_WAKE_WORD = True    # If False, continuously listens for commands
CONVERSATION_TIMEOUT = 12.0 # Seconds to stay in active listening state after responding

# Assistant Persona
ASSISTANT_NAME = "Jarvis"
USER_NAME = "Sir"

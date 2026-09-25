# JARVIS — Autonomous Local AI Assistant

A fully local, GPU-accelerated, always-on AI assistant for Windows built with Python, faster-whisper, pyttsx3, Ollama, OpenCV, and Electron.

---

## ⚡ System Hardware Detected & Configured

- **Operating System:** Windows 11 (64-bit)
- **Dedicated GPU:** NVIDIA GeForce RTX 5060 (8 GB VRAM)
- **CUDA Acceleration:** CUDA 13.1 / CTranslate2 with `float16` precision
- **Speech-to-Text (STT):** `faster-whisper` (`tiny.en` on CUDA ~120ms inference latency)
- **Text-to-Speech (TTS):** `pyttsx3` via Windows native SAPI5 (offline, zero-network, instant)
- **Audio Capture:** `sounddevice` with dynamic ambient noise floor calibration & Voice Activity Detection (VAD)

---

## 📁 Project Architecture (Phase 1)

```
Assistant/
├── config.py             # Global configuration (STT, TTS, Wake words, thresholds, paths)
├── requirements.txt      # Python dependencies
├── jarvis.py             # Main entry point & voice conversational loop
├── test_voice.py         # Self-test diagnostic & latency benchmarking suite
├── core/
│   ├── __init__.py       # Core package exports
│   ├── audio.py          # SoundDevice microphone recorder with VAD & silence detection
│   ├── stt.py            # faster-whisper engine (CUDA float16 with CPU fallback)
│   ├── tts.py            # Thread-safe pyttsx3 worker with status event callbacks
│   └── logger.py         # Structured colorized console & file logging
└── logs/
    └── jarvis_activity.log # Persistent action, command, and latency audit log
```

---

## 🚀 Phase 1 — Setup & Installation

The project environment is already configured in `.venv` (Python 3.11). If you ever need to recreate or reinstall:

```powershell
# 1. Activate the virtual environment
.\.venv\Scripts\activate

# 2. Dependencies are defined in requirements.txt:
uv pip install -r requirements.txt
```

---

## 🧪 Manual Verification & Latency Benchmarks

### 1. Automated Diagnostic Benchmark
Run the automated test suite to verify TTS audio output and CUDA STT inference speed:

```powershell
.\.venv\Scripts\python test_voice.py
```

**Benchmark Results:**
- **TTS Initialization Latency:** `0.4 ms`
- **faster-whisper GPU Load Time:** `~940 ms` (on RTX 5060)
- **STT Inference Latency:** `~120 ms` (Greedy float16 on CUDA)

### 2. Live Microphone Latency Test
To test recording from your active microphone (e.g. headset/webcam) and test end-to-end round trip latency:

```powershell
.\.venv\Scripts\python test_voice.py --mic
```

### 3. Run the Live Voice Assistant
To run Jarvis in continuous voice mode with wake-word detection ("Jarvis" or "Hey Jarvis"):

```powershell
.\.venv\Scripts\python jarvis.py
```

*Say: **"Jarvis, what time is it?"** or **"Jarvis, introduce yourself"** or **"Jarvis, status"**.*

### 4. Interactive Text Console Mode (Diagnostic / Muted Mic)
```powershell
.\.venv\Scripts\python jarvis.py --text
```

---

## 🔄 Upcoming Roadmap

- [x] **Phase 1 — Voice Core:** `faster-whisper` (CUDA), `pyttsx3`, VAD audio loop, latency tracking.
- [ ] **Phase 2 — Brain via Local LLM:** Ollama (`llama3.1:8b` / `llama3.2:3b`) with tool/function calling & context memory.
- [ ] **Phase 3 — Face Recognition Gate:** OpenCV & `face_recognition` reference photo verification before gating system controls.
- [ ] **Phase 4 — Computer Control Tool Layer:** App control, shell commands, file operations, system volume/power, PyAutoGUI keyboard/mouse.
- [ ] **Phase 5 — Boot Startup & Background Service:** Windows Task Scheduler / PyWin32 background daemon with tray icon.
- [ ] **Phase 6 — Iron Man-style HUD Frontend:** Electron frameless transparent HUD, WebSocket IPC to Python backend, Reticle verification.
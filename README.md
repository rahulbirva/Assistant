# JARVIS — Autonomous Local AI Assistant

A fully local, GPU-accelerated, always-on AI assistant for Windows built with Python, faster-whisper, pyttsx3, Ollama, OpenCV, and Electron.

---

## ⚡ System Hardware Detected & Configured

- **Operating System:** Windows 11 (64-bit)
- **Dedicated GPU:** NVIDIA GeForce RTX 5060 (8 GB VRAM)
- **CUDA Acceleration:** CUDA 13.1 / CTranslate2 with `float16` precision
- **Speech-to-Text (STT):** `faster-whisper` (`small.en` on CUDA ~60ms inference latency, beam size 3)
- **Text-to-Speech (TTS):** `pyttsx3` via Windows native SAPI5 (offline, zero-network, instant)
- **Local Reasoning LLM:** `llama3.2:3b` via local Ollama (`http://localhost:11434`) with autonomous tool/function calling
- **Audio Capture:** `sounddevice` with dynamic ambient noise floor calibration & Voice Activity Detection (VAD)

---

## 📁 Project Architecture

```
Assistant/
├── config.py             # Global configuration (STT, TTS, Ollama model, thresholds, paths)
├── requirements.txt      # Python dependencies
├── jarvis.py             # Main entry point & voice conversational loop (Phase 1 & 2)
├── test_voice.py         # Phase 1: Voice core diagnostic & latency benchmark
├── test_brain.py         # Phase 2: Ollama brain reasoning & tool calling benchmark
├── run.bat               # One-click launcher for Jarvis voice assistant
├── test.bat              # One-click diagnostic test runner
├── core/
│   ├── __init__.py       # Core package exports
│   ├── audio.py          # SoundDevice microphone recorder with VAD & silence detection
│   ├── stt.py            # faster-whisper engine (CUDA float16 with CPU fallback)
│   ├── tts.py            # Thread-safe pyttsx3 worker with status event callbacks
│   ├── logger.py         # Structured colorized console & file logging
│   ├── llm.py            # Phase 2: Ollama brain, rolling memory, tool calling loop
│   └── tools.py          # Phase 2 & 4: Computer control tool layer with safety confirmation
└── logs/
    └── jarvis_activity.log # Persistent action, command, and latency audit log
```

---

## 🚀 Setup & Installation

The project environment is already configured in `.venv` (Python 3.11).

```powershell
# Dependencies are tracked in requirements.txt:
uv pip install -r requirements.txt
```

---

## 🧪 Phase 2 Verification & Manual Tests

### 1. Test Ollama Brain & Autonomous Tool Calling
Run the automated Phase 2 test suite:

```powershell
.\.venv\Scripts\python test_brain.py
```
This tests:
- Direct conversational question reasoning
- Autonomous tool calling (`get_status`: battery, time, running apps)
- Non-negotiable safety confirmation gating (`file_op`: delete confirmation prompt)

### 2. Run the Full Live Assistant (Voice + Brain)
```cmd
.\run.bat
```
*(Or `.\.venv\Scripts\python jarvis.py`)*

Try speaking to Jarvis:
- *"Jarvis, how are you today?"*
- *"Jarvis, what is the battery and system status?"*
- *"Jarvis, open Notepad"*
- *"Jarvis, close Notepad"*
- *"Jarvis, increase the volume"*
- *"Jarvis, who created you?"*

### 3. Run in Interactive Console Mode (Muted Mic / Text Testing)
```cmd
.\run.bat --text
```

---

## 🛡️ Non-Negotiable Safety Behavior

Any destructive command:
- Deleting files/folders
- System shutdown or restart
- Non-read-only arbitrary shell commands

**Automatically halts execution** and Jarvis asks:
> *"Are you sure you want to [action]?"*

Jarvis will only execute the action if you explicitly confirm with *"yes"*, *"sure"*, or *"proceed"*. If you say *"no"* or *"cancel"*, the action is safely aborted.

Every executed tool is audited with a timestamp in `logs/jarvis_activity.log`.

---

## 🔄 Upcoming Roadmap

- [x] **Phase 1 — Voice Core:** `faster-whisper` (`small.en` on CUDA), `pyttsx3`, VAD audio loop, latency tracking.
- [x] **Phase 2 — Brain via Local LLM:** Ollama (`llama3.2:3b`), tool/function calling loop, rolling context memory, safety confirmation gating.
- [ ] **Phase 3 — Face Recognition Gate:** OpenCV & `face_recognition` reference photo verification before gating system controls.
- [ ] **Phase 4 — Computer Control Tool Layer:** App control, shell commands, file operations, system volume/power, PyAutoGUI keyboard/mouse (scaffolded in `core/tools.py`).
- [ ] **Phase 5 — Boot Startup & Background Service:** Windows Task Scheduler / PyWin32 background daemon with tray icon.
- [ ] **Phase 6 — Iron Man-style HUD Frontend:** Electron frameless transparent HUD, WebSocket IPC to Python backend, Reticle verification.
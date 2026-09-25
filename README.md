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
- **Biometric Security:** OpenCV & `face_recognition` (128-d dlib encodings) periodic webcam background verification
- **Audio Capture:** `sounddevice` with dynamic ambient noise floor calibration & Voice Activity Detection (VAD)

---

## 📁 Project Architecture

```
Assistant/
├── config.py             # Global configuration (STT, TTS, Ollama, Face Gate settings)
├── requirements.txt      # Python dependencies
├── jarvis.py             # Main entry point & voice conversational loop (Phase 1, 2, 3)
├── enroll_face.py        # Phase 3: Interactive webcam face enrollment tool
├── test_voice.py         # Phase 1: Voice core diagnostic & latency benchmark
├── test_brain.py         # Phase 2: Ollama brain reasoning & tool calling benchmark
├── test_face.py          # Phase 3: Biometric face gate & authorization test suite
├── run.bat               # One-click launcher for Jarvis voice assistant
├── test.bat              # One-click diagnostic test runner
├── enroll.bat            # One-click launcher to enroll your face
├── core/
│   ├── __init__.py       # Core package exports
│   ├── audio.py          # SoundDevice microphone recorder with VAD & silence detection
│   ├── stt.py            # faster-whisper engine (CUDA float16 with CPU fallback)
│   ├── tts.py            # Thread-safe pyttsx3 worker with status event callbacks
│   ├── logger.py         # Structured colorized console & file logging
│   ├── llm.py            # Phase 2: Ollama brain, rolling memory, tool calling loop
│   ├── tools.py          # Phase 2 & 4: Computer control tool layer with safety confirmation
│   └── face_gate.py      # Phase 3: OpenCV webcam background scanner & authorization gate
├── data/
│   └── faces/            # Enrolled reference photos & 128-d encodings
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

## 🧪 Phase 3 Verification & Manual Tests

### 1. Enroll Your Reference Face
To enable facial recognition, enroll 4 reference photos of your face via webcam:

```cmd
.\enroll.bat
```
*(Or `.\.venv\Scripts\python enroll_face.py`)*

*The tool will count down and capture 4 angles of your face, generate 128-d facial embeddings, and save them in `data/faces/`.*

### 2. Test Biometric Security Gating
Run the automated Phase 3 test suite:

```powershell
.\.venv\Scripts\python test_face.py
```
This tests:
- OpenCV webcam capture & resolution
- dlib face detector initialization
- **Access Gating:** Verifies that when unauthorized/unrecognized, system-control commands (`open_app`, `run_command`, `file_op`) are **strictly blocked**, while regular conversational queries still succeed (chat-only mode).
- Verifies that when authorized, control commands are permitted.

### 3. Run the Live Assistant with Biometric Protection
```cmd
.\run.bat
```
- While you are in front of your webcam, Jarvis recognizes you and grants full computer control.
- If an unrecognized person sits in front of the PC, Jarvis will chat politely but will refuse to open apps, execute shell commands, or delete files:
  > *"Access denied, Sir. Biometric facial authentication required to execute system control actions."*

---

## 🧪 Phase 4 Verification & Manual Tests

### 1. Automated Test Suite
Run the automated Phase 4 computer control verification suite:

```powershell
.\.venv\Scripts\python test_tools.py
```
This tests:
1. **System Inspection (`get_status`):** Date/time, battery, CPU/RAM utilization, live Wi-Fi SSID & signal strength, and screen brightness.
2. **App Lifecycle (`open_app` & `close_app`):** Launches Notepad, verifies execution, and terminates cleanly.
3. **Hardware Control (`system_control`):**
   - Volume adjustment via native Windows virtual key events.
   - Screen brightness adjustment & restoration via DDC/CI / WMI.
   - Destructive safety checks for shutdown and restart.
4. **File Operations (`file_op`):** Directory creation, file writing, directory listing, file moving/renaming, pattern searching, and destructive confirmation gating on deletion.
5. **Safe Shell Execution (`run_command`):** Autonomous execution of safe read-only queries (`whoami`, `get-date`, `ipconfig`), while arbitrary/modifying commands trigger safety gating.
6. **Input Automation (`keyboard_mouse`):** Safe keystroke and hotkey dispatch.
7. **End-to-End LLM Tool Calling:** Live inference via local Ollama `llama3.2:3b` executing tool calls and synthesizing natural spoken replies.

### 2. Live Voice Testing for Phase 4
Launch Jarvis:
```cmd
.\run.bat
```
Try speaking commands:
- *"What is the current time and battery level?"*
- *"Check the Wi-Fi status and system performance."*
- *"Open Notepad."* / *"Close Notepad."*
- *"Open YouTube."* / *"Open GitHub."*
- *"Turn the volume up."* / *"Mute the audio."*
- *"Set screen brightness to 80 percent."*
- *"Create a file named notes.txt with text Hello World."*
- *"Delete notes.txt."* ➔ Notice Jarvis asks: *"Are you sure you want to permanently delete the file...?"* Say *"Yes"* to proceed or *"No"* to cancel.

---

## 🛡️ Non-Negotiable Safety Behavior

1. **Biometric Control Gate:** Unrecognized persons are restricted to chat-only mode (all computer control tools are blocked).
2. **Destructive Action Confirmation:** Even when authorized, destructive actions (file deletion, system shutdown/restart, non-whitelisted shell commands) **always require spoken confirmation** (*"Are you sure you want to ...?"*).
3. **Audit Trail:** Every action, command, and authorization state is logged to `logs/jarvis_activity.log`.

---

## 🔄 Roadmap Status

- [x] **Phase 1 — Voice Core:** `faster-whisper` (`small.en` on CUDA), `pyttsx3`, VAD audio loop, latency tracking.
- [x] **Phase 2 — Brain via Local LLM:** Ollama (`llama3.2:3b`), tool/function calling loop, rolling context memory, safety confirmation gating.
- [x] **Phase 3 — Face Recognition Gate:** OpenCV & `face_recognition` reference photo verification, background scanner, chat-only restriction.
- [x] **Phase 4 — Computer Control Tool Layer:** App control, shell commands, file operations, system volume/power/brightness, PyAutoGUI keyboard/mouse.
- [ ] **Phase 5 — Boot Startup & Background Service:** Windows Task Scheduler / PyWin32 background daemon with tray icon.
- [ ] **Phase 6 — Iron Man-style HUD Frontend:** Electron frameless transparent HUD, WebSocket IPC to Python backend, Reticle verification.
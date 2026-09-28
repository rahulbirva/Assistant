# ⚡ JARVIS — Autonomous Tactical AI Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/LLM-Llama_3.2_3B-black?logo=ollama&logoColor=white)](https://ollama.ai)
[![faster-whisper](https://img.shields.io/badge/STT-faster--whisper_CUDA-green)](https://github.com/SYSTRAN/faster-whisper)
[![HUD](https://img.shields.io/badge/HUD-Iron_Man_Tactical_MK--VII-00f0ff)](http://localhost:7788)
[![License](https://img.shields.io/badge/License-MIT-purple)](#license)

> **A fully offline, autonomous AI desktop assistant inspired by Iron Man's J.A.R.V.I.S.**  
> Features real-time voice recognition, an offline local LLM brain with computer control tool execution, an Iron Man tactical HUD dashboard on `localhost:7788`, and biometric security. **Zero cloud dependency. Complete privacy.**

---

## 🌟 Key Features

* **🛡️ 100% Offline & Private:** Powered locally by **Ollama (`llama3.2:3b`)** and **faster-whisper** — no API keys, no subscriptions, no telemetry transmitted to the cloud.
* **🎙️ Ultra-Low Latency Voice Core:** 
  * **STT:** `faster-whisper` (`small.en` on CUDA float16 ~60ms inference latency).
  * **TTS:** Microsoft SAPI5 speech synthesis (instant, thread-safe, 0ms network latency).
* **🖥️ Iron Man Tactical HUD Dashboard:**
  * Accessible on any browser at `http://localhost:7788`.
  * Dual-wing sci-fi layout with rotating Arc Reactor visualizer, 4-gauge hardware telemetry matrix (CPU, GPU, Whisper, Llama), live action log feed, and audio synthesizer sound effects.
  * Pinned **Executive Command Input** bar for typed directives.
  * Seamless `⛶ FULLSCREEN` mode (press `F11` or click the HUD button).
* **🦾 Autonomous PC Control Tools:**
  * **Apps & Web:** Open/close apps (Notepad, Spotify, Calculator, YouTube, GitHub, custom URLs).
  * **Media & Playback:** Search & play songs on Spotify, play videos directly on YouTube.
  * **Hardware & System:** Volume adjustment, screen brightness, battery/Wi-Fi telemetry, task management.
  * **Screen Vision (OCR):** Live visual screen inspection with EasyOCR to click and read screen elements.
  * **File Operations:** Read, write, move, list, and search local files.
* **🔒 Biometric Security Gate:** OpenCV + dlib 128-d face recognition. Unrecognized users are restricted to safe conversational queries, blocking sensitive system control actions.
* **⚡ Windows Boot Auto-Start & System Tray:**
  * Auto-starts silently on Windows login with no command prompt popups.
  * System tray icon with 1-click Pause/Resume and Shutdown.

---

## 📋 System Requirements

* **Operating System:** Windows 10 or Windows 11 (64-bit).
* **Python:** Python 3.10 or 3.11 ([Download Python](https://www.python.org/downloads/))  
  *(Make sure to check **"Add Python to PATH"** during installation)*.
* **Git:** Git for Windows ([Download Git](https://git-scm.com/)).
* **Ollama:** Offline AI model runtime ([Download Ollama](https://ollama.ai/)).
* **Hardware:**
  * **GPU (Recommended):** NVIDIA GPU with 4GB+ VRAM (e.g. GTX 1660, RTX 3050/4060/5060) for CUDA acceleration.
  * **CPU:** If no NVIDIA GPU is detected, JARVIS automatically adapts and runs on CPU mode.
  * **Microphone & Speakers** for voice interaction.
  * **Webcam (Optional):** Only needed if using facial recognition.

---

## 🚀 Quick Start Guide (For Any Device)

### Step 1: Clone the Repository
Open Command Prompt or PowerShell and clone the repo:
```cmd
git clone https://github.com/rahulbirva/Assistant.git
cd Assistant
```

### Step 2: Run the 1-Click Installer
Inside the `Assistant` folder, simply **double-click [`install.bat`](file:///c:/Users/RAHUL/Downloads/Work%20(IMP)/Assistant/install.bat)** (or execute in terminal):
```cmd
install.bat
```
This automated installer will:
1. Validate your Python installation.
2. Create the Python virtual environment (`.venv`).
3. Install all dependencies from `requirements.txt`.
4. Check Ollama and automatically pull the `llama3.2:3b` model.

### Step 3: Launch JARVIS
Double-click:
```cmd
START_JARVIS.bat
```
* The JARVIS background service (voice core, model loader, telemetry) will start.
* Your web browser will automatically open to **`http://localhost:7788`**.
* JARVIS will announce: *"Jarvis is online and at your service, Sir."*

---

## 🎮 How to Use & Voice Directives

Simply speak into your microphone, or type commands into the **`> INPUT_`** bar on the HUD dashboard (`http://localhost:7788`).

### Example Voice Commands:

| Directive | What JARVIS Does |
| :--- | :--- |
| *"What time is it and how is the battery?"* | Speaks current time, date, and battery level |
| *"Open YouTube"* / *"Open Spotify"* | Launches application or navigates to website |
| *"Play Bohemian Rhapsody on YouTube"* | Searches and starts video playback directly |
| *"Play Daft Punk on Spotify"* | Opens Spotify and searches the artist/track |
| *"Turn the volume up"* / *"Mute the audio"* | Adjusts master Windows audio volume |
| *"Set screen brightness to 70 percent"* | Adjusts display backlight via DDC/CI |
| *"Read what is on my screen"* | Takes a screenshot, runs OCR, and summarizes visible text |
| *"Create a note named todo.txt with buy milk"* | Creates file in workspace directory |
| *"Check system performance"* | Reports CPU, GPU, RAM, and Wi-Fi status |

---

## ⏹️ How to Turn JARVIS ON / OFF

| Action | Instructions |
| :--- | :--- |
| **Turn ON** | Double-click **[`START_JARVIS.bat`](file:///c:/Users/RAHUL/Downloads/Work%20(IMP)/Assistant/START_JARVIS.bat)** |
| **Turn OFF** | Double-click **[`STOP_JARVIS.bat`](file:///c:/Users/RAHUL/Downloads/Work%20(IMP)/Assistant/STOP_JARVIS.bat)**, or click **`SYSTEM ONLINE ⏻`** in the HUD header |
| **Pause Sensors** | Click **`SYSTEM ONLINE ⏻`** in the HUD and choose **PAUSE / RESUME (STANDBY)** |
| **Windows Auto-Start** | To enable auto-start on boot: `python register_startup.py`<br>To disable: `python register_startup.py --unregister` |

---

## 📁 Repository Structure

```
Assistant/
├── START_JARVIS.bat        # 1-Click Master Power ON & HUD launcher
├── STOP_JARVIS.bat         # 1-Click Master Power OFF
├── install.bat             # 1-Click automated setup for fresh clones
├── run.bat                 # Console mode launcher (useful for debugging)
├── jarvis_service.py       # Main background daemon (Voice + Vision + Web server)
├── hud_server.py           # HTTP & WebSocket bridge (Port 7788 / 7789)
├── jarvis_hud.html         # Iron Man HUD interface (served on localhost:7788)
├── config.py               # Global settings (thresholds, ports, models)
├── requirements.txt        # Python dependency manifest
├── register_startup.py     # Windows Registry / Task Scheduler auto-start manager
├── enroll.bat              # 1-Click facial recognition enrollment launcher
├── enroll_face.py          # Biometric face capture tool
│
├── core/                   # Core Subsystems
│   ├── audio.py            # SoundDevice capture with Voice Activity Detection (VAD)
│   ├── stt.py              # faster-whisper CUDA speech recognition engine
│   ├── tts.py              # Microsoft SAPI5 speech synthesis
│   ├── llm.py              # Ollama Llama-3.2 brain & autonomous function calling
│   ├── tools.py            # System execution tools (apps, media, brightness, files)
│   ├── screen_monitor.py   # EasyOCR vision and screen analysis engine
│   ├── face_gate.py        # OpenCV + dlib biometric authentication gate
│   └── logger.py           # Structured logging to console and logs/
│
├── hud/                    # Static Web HUD assets
│   ├── index.html          # Web HUD copy
│   └── package.json        # HUD configuration
│
└── logs/
    └── jarvis_activity.log # Persistent activity and latency audit trail
```

---

## ⚙️ Configuration & Customization

You can customize JARVIS in [`config.py`](file:///c:/Users/RAHUL/Downloads/Work%20(IMP)/Assistant/config.py):

* **Change AI Model:**  
  Change `OLLAMA_MODEL = "llama3.2:3b"` to `"mistral"`, `"deepseek-r1:8b"`, or any model installed in Ollama.
* **Adjust Voice Speed:**  
  Modify `TTS_RATE = 195` (higher is faster, lower is slower).
* **Toggle Face Biometrics:**  
  Set `FACE_GATE_ENABLED = True` to require webcam facial verification, or `False` to run in unconstrained mode.
* **Change HUD Port:**  
  Modify `HUD_HTTP_PORT = 7788` and `HUD_WS_PORT = 7789`.

---

## ❓ Troubleshooting & FAQs

#### 1. "Ollama is not recognized"
* Download and install Ollama from [https://ollama.ai](https://ollama.ai).
* Open Command Prompt and test with: `ollama run llama3.2:3b`.

#### 2. "No module named torch / CUDA error"
* If you have an NVIDIA GPU, make sure your NVIDIA graphics drivers are up to date.
* If you do not have an NVIDIA GPU, JARVIS will automatically fallback to CPU mode.

#### 3. "Microphone does not hear me"
* Open Windows Sound Settings and verify your default input microphone is working.
* You can adjust sensitivity by lowering `SILENCE_THRESHOLD` in [`config.py`](file:///c:/Users/RAHUL/Downloads/Work%20(IMP)/Assistant/config.py).

#### 4. "How do I enroll my face?"
* Run `enroll.bat` while in front of your webcam.
* The script will take 4 photos at different angles and save your biometric profile into `data/faces/`.

---

## 📜 License

This project is licensed under the MIT License — feel free to modify, extend, and adapt for your personal smart workstation setup!
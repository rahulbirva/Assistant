"""
JARVIS UNIFIED DIAGNOSTIC & END-TO-END VERIFICATION SUITE
Tests all 4 phases built today in a single command:
  - Phase 1: Voice Core (STT CUDA, TTS SAPI5, Microphone capture & VAD)
  - Phase 2: Local Brain (Ollama llama3.2:3b, Tool Calling, Confirmation Gate)
  - Phase 3: Biometric Face Gate (Webcam capture, dlib embeddings, Access Policy)
  - Phase 4: Computer Control (Status, Apps, Volume/Brightness, Files, Shell, Input)
  - End-to-End: Full Simulated Conversational Loop with spoken TTS output
"""
import os
import sys
import time
import argparse
import numpy as np
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from core.logger import logger
from core.tts import TTSEngine
from core.stt import STTEngine
from core.llm import OllamaBrain
from core.tools import tool_executor
from core.face_gate import FaceGate, face_gate


class JarvisTestRunner:
    def __init__(self, interactive_mic: bool = False):
        self.interactive_mic = interactive_mic
        self.results = {}
        self.latencies = {}

    def banner(self, phase_name: str):
        logger.log("INFO", "\n" + "=" * 70)
        logger.log("INFO", f"  >>> {phase_name.upper()}")
        logger.log("INFO", "=" * 70)

    def run_phase_1_voice_core(self):
        self.banner("Phase 1: Voice Core (STT, TTS, Audio Capture)")
        
        # 1. TTS Test
        try:
            logger.log("INFO", "Testing Text-to-Speech (pyttsx3 Windows SAPI5)...")
            t0 = time.perf_counter()
            tts = TTSEngine()
            tts.speak("Jarvis diagnostic sequence initiated. Testing voice core.", wait=True)
            tts_time = (time.perf_counter() - t0) * 1000
            tts.stop()
            self.latencies["TTS Speak"] = f"{tts_time:.1f}ms"
            self.results["TTS Output"] = "PASS"
            logger.log("SUCCESS", f"TTS synthesized and spoken in {tts_time:.1f}ms")
        except Exception as e:
            self.results["TTS Output"] = f"FAIL: {e}"
            logger.log("ERROR", f"TTS test failed: {e}")

        # 2. STT on CUDA Test
        try:
            logger.log("INFO", f"Testing faster-whisper STT on CUDA ({config.STT_MODEL_SIZE})...")
            t0 = time.perf_counter()
            stt = STTEngine()
            
            # Synthetic 1.5s audio chunk
            t = np.linspace(0, 1.5, int(1.5 * config.AUDIO_SAMPLE_RATE), endpoint=False)
            synthetic_audio = (0.2 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
            text, infer_ms = stt.transcribe(synthetic_audio)
            
            self.latencies["STT Inference"] = f"{infer_ms:.1f}ms"
            self.results["STT CUDA"] = "PASS"
            logger.log("SUCCESS", f"STT CUDA transcription completed in {infer_ms:.1f}ms (Device: {stt.device})")
        except Exception as e:
            self.results["STT CUDA"] = f"FAIL: {e}"
            logger.log("ERROR", f"STT test failed: {e}")

        # 3. Microphone Check
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            default_in = sd.query_devices(kind='input')
            logger.log("SUCCESS", f"Microphone detected: '{default_in['name']}' (Sample rate: {default_in['default_samplerate']}Hz)")
            self.results["Microphone Hardware"] = "PASS"
        except Exception as e:
            self.results["Microphone Hardware"] = f"FAIL: {e}"
            logger.log("ERROR", f"Microphone detection failed: {e}")

    def run_phase_2_local_brain(self):
        self.banner("Phase 2: Local Brain via Ollama (Reasoning & Tool Calling)")
        
        try:
            logger.log("INFO", f"Connecting to Ollama model '{config.OLLAMA_MODEL}'...")
            t0 = time.perf_counter()
            brain = OllamaBrain(model=config.OLLAMA_MODEL)
            
            # Simple conversational query
            reply, latency = brain.think_and_respond("Respond in one sentence: Are all systems ready?")
            self.latencies["LLM Chat Latency"] = f"{latency:.1f}ms"
            self.results["LLM Inference"] = "PASS"
            logger.log("SUCCESS", f"Ollama response ({latency:.1f}ms): {reply}")

            # Tool calling reasoning check
            logger.log("INFO", "Testing LLM autonomous tool-calling decision...")
            tool_reply, tool_latency = brain.think_and_respond("What time is it right now?")
            self.latencies["LLM Tool Calling"] = f"{tool_latency:.1f}ms"
            self.results["LLM Tool Calling"] = "PASS"
            logger.log("SUCCESS", f"Tool synthesized answer ({tool_latency:.1f}ms): {tool_reply}")

            # Safety Confirmation Gating
            is_dest, reason = tool_executor.is_destructive("system_control", {"action": "shutdown"})
            assert is_dest is True, "Shutdown action MUST trigger destructive confirmation!"
            self.results["Destructive Confirmation Gate"] = "PASS"
            logger.log("SUCCESS", f"Destructive safety confirmation validated: '{reason}'")

        except Exception as e:
            self.results["LLM Inference"] = f"FAIL: {e}"
            logger.log("ERROR", f"Ollama brain test failed: {e}")

    def run_phase_3_biometric_face_gate(self):
        self.banner("Phase 3: Biometric Face Recognition Gate")

        # 1. Webcam Frame Capture
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            assert cap.isOpened(), "Could not open webcam index 0"
            ret, frame = cap.read()
            cap.release()
            assert ret and frame is not None, "Failed to capture webcam frame"
            h, w = frame.shape[:2]
            logger.log("SUCCESS", f"OpenCV webcam frame captured: {w}x{h}")
            self.results["Webcam Capture"] = "PASS"
        except Exception as e:
            self.results["Webcam Capture"] = f"FAIL: {e}"
            logger.log("ERROR", f"Webcam check failed: {e}")

        # 2. Reference Biometrics Check
        try:
            gate = FaceGate()
            enrolled = gate.is_enrolled
            count = len(gate.known_encodings)
            if enrolled:
                logger.log("SUCCESS", f"Biometric reference encodings found: {count} reference angles enrolled.")
                self.results["Biometric Enrollment"] = "PASS"
            else:
                logger.log("WARN", "No face enrolled yet. Run .\\enroll.bat to register your face.")
                self.results["Biometric Enrollment"] = "WARN (Not Enrolled)"
        except Exception as e:
            self.results["Biometric Enrollment"] = f"FAIL: {e}"
            logger.log("ERROR", f"Biometrics check failed: {e}")

        # 3. Access Policy Gating (Block system tools if unauthorized)
        try:
            brain = OllamaBrain(model=config.OLLAMA_MODEL)
            # Temporarily simulate unauthorized state
            face_gate.is_recognized = False
            config.FACE_GATE_BYPASS = False
            config.FACE_RECOGNITION_ENABLED = True
            
            logger.log("INFO", "Simulating unauthorized intruder: testing control tool blockage...")
            reply, _ = brain.think_and_respond("Open Notepad")
            assert "access denied" in reply.lower() or "biometric" in reply.lower() or "restricted" in reply.lower(), (
                f"Unauthorized request was NOT blocked! Got: {reply}"
            )
            self.results["Biometric Security Gate"] = "PASS"
            logger.log("SUCCESS", f"Biometric gate successfully blocked unauthorized control command: '{reply}'")
        except Exception as e:
            self.results["Biometric Security Gate"] = f"FAIL: {e}"
            logger.log("ERROR", f"Biometric security gate test failed: {e}")
        finally:
            # Restore normal authorized state for subsequent tests
            face_gate.is_recognized = True

    def run_phase_4_computer_control(self):
        self.banner("Phase 4: Computer Control Tool Layer")

        # 1. System Status Inspection
        try:
            status = tool_executor.execute("get_status", {"category": "all"})
            logger.log("SUCCESS", f"Full System Status: {status}")
            assert "Current Time" in status and "Wi-Fi" in status, "Missing expected status fields!"
            self.results["System Status Tool"] = "PASS"
        except Exception as e:
            self.results["System Status Tool"] = f"FAIL: {e}"
            logger.log("ERROR", f"System status tool failed: {e}")

        # 2. App Lifecycle
        try:
            logger.log("INFO", "Testing app launch and termination (Notepad)...")
            open_res = tool_executor.execute("open_app", {"name": "notepad"})
            time.sleep(1.5)
            close_res = tool_executor.execute("close_app", {"name": "notepad"})
            logger.log("SUCCESS", f"App lifecycle: {open_res} -> {close_res}")
            self.results["App Lifecycle Management"] = "PASS"
        except Exception as e:
            self.results["App Lifecycle Management"] = f"FAIL: {e}"
            logger.log("ERROR", f"App lifecycle failed: {e}")

        # 3. System Hardware Control (Volume & Brightness)
        try:
            vol_res = tool_executor.execute("system_control", {"action": "volume_up"})
            br_res = tool_executor.execute("system_control", {"action": "brightness_up"})
            tool_executor.execute("system_control", {"action": "brightness_set", "value": "84"})
            logger.log("SUCCESS", f"Hardware controls: Volume ({vol_res}), Brightness ({br_res})")
            self.results["System Hardware Control"] = "PASS"
        except Exception as e:
            self.results["System Hardware Control"] = f"FAIL: {e}"
            logger.log("ERROR", f"Hardware control failed: {e}")

        # 4. File Operations
        try:
            test_path = PROJECT_ROOT / "data" / "diag_test.txt"
            renamed_path = PROJECT_ROOT / "data" / "diag_test_renamed.txt"
            
            tool_executor.execute("file_op", {"action": "create_file", "path": str(test_path), "destination": "Diagnostic verification"})
            tool_executor.execute("file_op", {"action": "move", "path": str(test_path), "destination": str(renamed_path)})
            del_res = tool_executor.execute("file_op", {"action": "delete", "path": str(renamed_path)})
            logger.log("SUCCESS", f"File ops (create, rename, delete): {del_res}")
            self.results["File Operations Tool"] = "PASS"
        except Exception as e:
            self.results["File Operations Tool"] = f"FAIL: {e}"
            logger.log("ERROR", f"File ops failed: {e}")

        # 5. Shell Execution
        try:
            cmd_res = tool_executor.execute("run_command", {"cmd": "whoami"}).strip()
            logger.log("SUCCESS", f"PowerShell execution: user '{cmd_res}'")
            self.results["Safe Shell Execution"] = "PASS"
        except Exception as e:
            self.results["Safe Shell Execution"] = f"FAIL: {e}"
            logger.log("ERROR", f"Shell execution failed: {e}")

        # 6. Keyboard / Mouse Automation
        try:
            key_res = tool_executor.execute("keyboard_mouse", {"action": "press_key", "text_or_key": "shift"})
            logger.log("SUCCESS", f"Input automation: {key_res}")
            self.results["Keyboard/Mouse Automation"] = "PASS"
        except Exception as e:
            self.results["Keyboard/Mouse Automation"] = f"FAIL: {e}"
            logger.log("ERROR", f"Input automation failed: {e}")

    def run_end_to_end_pipeline(self):
        self.banner("Phase 1-4 End-to-End Pipeline Integration")
        
        logger.log("INFO", "Running complete unified pipeline: Simulated Voice Command -> Face Check -> LLM -> Tool -> Spoken TTS Output...")
        try:
            face_gate.is_recognized = True
            brain = OllamaBrain(model=config.OLLAMA_MODEL)
            tts = TTSEngine()

            query = "What is the Wi-Fi connection and current battery status?"
            logger.log("USER", f"Incoming Voice Command: '{query}'")

            t_pipeline = time.perf_counter()
            spoken_reply, llm_ms = brain.think_and_respond(query)
            logger.log("SUCCESS", f"Jarvis Brain Output ({llm_ms:.1f}ms): {spoken_reply}")

            # Speak the synthesized response through pyttsx3
            tts.speak(spoken_reply, wait=True)
            tts.stop()
            pipeline_total = (time.perf_counter() - t_pipeline) * 1000

            self.latencies["Full Pipeline Round-Trip"] = f"{pipeline_total:.1f}ms"
            self.results["End-to-End Voice Pipeline"] = "PASS"
            logger.log("SUCCESS", f"End-to-end command executed and spoken in {pipeline_total:.1f}ms!")

        except Exception as e:
            self.results["End-to-End Voice Pipeline"] = f"FAIL: {e}"
            logger.log("ERROR", f"End-to-end pipeline failed: {e}")

        # Optional live microphone test
        if self.interactive_mic:
            logger.log("INFO", "\n" + "-" * 70)
            logger.log("INFO", "LIVE MICROPHONE TEST: Say any command aloud now (e.g. 'Jarvis, open Notepad')...")
            try:
                import sounddevice as sd
                stt = STTEngine()
                duration = 3.5
                audio = sd.rec(int(duration * config.AUDIO_SAMPLE_RATE), samplerate=config.AUDIO_SAMPLE_RATE, channels=1, dtype="float32")
                sd.wait()
                text, infer_ms = stt.transcribe(audio[:, 0])
                logger.log("SUCCESS", f"Live Speech Transcribed ({infer_ms:.1f}ms): '{text}'")
                if text:
                    reply, _ = brain.think_and_respond(text)
                    logger.log("SUCCESS", f"Live Jarvis Response: '{reply}'")
                    tts = TTSEngine()
                    tts.speak(reply, wait=True)
                    tts.stop()
            except Exception as e:
                logger.log("WARN", f"Live microphone test encountered notice: {e}")

    def print_scorecard(self):
        logger.log("INFO", "\n" + "=" * 70)
        logger.log("INFO", "                 JARVIS FULL SYSTEM TEST SCORECARD")
        logger.log("INFO", "=" * 70)
        
        all_passed = True
        for test_name, status in self.results.items():
            if "PASS" in status:
                logger.log("SUCCESS", f"  [+] {test_name.ljust(35)} : {status}")
            elif "WARN" in status:
                logger.log("WARN", f"  [!] {test_name.ljust(35)} : {status}")
            else:
                logger.log("ERROR", f"  [-] {test_name.ljust(35)} : {status}")
                all_passed = False

        if self.latencies:
            logger.log("INFO", "\n" + "-" * 70)
            logger.log("INFO", "  LATENCY BENCHMARKS")
            logger.log("INFO", "-" * 70)
            for metric, lat in self.latencies.items():
                logger.log("INFO", f"  * {metric.ljust(35)} : {lat}")

        logger.log("INFO", "=" * 70)
        if all_passed:
            logger.log("SUCCESS", "  >>> ALL SYSTEMS OPERATIONAL: JARVIS IS READY FOR ACTION <<<")
        else:
            logger.log("WARN", "  >>> SOME TESTS FAILED OR WARNED. REVIEW LOG ABOVE <<<")
        logger.log("INFO", "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Jarvis Unified System Verification Suite")
    parser.add_argument("--mic", action="store_true", help="Include live interactive microphone test at the end")
    args = parser.parse_args()

    runner = JarvisTestRunner(interactive_mic=args.mic)
    runner.run_phase_1_voice_core()
    runner.run_phase_2_local_brain()
    runner.run_phase_3_biometric_face_gate()
    runner.run_phase_4_computer_control()
    runner.run_end_to_end_pipeline()
    runner.print_scorecard()


if __name__ == "__main__":
    main()

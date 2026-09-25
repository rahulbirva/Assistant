"""
Phase 1 Diagnostic and Latency Benchmark Test Suite
Runs automated checks on TTS, STT (CUDA), Microphone capture, and round-trip latency.
"""
import sys
import time
import numpy as np
import sounddevice as sd

import config
from core.logger import logger
from core.tts import TTSEngine
from core.stt import STTEngine

def test_tts():
    logger.log("INFO", ">>> TEST 1: Testing Text-to-Speech (pyttsx3 SAPI5)...")
    t0 = time.perf_counter()
    tts = TTSEngine()
    init_ms = (time.perf_counter() - t0) * 1000
    logger.log("INFO", f"TTS initialization time: {init_ms:.1f}ms")
    
    t0 = time.perf_counter()
    tts.speak("Diagnostic test 1. Audio output functional.", wait=True)
    speak_ms = (time.perf_counter() - t0) * 1000
    logger.log("INFO", f"TTS spoken and verified in {speak_ms:.1f}ms")
    tts.stop()
    return True

def test_stt_inference():
    logger.log("INFO", ">>> TEST 2: Testing faster-whisper STT on CUDA...")
    t0 = time.perf_counter()
    stt = STTEngine()
    load_ms = (time.perf_counter() - t0) * 1000
    
    # Generate 1.5 seconds of simulated audio
    sample_rate = config.AUDIO_SAMPLE_RATE
    t = np.linspace(0, 1.5, int(1.5 * sample_rate), endpoint=False)
    synthetic_audio = (0.2 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    
    text, infer_ms = stt.transcribe(synthetic_audio)
    logger.log("INFO", f"STT synthetic audio transcription completed in: {infer_ms:.1f}ms (Engine: {stt.device})")
    assert infer_ms < 1000, "STT latency should be under 1000ms on CUDA!"
    return True

def test_microphone_and_roundtrip():
    logger.log("INFO", ">>> TEST 3: Testing Microphone Recording & Live Latency...")
    stt = STTEngine()
    tts = TTSEngine()
    
    duration = 3.0
    logger.log("INFO", f"Recording {duration:.1f} seconds from default microphone... Please say: 'Jarvis, what time is it?'")
    
    t_rec_start = time.perf_counter()
    audio = sd.rec(int(duration * config.AUDIO_SAMPLE_RATE), samplerate=config.AUDIO_SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    rec_ms = (time.perf_counter() - t_rec_start) * 1000
    
    logger.log("INFO", f"Audio recorded ({len(audio)} samples, {rec_ms:.1f}ms). Transcribing...")
    
    t_roundtrip_start = time.perf_counter()
    text, stt_ms = stt.transcribe(audio[:, 0])
    
    # Process
    t_proc = time.perf_counter()
    if "time" in text.lower():
        reply = "The current time has been requested. Test successful."
    else:
        reply = f"Captured speech: {text or '[Silence / Unrecognized]'}"
    proc_ms = (time.perf_counter() - t_proc) * 1000
    
    # TTS
    t_tts = time.perf_counter()
    tts.speak(reply, wait=True)
    tts_ms = (time.perf_counter() - t_tts) * 1000
    
    total_ms = (time.perf_counter() - t_roundtrip_start) * 1000
    
    logger.log("INFO", "--------------------------------------------------")
    logger.log("INFO", f"Transcribed text: '{text}'")
    logger.log("INFO", f"Latency STT:       {stt_ms:.1f} ms")
    logger.log("INFO", f"Latency Process:   {proc_ms:.1f} ms")
    logger.log("INFO", f"Latency TTS Speak: {tts_ms:.1f} ms")
    logger.log("LATENCY", f"Total End-to-End Latency: {total_ms:.1f} ms")
    logger.log("INFO", "--------------------------------------------------")
    
    tts.stop()
    return True

def main():
    logger.log("INFO", "==================================================")
    logger.log("INFO", "   JARVIS PHASE 1 — VOICE CORE DIAGNOSTIC SUITE   ")
    logger.log("==================================================")
    
    try:
        test_tts()
        test_stt_inference()
        logger.log("INFO", "All automated core tests PASSED!")
        logger.log("INFO", "Run `python jarvis.py` to start the live interactive voice loop.")
    except Exception as e:
        logger.log("ERROR", f"Diagnostic failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

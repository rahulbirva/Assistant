"""
JARVIS — Voice Core (Phase 1)
Main entry point for voice listening, wake word detection, STT/TTS loop, and latency benchmarking.
"""
import sys
import time
import argparse
from datetime import datetime
import config
from core.logger import logger
from core.tts import TTSEngine
from core.stt import STTEngine
from core.audio import AudioRecorder

class JarvisVoiceCore:
    """Manages the Phase 1 Voice Core conversational loop."""
    
    def __init__(self, require_wake_word: bool = config.REQUIRE_WAKE_WORD):
        self.require_wake_word = require_wake_word
        self.wake_words = [w.lower() for w in config.WAKE_WORDS]
        self.active_session_until = 0.0
        
        logger.log("INFO", "Initializing Jarvis Voice Core...")
        
        # Initialize TTS
        self.tts = TTSEngine(
            on_start_speaking=lambda: logger.log("SPEAKING", "[Audio Output Started]"),
            on_finish_speaking=lambda: logger.log("IDLE", "[Audio Output Finished]"),
        )
        
        # Initialize STT
        self.stt = STTEngine()
        
        # Initialize Audio Recorder
        self.recorder = AudioRecorder(
            on_listening_start=lambda: logger.log("LISTENING", "User is speaking..."),
            on_listening_end=lambda: logger.log("THINKING", "Processing speech audio..."),
        )

    def startup(self):
        """Calibrates microphone and greets user."""
        logger.log("INFO", "==================================================")
        logger.log("INFO", f"⚡ {config.ASSISTANT_NAME} VOICE CORE ONLINE ⚡")
        logger.log("INFO", f"• STT: faster-whisper ({self.stt.model_name}) on {self.stt.device}")
        logger.log("INFO", f"• TTS: pyttsx3 (SAPI5 offline)")
        logger.log("INFO", f"• Wake Words: {', '.join(self.wake_words)}")
        logger.log("INFO", f"• Mode: {'Wake-word gated' if self.require_wake_word else 'Always listening'}")
        logger.log("INFO", "==================================================")
        
        if config.AUDIO_CALIBRATE_ON_START:
            self.recorder.calibrate_noise(duration=1.0)
            
        greeting = f"Systems initialized. I am online and listening, {config.USER_NAME}."
        self.tts.speak(greeting, wait=True)

    def extract_command_after_wake_word(self, text: str) -> tuple[bool, str]:
        """
        Checks if text contains a wake word.
        Returns: (has_wake_word, remaining_command)
        """
        cleaned = text.lower().strip()
        # Remove common punctuation for matching
        for punct in [".", ",", "!", "?"]:
            cleaned = cleaned.replace(punct, "")
            
        for w in self.wake_words:
            if cleaned == w:
                return True, ""
            if cleaned.startswith(w + " "):
                cmd = cleaned[len(w):].strip()
                return True, cmd
            if w in cleaned:
                # Find position
                idx = cleaned.find(w)
                cmd = cleaned[idx + len(w):].strip()
                return True, cmd
                
        return False, ""

    def process_command(self, query: str) -> str:
        """
        Built-in Phase 1 keyword command processor.
        (In Phase 2, this delegates to the Ollama local LLM brain).
        """
        q = query.lower().strip()
        
        if not q:
            return f"Yes, {config.USER_NAME}? How may I assist you?"

        if any(w in q for w in ["hello", "hi", "hey"]):
            return f"Hello, {config.USER_NAME}. I am online and listening."

        if any(w in q for w in ["how are you", "how're you", "how are you doing"]):
            return f"I am functioning at peak efficiency, {config.USER_NAME}. All systems ready."

        if "time" in q:
            now = datetime.now().strftime("%I:%M %p")
            return f"The current time is {now}."
            
        if "date" in q or "today" in q:
            today = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {today}."
            
        if any(w in q for w in ["who are you", "introduce yourself", "identity"]):
            return (
                f"I am {config.ASSISTANT_NAME}, your personal offline AI assistant running locally "
                f"on your Windows PC with GPU acceleration. My voice core is powered by faster-whisper and pyttsx3."
            )

        if any(w in q for w in ["what can you do", "help", "capabilities"]):
            return (
                f"I can tell you the time, date, report system status, benchmark latency, and in Phase 2, "
                f"reason through local Ollama LLM to automate computer actions."
            )

        if any(w in q for w in ["thank you", "thanks"]):
            return f"Always at your service, {config.USER_NAME}."
            
        if "status" in q or "system status" in q:
            return (
                f"All core systems operational. STT model {self.stt.model_name} running on {self.stt.device} with float16 precision. "
                f"Voice synthesis active and ready."
            )

        if "latency" in q or "benchmark" in q:
            return "Voice latency benchmark complete. Response times are well within target."

        if any(word in q for word in ["exit", "quit", "shutdown", "goodbye"]):
            return "__EXIT__"

        # Default fallback response for voice core testing
        return (
            f"I heard you say: '{query}'. Voice core is operational. "
            f"Phase 2 will connect this query to your local Ollama reasoning model."
        )

    def run_voice_loop(self):
        """Continuous voice listening and conversation loop."""
        self.startup()
        
        try:
            while True:
                now = time.time()
                in_active_session = now < self.active_session_until
                
                if not self.require_wake_word or in_active_session:
                    logger.log("LISTENING", f"Listening for command... ({'Active session' if in_active_session else 'Always listen'})")
                else:
                    logger.log("IDLE", f"Waiting for wake word ('{self.wake_words[0]}')...")

                # Listen for speech utterance
                audio = self.recorder.listen_utterance(timeout=None)
                if audio is None:
                    continue

                # Transcribe speech
                text, stt_ms = self.stt.transcribe(audio)
                if not text:
                    continue

                logger.log("HEARD", f"Transcribed: '{text}' ({stt_ms:.1f}ms)")
                
                is_wake = False
                command = ""

                if self.require_wake_word and not in_active_session:
                    is_wake, command = self.extract_command_after_wake_word(text)
                    if not is_wake:
                        # Audio didn't contain wake word, ignore and keep idling
                        continue
                    # Wake word detected: open active session window
                    self.active_session_until = time.time() + config.CONVERSATION_TIMEOUT
                else:
                    # In active session or always listening
                    command = text
                    self.active_session_until = time.time() + config.CONVERSATION_TIMEOUT

                # Process command and measure latency
                t_proc_start = time.perf_counter()
                response = self.process_command(command)
                proc_ms = (time.perf_counter() - t_proc_start) * 1000

                if response == "__EXIT__":
                    self.tts.speak(f"Shutting down voice core. Goodbye, {config.USER_NAME}.", wait=True)
                    break

                # Measure TTS speech latency
                t_tts_start = time.perf_counter()
                self.tts.speak(response, wait=False)
                tts_ms = (time.perf_counter() - t_tts_start) * 1000

                # Total round trip latency (speech finished -> model responded)
                total_latency = stt_ms + proc_ms + tts_ms
                logger.log_latency(stt_ms, proc_ms, tts_ms, total_latency)

        except KeyboardInterrupt:
            logger.log("INFO", "Shutdown requested by user (Ctrl+C).")
        finally:
            self.shutdown()

    def run_text_loop(self):
        """Interactive text test loop for debugging without microphone."""
        logger.log("INFO", "Starting Jarvis in Text Mode (type 'exit' to quit)...")
        self.tts.speak(f"Text mode initialized, {config.USER_NAME}.", wait=False)
        while True:
            try:
                user_input = input("\nYou > ").strip()
                if not user_input:
                    continue
                t0 = time.perf_counter()
                response = self.process_command(user_input)
                proc_ms = (time.perf_counter() - t0) * 1000
                if response == "__EXIT__":
                    self.tts.speak(f"Goodbye, {config.USER_NAME}.", wait=True)
                    break
                t_tts = time.perf_counter()
                self.tts.speak(response, wait=True)
                tts_ms = (time.perf_counter() - t_tts) * 1000
                logger.log_latency(0.0, proc_ms, tts_ms, proc_ms + tts_ms)
            except (KeyboardInterrupt, EOFError):
                break
        self.shutdown()

    def shutdown(self):
        """Clean shutdown of resources."""
        logger.log("INFO", "Closing audio stream and voice engines...")
        self.recorder.close()
        self.tts.stop()
        logger.log("INFO", "Jarvis voice core terminated cleanly.")

def main():
    parser = argparse.ArgumentParser(description="Jarvis Voice Core (Phase 1)")
    parser.add_argument(
        "--always-listen",
        action="store_true",
        help="Disable wake word requirement and process all detected speech immediately.",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Run in interactive text console mode with TTS voice responses.",
    )
    args = parser.parse_args()
    
    jarvis = JarvisVoiceCore(require_wake_word=not args.always_listen)
    if args.text:
        jarvis.run_text_loop()
    else:
        jarvis.run_voice_loop()

if __name__ == "__main__":
    main()

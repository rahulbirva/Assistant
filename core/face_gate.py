"""
Face Recognition Biometric Gate for Jarvis (Phase 3).
Periodically verifies the user's face via webcam to gate system control commands.
"""
import os
import sys
import time
import pickle
import threading
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

import config
from core.logger import logger

try:
    import face_recognition
except ImportError:
    face_recognition = None

FACES_DIR = config.BASE_DIR / "data" / "faces"
ENCODINGS_FILE = FACES_DIR / "encodings.pkl"

class FaceGate:
    """
    Biometric security layer: captures webcam frames periodically in a background thread,
    verifying if the person in frame matches the enrolled reference face.
    """
    def __init__(
        self,
        camera_index: int = 0,
        check_interval: float = 4.0,
        tolerance: float = 0.52,
    ):
        self.camera_index = camera_index
        self.check_interval = check_interval
        self.tolerance = tolerance
        
        self.known_encodings: List[np.ndarray] = []
        self.is_enrolled = False
        self.is_recognized = False
        self.last_status = "INITIALIZING"
        self.last_check_time = 0.0
        
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        FACES_DIR.mkdir(parents=True, exist_ok=True)
        self.load_encodings()

    def load_encodings(self) -> bool:
        """Loads saved reference face encodings from disk."""
        with self._lock:
            if ENCODINGS_FILE.exists():
                try:
                    with open(ENCODINGS_FILE, "rb") as f:
                        self.known_encodings = pickle.load(f)
                    self.is_enrolled = len(self.known_encodings) > 0
                    if self.is_enrolled:
                        logger.log("INFO", f"Loaded {len(self.known_encodings)} reference face encodings.")
                    return self.is_enrolled
                except Exception as e:
                    logger.log("ERROR", f"Failed to load reference face encodings: {e}")
            self.is_enrolled = False
            return False

    def save_encodings(self, encodings: List[np.ndarray]):
        """Persists reference face encodings to disk."""
        with self._lock:
            self.known_encodings = encodings
            self.is_enrolled = len(encodings) > 0
            with open(ENCODINGS_FILE, "wb") as f:
                pickle.dump(encodings, f)
            logger.log("INFO", f"Saved {len(encodings)} reference face encodings to {ENCODINGS_FILE}.")

    def start_background_scanner(self):
        """Starts background verification thread."""
        if not self.is_enrolled:
            logger.log("WARN", "Face Gate: No reference face enrolled yet! Run `python enroll_face.py`.")
            self.last_status = "NOT_ENROLLED"
            # In unenrolled state, system controls remain gated until face is enrolled
            return

        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._scan_loop, daemon=True, name="FaceGate-Worker")
        self._worker_thread.start()
        logger.log("INFO", f"Face Gate scanner started (interval: {self.check_interval}s).")

    def _scan_loop(self):
        """Continuous periodic webcam verification loop."""
        while not self._stop_event.is_set():
            try:
                recognized, status = self.verify_current_frame()
                with self._lock:
                    self.is_recognized = recognized
                    self.last_status = status
                    self.last_check_time = time.time()
            except Exception as e:
                with self._lock:
                    self.last_status = f"ERROR: {e}"
            
            time.sleep(self.check_interval)

    def verify_current_frame(self) -> Tuple[bool, str]:
        """
        Captures a single frame from the webcam, checks face detection,
        and matches against reference encodings.
        """
        if not face_recognition:
            return False, "FACE_RECOGNITION_UNAVAILABLE"

        if not self.is_enrolled or not self.known_encodings:
            return False, "NOT_ENROLLED"

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            return False, "CAMERA_UNAVAILABLE"

        try:
            # Let camera adjust exposure for 2 frames
            for _ in range(2):
                cap.read()
            ret, frame = cap.read()
        finally:
            cap.release()

        if not ret or frame is None:
            return False, "FRAME_CAPTURE_FAILED"

        # Downsample frame 2x and convert BGR to RGB for fast processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        if not face_locations:
            return False, "NO_FACE_DETECTED"

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if not face_encodings:
            return False, "ENCODING_FAILED"

        # Compare detected face against all reference encodings
        current_face = face_encodings[0]
        distances = face_recognition.face_distance(self.known_encodings, current_face)
        best_match_idx = int(np.argmin(distances))
        best_distance = float(distances[best_match_idx])

        if best_distance < self.tolerance:
            confidence = (1.0 - best_distance) * 100
            return True, f"RECOGNIZED ({confidence:.1f}% match)"
        else:
            return False, f"UNRECOGNIZED_PERSON (distance: {best_distance:.2f})"

    def is_authorized(self) -> bool:
        """
        Returns True if the user is currently verified, False otherwise.
        Gated actions: if False, assistant operates in chat-only mode.
        """
        # If bypassed in config for debugging
        if getattr(config, "FACE_GATE_BYPASS", False):
            return True

        if not self.is_enrolled:
            return False

        with self._lock:
            return self.is_recognized

    def stop(self):
        """Stops background scanner thread."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.5)

face_gate = FaceGate()

"""
Face Enrollment Tool for Jarvis (Phase 3).
Captures 3-5 reference photos via webcam, computes 128-d face encodings, and saves them.
"""
import time
import cv2
import numpy as np
import face_recognition

import config
from core.logger import logger
from core.face_gate import FaceGate, FACES_DIR

def capture_reference_photos(num_photos: int = 4) -> bool:
    """Interactively captures reference photos from webcam."""
    logger.log("INFO", "==================================================")
    logger.log("INFO", "       JARVIS BIOMETRIC FACE ENROLLMENT           ")
    logger.log("==================================================")
    logger.log("INFO", f"We will capture {num_photos} reference photos of your face.")
    logger.log("INFO", "Position yourself in front of your webcam in good lighting.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.log("ERROR", "Cannot open webcam. Please ensure camera is connected and not in use.")
        return False

    FACES_DIR.mkdir(parents=True, exist_ok=True)
    captured_encodings = []
    
    prompts = [
        "1. Look directly forward at the camera",
        "2. Tilt your head slightly to the left",
        "3. Tilt your head slightly to the right",
        "4. Smile or give a natural expression looking forward"
    ]

    try:
        for i in range(num_photos):
            prompt = prompts[i] if i < len(prompts) else f"Photo {i+1}: Look at the camera"
            logger.log("INFO", f"\n>>> Step {i+1}/{num_photos}: {prompt}")
            
            # Countdown
            for sec in range(3, 0, -1):
                logger.log("INFO", f"Taking photo in {sec}...")
                time.sleep(1.0)

            # Flush camera buffer
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.log("WARN", "Failed to capture frame, retrying step...")
                continue

            # Check face detection
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb, model="hog")
            
            if not locations:
                logger.log("WARN", "No face detected in frame! Please make sure your face is visible and well-lit.")
                logger.log("INFO", "Retrying this step in 2 seconds...")
                time.sleep(2.0)
                # Retry step
                for _ in range(5):
                    cap.read()
                ret, frame = cap.read()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locations = face_recognition.face_locations(rgb, model="hog")
                if not locations:
                    logger.log("ERROR", "Face still not detected. Skipping.")
                    continue

            # Compute encoding
            encs = face_recognition.face_encodings(rgb, locations)
            if encs:
                captured_encodings.append(encs[0])
                # Save photo
                photo_path = FACES_DIR / f"reference_{i+1}.jpg"
                cv2.imwrite(str(photo_path), frame)
                logger.log("INFO", f"[OK] Captured and encoded reference photo {i+1} ({photo_path.name})")

    finally:
        cap.release()

    if len(captured_encodings) >= 2:
        gate = FaceGate()
        gate.save_encodings(captured_encodings)
        logger.log("INFO", "==================================================")
        logger.log("INFO", f"SUCCESS: ENROLLMENT COMPLETE! {len(captured_encodings)} reference angles saved.")
        logger.log("INFO", "Jarvis Face Gate biometric protection is now ACTIVE.")
        logger.log("INFO", "==================================================")
        return True
    else:
        logger.log("ERROR", f"Enrollment incomplete. Only {len(captured_encodings)} photos captured. Please re-run.")
        return False

def main():
    capture_reference_photos(num_photos=4)

if __name__ == "__main__":
    main()

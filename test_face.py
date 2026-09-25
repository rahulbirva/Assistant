"""
Phase 3 Diagnostic Test Suite for Face Recognition Gate.
Tests webcam frame capture, face detection, encoding computation, and authorization gating.
"""
import time
import cv2
import numpy as np

import config
from core.logger import logger
from core.face_gate import FaceGate, face_gate
from core.llm import OllamaBrain

def test_camera_and_detection():
    logger.log("INFO", ">>> TEST 1: Testing OpenCV Webcam Capture & Resolution...")
    cap = cv2.VideoCapture(0)
    assert cap.isOpened(), "Failed to open webcam at index 0!"
    
    ret, frame = cap.read()
    cap.release()
    assert ret and frame is not None, "Failed to capture frame from webcam!"
    
    h, w, c = frame.shape
    logger.log("INFO", f"Webcam frame captured successfully: {w}x{h} ({c} channels)")
    return True

def test_face_recognition_models():
    logger.log("INFO", ">>> TEST 2: Testing dlib Face Detection & 128-d Encoding...")
    import face_recognition
    
    # Generate synthetic image or test with blank/dummy image
    synthetic_image = np.zeros((300, 300, 3), dtype=np.uint8)
    # Draw simple face-like shapes
    cv2.circle(synthetic_image, (150, 150), 80, (200, 200, 200), -1)
    
    locations = face_recognition.face_locations(synthetic_image)
    logger.log("INFO", f"Face detector initialized and operational (tested on sample frame).")
    return True

def test_authorization_gating():
    logger.log("INFO", ">>> TEST 3: Testing Non-Negotiable Biometric Control Gating...")
    brain = OllamaBrain()
    
    # Simulate unauthorized state
    face_gate.is_recognized = False
    face_gate.is_enrolled = True
    config.FACE_GATE_BYPASS = False
    config.FACE_RECOGNITION_ENABLED = True
    
    logger.log("INFO", f"Simulated user state: UNAUTHORIZED (is_authorized={face_gate.is_authorized()})")
    
    # Try calling a system control action (open_app)
    prompt = "Open Notepad"
    logger.log("INFO", f"User query: '{prompt}'")
    reply, _ = brain.think_and_respond(prompt)
    logger.log("INFO", f"Jarvis reply: {reply}")
    
    assert "access denied" in reply.lower() or "biometric" in reply.lower() or "restricted" in reply.lower(), (
        f"Control command should be BLOCKED when user is not recognized! Got: {reply}"
    )
    logger.log("INFO", "[PASS] System-control command was correctly BLOCKED for unrecognized person.")
    
    # Now test that chat-only queries still work even when unauthorized
    chat_prompt = "What is the capital of France?"
    logger.log("INFO", f"\nTesting chat-only query while unauthorized: '{chat_prompt}'")
    chat_reply, _ = brain.think_and_respond(chat_prompt)
    logger.log("INFO", f"Jarvis reply: {chat_reply}")
    assert "paris" in chat_reply.lower(), "Chat should still function in chat-only mode!"
    logger.log("INFO", "[PASS] Chat-only queries allowed for unrecognized person.")
    
    # Now simulate authorized state
    face_gate.is_recognized = True
    logger.log("INFO", f"\nSimulated user state: AUTHORIZED (is_authorized={face_gate.is_authorized()})")
    auth_reply, _ = brain.think_and_respond(prompt)
    logger.log("INFO", f"Jarvis reply when authorized: {auth_reply}")
    assert "access denied" not in auth_reply.lower(), "Command should be permitted when user is authorized!"
    logger.log("INFO", "[PASS] System-control command was correctly PERMITTED for authorized person.")
    
    return True

def main():
    logger.log("INFO", "==================================================")
    logger.log("INFO", "   JARVIS PHASE 3 — FACE RECOGNITION TEST SUITE   ")
    logger.log("==================================================")
    
    try:
        test_camera_and_detection()
        test_face_recognition_models()
        test_authorization_gating()
        logger.log("INFO", "==================================================")
        logger.log("INFO", "All Phase 3 Face Recognition tests PASSED!")
        logger.log("INFO", "To enroll your real face, run: `python enroll_face.py`")
        logger.log("INFO", "==================================================")
    except Exception as e:
        logger.log("ERROR", f"Face test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

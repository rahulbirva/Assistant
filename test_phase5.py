"""
Phase 5 Verification & Diagnostic Suite.
Tests:
  1. Desktop Screenshot Capture & EasyOCR text extraction
  2. Fuzzy text matching and UI coordinate calculation
  3. Vision tools: scroll, click_at_position, click_on_text
  4. System tray icon image generation across all 7 states
  5. End-to-End LLM vision-aware tool calling
  6. Task Scheduler startup registration commands
"""
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import logger
from core.screen_monitor import screen_monitor
from core.tools import tool_executor, TOOL_DEFINITIONS
from core.llm import OllamaBrain
from jarvis_tray import JarvisTrayIcon
import register_startup


def banner(title: str):
    logger.log("INFO", "=" * 65)
    logger.log("INFO", f"  TEST SUITE: {title}")
    logger.log("INFO", "=" * 65)


def test_screen_capture_and_ocr():
    banner("1. Desktop Screenshot & EasyOCR Text Extraction")
    img, results = screen_monitor.capture_now()
    assert img is not None, "Failed to capture desktop screenshot!"
    w, h = img.size
    logger.log("SUCCESS", f"Desktop captured successfully: {w}x{h} pixels")

    logger.log("INFO", f"OCR extracted {len(results)} readable text regions on screen.")
    assert len(results) > 0, "OCR should find visible text on active desktop!"

    for r in results[:5]:
        logger.log("SUCCESS", f"  * '{r['text']}' (Conf: {r['confidence']:.2f}) at center {r['center']}")

    ctx = screen_monitor.get_screen_context()
    logger.log("SUCCESS", f"Generated LLM screen context: {ctx[:120]}...")


def test_fuzzy_text_search():
    banner("2. Fuzzy Text Matching & Coordinate Detection")
    _, results = screen_monitor.capture_now()
    if not results:
        logger.log("WARN", "No OCR results available to test fuzzy match.")
        return

    sample = results[0]["text"]
    logger.log("INFO", f"Testing search for: '{sample}'")
    match = screen_monitor.find_text(sample)
    assert match is not None, f"Should find exact or fuzzy match for '{sample}'!"
    logger.log("SUCCESS", f"Found match: '{match['text']}' at {match['center']}")

    # Partial substring test
    if len(sample) > 3:
        sub = sample[:4]
        sub_match = screen_monitor.find_text(sub)
        assert sub_match is not None, f"Should find match for substring '{sub}'!"
        logger.log("SUCCESS", f"Found substring match for '{sub}': '{sub_match['text']}'")


def test_vision_tools():
    banner("3. Vision-Aware Computer Control Tools")

    # 1. Scroll
    scroll_res = tool_executor.execute("scroll", {"direction": "down", "amount": 2})
    logger.log("SUCCESS", f"Scroll tool: {scroll_res}")
    assert "Scrolled" in scroll_res

    # 2. Click at position (safe coordinate test)
    click_pos_res = tool_executor.execute("click_at_position", {"x": 500, "y": 500})
    logger.log("SUCCESS", f"Click position tool: {click_pos_res}")
    assert "Clicked at coordinates" in click_pos_res

    # 3. Click on text (using OCR match)
    _, results = screen_monitor.capture_now()
    if results:
        target = results[0]["text"]
        click_txt_res = tool_executor.execute("click_on_text", {"target_text": target})
        logger.log("SUCCESS", f"Click on text tool: {click_txt_res}")
        assert "Clicked on" in click_txt_res


def test_tray_icon_generation():
    banner("4. System Tray State Icons Generation")
    tray = JarvisTrayIcon()
    states = ["IDLE", "LISTENING", "THINKING", "SPEAKING", "LOCKED", "SEEING", "PAUSED"]

    for st in states:
        icon_img = tray._create_icon_image(st)
        assert icon_img is not None and icon_img.size == (64, 64), f"Invalid icon for state {st}"
        logger.log("SUCCESS", f"Generated 64x64 RGBA icon for state: [{st}]")


def test_llm_vision_reasoning():
    banner("5. End-to-End LLM Vision Reasoning")
    brain = OllamaBrain()

    query = "Look at my screen and click on File"
    logger.log("USER", f"Query: '{query}'")
    reply, latency = brain.think_and_respond(query)
    logger.log("SUCCESS", f"Jarvis response ({latency:.1f}ms): {reply}")


def test_startup_registration():
    banner("6. Windows Task Scheduler Registration Script")
    # Query current status
    registered = register_startup.query_task()
    logger.log("SUCCESS", f"Task Scheduler query completed (Registered: {registered})")


def main():
    logger.log("INFO", "Starting JARVIS Phase 5 Diagnostic & Verification Suite...")
    try:
        test_screen_capture_and_ocr()
        test_fuzzy_text_search()
        test_vision_tools()
        test_tray_icon_generation()
        test_llm_vision_reasoning()
        test_startup_registration()

        logger.log("INFO", "=" * 65)
        logger.log("SUCCESS", "ALL PHASE 5 TESTS COMPLETED SUCCESSFULLY!")
        logger.log("INFO", "=" * 65)
    except Exception as e:
        logger.log("ERROR", f"Phase 5 test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

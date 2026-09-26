"""
Screen Monitor & OCR Engine for Jarvis (Phase 5).
Continuously captures desktop screenshots, runs EasyOCR to extract visible text
and bounding box coordinates, and provides vision-aware screen context to the LLM and tools.
"""
import os
import sys
import time
import ctypes
import difflib
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageGrab

from core.logger import logger
import config

# Suppress PyTorch deprecation warnings in stdout
import warnings
warnings.filterwarnings("ignore")

try:
    import easyocr
except ImportError:
    easyocr = None


def ensure_interactive_desktop():
    """Ensures current thread is attached to the interactive Windows 'Default' desktop."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


class ScreenMonitor:
    """
    Background worker that captures primary screen and runs OCR.
    Thread-safe cache provides current screen text, coordinates, and summaries.
    """

    def __init__(self, interval: float = 2.5, min_confidence: float = 0.6):
        self.interval = interval
        self.min_confidence = min_confidence
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Cached state
        self.latest_screenshot: Optional[Image.Image] = None
        self.latest_ocr_results: List[Dict[str, Any]] = []
        self.latest_summary: str = "Screen monitor starting up..."
        self.last_capture_time: float = 0.0

        # EasyOCR Reader
        self.reader = None
        self._init_reader()

    def _init_reader(self):
        """Initializes the EasyOCR reader with GPU support if available."""
        if not easyocr:
            logger.log("WARN", "EasyOCR is not installed. Screen vision will be disabled.")
            return

        try:
            logger.log("INFO", "Initializing EasyOCR reader...")
            # verbose=False avoids Windows charmap encoding errors
            self.reader = easyocr.Reader(["en"], gpu=True, verbose=False)
            logger.log("INFO", "EasyOCR reader initialized and ready.")
        except Exception as e:
            try:
                # Fallback to CPU if GPU initialization encounters issues
                self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                logger.log("INFO", "EasyOCR reader initialized on CPU fallback.")
            except Exception as ex:
                logger.log("ERROR", f"Failed to initialize EasyOCR reader: {ex}")

    def capture_screenshot(self) -> Optional[Image.Image]:
        """
        Captures a screenshot of the primary screen.
        Uses a clean worker thread to guarantee successful SetThreadDesktop attachment
        even if the caller thread has already allocated console or GUI handles.
        """
        result = []

        def _do_grab():
            ensure_interactive_desktop()
            try:
                img = ImageGrab.grab()
                result.append(img)
            except Exception as e:
                result.append(None)

        # Run in a dedicated thread with fresh Win32 thread state
        t = threading.Thread(target=_do_grab, name="ScreenGrabWorker")
        t.start()
        t.join(timeout=4.0)

        if result and result[0] is not None:
            return result[0]
        else:
            logger.log("WARN", "Screen capture returned None")
            return None

    def process_screenshot(self, img: Image.Image) -> List[Dict[str, Any]]:
        """Runs OCR on the given image and returns list of detected text elements."""
        if not self.reader or img is None:
            return []

        try:
            arr = np.array(img)
            # EasyOCR returns list of (bbox, text, prob)
            raw_results = self.reader.readtext(arr)
            parsed = []

            for bbox, text, prob in raw_results:
                clean_text = text.strip()
                if not clean_text or prob < self.min_confidence:
                    continue

                # bbox is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                pts = [[int(pt[0]), int(pt[1])] for pt in bbox]
                cx = int((pts[0][0] + pts[2][0]) / 2)
                cy = int((pts[0][1] + pts[2][1]) / 2)
                w = int(abs(pts[1][0] - pts[0][0]))
                h = int(abs(pts[2][1] - pts[1][1]))

                parsed.append({
                    "text": clean_text,
                    "confidence": float(prob),
                    "box": pts,
                    "center": (cx, cy),
                    "width": w,
                    "height": h,
                })

            return parsed
        except Exception as e:
            logger.log("ERROR", f"OCR processing error: {e}")
            return []

    def _build_summary(self, results: List[Dict[str, Any]]) -> str:
        """Constructs an organized summary of visible screen elements for the LLM prompt."""
        if not results:
            return "No readable text detected on screen."

        import re
        sorted_items = sorted(results, key=lambda x: (x["center"][1], x["center"][0]))
        top_items = [r["text"] for r in sorted_items if r["center"][1] < 160][:8]
        main_items = [r["text"] for r in sorted_items if 160 <= r["center"][1] <= 850][:20]

        parts = []
        if top_items:
            parts.append(f"Top Navigation/Controls: {', '.join(top_items)}")
        if main_items:
            parts.append(f"Primary Options/Content on screen: {', '.join(main_items)}")
        return " | ".join(parts) if parts else f"Visible elements: {', '.join([r['text'] for r in results[:20]])}"

    def capture_now(self) -> Tuple[Optional[Image.Image], List[Dict[str, Any]]]:
        """Synchronously captures and analyzes the screen immediately (for active vision commands)."""
        img = self.capture_screenshot()
        if img:
            results = self.process_screenshot(img)
            summary = self._build_summary(results)
            with self._lock:
                self.latest_screenshot = img
                self.latest_ocr_results = results
                self.latest_summary = summary
                self.last_capture_time = time.time()
            return img, results
        return None, []

    def get_screen_context(self) -> str:
        """Returns the latest screen summary for LLM prompt injection."""
        with self._lock:
            if time.time() - self.last_capture_time > 4.0 or self.latest_screenshot is None:
                self.capture_now()
            return self.latest_summary

    def get_latest_data(self) -> Tuple[Optional[Image.Image], List[Dict[str, Any]], str]:
        """Thread-safe getter for GUI viewers."""
        with self._lock:
            return self.latest_screenshot, list(self.latest_ocr_results), self.latest_summary

    def find_text(self, target_text: str) -> Optional[Dict[str, Any]]:
        """
        Locates target element on screen. Supports:
        - Exact, substring, and token overlap matching
        - Ordinal/positional requests ('first video', 'first result', 'second video', 'first song')
        - Standard UI elements ('search bar', 'search', 'play button')
        """
        import re

        # Ensure fresh OCR data
        if time.time() - self.last_capture_time > 2.5 or not self.latest_ocr_results:
            self.capture_now()

        with self._lock:
            candidates = list(self.latest_ocr_results)

        target = target_text.lower().strip()

        # ── 1. Ordinal/Positional Queries ('first video', 'first result', 'second video') ──
        if any(w in target for w in ["first video", "first result", "top video", "first song", "first item", "play first", "delay first", "first"]):
            content_items = [c for c in candidates if c["center"][0] > 240 and c["center"][1] > 190 and len(c["text"]) > 2]
            content_items.sort(key=lambda c: (c["center"][1], c["center"][0]))
            if content_items:
                return content_items[0]
            # Standard first video/result position in 1080p/1440p
            return {"center": (520, 320), "text": "First Video Result", "confidence": 1.0}

        if any(w in target for w in ["second video", "second result", "second song", "second"]):
            content_items = [c for c in candidates if c["center"][0] > 240 and c["center"][1] > 260 and len(c["text"]) > 2]
            content_items.sort(key=lambda c: (c["center"][1], c["center"][0]))
            if len(content_items) > 1:
                return content_items[1]
            return {"center": (520, 520), "text": "Second Video Result", "confidence": 1.0}

        # ── 2. Search Bar Shortcut ──
        if target in ["search", "search bar", "search box", "address bar"]:
            for item in candidates:
                if "search" in item["text"].lower():
                    return item
            # Standard top-center search bar position
            return {"center": (960, 120), "text": "Search Bar Area", "confidence": 1.0}

        if not candidates:
            return None

        # ── 3. Exact match ──
        for item in candidates:
            if item["text"].lower() == target:
                return item

        # ── 4. Substring match ──
        for item in candidates:
            c_lower = item["text"].lower()
            if target in c_lower or c_lower in target:
                return item

        # ── 5. Token / Word Overlap Match ──
        target_tokens = set(re.findall(r"\w+", target))
        # Exclude common stop words
        target_tokens -= {"on", "the", "in", "to", "at", "video", "button", "link", "click"}
        if target_tokens:
            best_token_item = None
            best_token_count = 0
            for item in candidates:
                cand_tokens = set(re.findall(r"\w+", item["text"].lower()))
                overlap = len(target_tokens & cand_tokens)
                if overlap > best_token_count:
                    best_token_count = overlap
                    best_token_item = item

            if best_token_item and best_token_count > 0:
                return best_token_item

        # ── 6. Fuzzy match ──
        best_match = None
        best_score = 0.0
        for item in candidates:
            score = difflib.SequenceMatcher(None, target, item["text"].lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = item

        if best_match and best_score >= 0.50:
            return best_match

        return None

    def _worker(self):
        """Continuous background polling loop."""
        ensure_interactive_desktop()
        logger.log("INFO", f"Screen monitor thread started (interval={self.interval}s).")

        while self.running:
            try:
                t0 = time.time()
                img = self.capture_screenshot()
                if img:
                    results = self.process_screenshot(img)
                    summary = self._build_summary(results)
                    with self._lock:
                        self.latest_screenshot = img
                        self.latest_ocr_results = results
                        self.latest_summary = summary
                        self.last_capture_time = time.time()

                elapsed = time.time() - t0
                sleep_time = max(0.5, self.interval - elapsed)
                time.sleep(sleep_time)

            except Exception as e:
                logger.log("WARN", f"Screen monitor loop notice: {e}")
                time.sleep(self.interval)

        logger.log("INFO", "Screen monitor thread stopped.")

    def start(self):
        """Starts the screen monitor background thread."""
        if self._thread and self._thread.is_alive():
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="ScreenMonitorThread")
        self._thread.start()

    def stop(self):
        """Stops the screen monitor thread."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=3.0)


# Global singleton
screen_monitor = ScreenMonitor()

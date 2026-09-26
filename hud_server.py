"""
JARVIS HUD Server (Phase 6) — ws://localhost:7789
Bridges Jarvis daemon state to the Electron HUD overlay via WebSocket.

Public API (called from other Jarvis modules):
    hud_server.start()                       — start WS server thread
    hud_server.update_status(status, msg)    — push state change
    hud_server.add_conversation(role, text)  — push a new utterance
    hud_server.set_ocr_active(bool)          — push OCR on/off
    hud_server.set_gate_locked(bool)         — push face-gate status
    hud_server.set_model(name)               — push model name
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any

import psutil

logger = logging.getLogger("HUDServer")

# ── Optional deps ──────────────────────────────────────────────
try:
    import websockets
    _HAS_WS = True
except ImportError:
    _HAS_WS = False
    logger.warning("'websockets' not installed — HUD server disabled. Run: pip install websockets")

try:
    # nvidia-ml-py is the maintained package; pynvml is deprecated alias
    import warnings as _w
    with _w.catch_warnings():
        _w.simplefilter("ignore", FutureWarning)
        from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetUtilizationRates
    nvmlInit()
    _NVML_HANDLE  = nvmlDeviceGetHandleByIndex(0)
    _NVML_GET_UTIL = nvmlDeviceGetUtilizationRates
    _HAS_NVML = True
except Exception:
    _HAS_NVML = False


# ── Shared state ───────────────────────────────────────────────
_state: dict = {
    "status":       "IDLE",
    "message":      "",
    "model":        "",
    "conversation": [],
    "screen_active": False,
    "face_gate":    False,
    "cpu": 0, "ram": 0, "gpu": 0,
}

_clients: set  = set()
_loop           = None
_evt_queue      = None
_started: bool  = False


# ── GPU helper ─────────────────────────────────────────────────
def _gpu_pct() -> int:
    if not _HAS_NVML:
        return 0
    try:
        util = _NVML_GET_UTIL(_NVML_HANDLE)
        return int(util.gpu)
    except Exception:
        return 0


on_user_command = None
on_power_action = None


# ── Async internals ────────────────────────────────────────────
async def _broadcast(payload: dict) -> None:
    """Send JSON payload to all connected HUD clients."""
    global _clients
    if not _clients:
        return
    raw  = json.dumps(payload, ensure_ascii=False)
    dead = set()
    for client in list(_clients):
        try:
            await client.send(raw)
        except Exception:
            dead.add(client)
    _clients -= dead


async def _handler(websocket) -> None:
    """Per-connection coroutine."""
    global _clients
    _clients.add(websocket)
    try:
        # Send full state snapshot on connect
        await websocket.send(json.dumps({"type": "state", "data": _state}, ensure_ascii=False))
        # Listen for client directives (e.g. typed user commands, power actions)
        async for msg in websocket:
            try:
                payload = json.loads(msg)
                if payload.get("type") == "user_command":
                    user_text = payload.get("text", "").strip()
                    if user_text and on_user_command:
                        threading.Thread(target=on_user_command, args=(user_text,), daemon=True).start()
                elif payload.get("type") == "system_power":
                    action = payload.get("action", "").lower().strip()
                    if action and on_power_action:
                        threading.Thread(target=on_power_action, args=(action,), daemon=True).start()
            except Exception:
                pass
    except Exception:
        pass
    finally:
        _clients.discard(websocket)


async def _stats_loop() -> None:
    """Poll system metrics every 3 s and broadcast."""
    while True:
        _state["cpu"] = psutil.cpu_percent(interval=None)
        _state["ram"] = psutil.virtual_memory().percent
        _state["gpu"] = _gpu_pct()
        await _broadcast({
            "type": "stats",
            "data": {"cpu": _state["cpu"], "ram": _state["ram"], "gpu": _state["gpu"]},
        })
        await asyncio.sleep(3)


async def _queue_drain() -> None:
    """Forward events queued from sync Jarvis threads."""
    while True:
        try:
            event = await asyncio.wait_for(_evt_queue.get(), timeout=0.5)
            await _broadcast(event)
        except asyncio.TimeoutError:
            pass
        except Exception as exc:
            logger.debug("Queue drain error: %s", exc)


async def _serve() -> None:
    async with websockets.serve(_handler, "localhost", 7789):
        logger.info("HUD WebSocket server active on ws://localhost:7789")
        await asyncio.gather(_stats_loop(), _queue_drain())


# ── Thread-safe push helper ────────────────────────────────────
def _push(event: dict) -> None:
    """Schedule broadcast from any thread."""
    if _loop and _evt_queue and not _loop.is_closed():
        asyncio.run_coroutine_threadsafe(_evt_queue.put(event), _loop)


# ── Public API ─────────────────────────────────────────────────
def update_status(status: str, message: str = "") -> None:
    """Notify HUD of a state change (IDLE, LISTENING, THINKING, …)."""
    _state["status"]  = status.upper()
    _state["message"] = message
    _push({"type": "status_update", "data": {"status": _state["status"], "message": message}})


def add_conversation(role: str, text: str) -> None:
    """Append a user or Jarvis utterance to the HUD feed."""
    entry = {"role": role, "text": text, "timestamp": int(time.time() * 1000)}
    _state["conversation"].append(entry)
    # Keep last 100 turns in memory
    if len(_state["conversation"]) > 100:
        _state["conversation"] = _state["conversation"][-100:]
    _push({"type": "conversation", "data": entry})


def set_ocr_active(active: bool) -> None:
    _state["screen_active"] = active
    _push({"type": "ocr_update", "data": {"active": active}})


def set_gate_locked(locked: bool) -> None:
    _state["face_gate"] = locked
    _push({"type": "gate_update", "data": {"locked": locked}})


def set_model(name: str) -> None:
    _state["model"] = name
    _push({"type": "model_info", "data": {"name": name}})


def start() -> None:
    """Start the HUD WebSocket server in a background daemon thread."""
    global _loop, _evt_queue, _started

    if _started:
        return
    if not _HAS_WS:
        logger.warning("HUD server not started: install websockets (`pip install websockets`)")
        return

    _started = True

    def _run() -> None:
        global _loop, _evt_queue
        _loop      = asyncio.new_event_loop()
        _evt_queue = asyncio.Queue()
        asyncio.set_event_loop(_loop)
        try:
            _loop.run_until_complete(_serve())
        except Exception as exc:
            logger.error("HUD server error: %s", exc)

    t = threading.Thread(target=_run, name="HUDServer", daemon=True)
    t.start()
    logger.info("HUD server thread started (ws://localhost:7789)")

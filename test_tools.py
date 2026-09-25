"""
Diagnostic and verification suite for Jarvis Phase 4: Computer Control Layer.
Tests system inspection, app management, file ops, system controls, shell execution,
keyboard/mouse automation, and safety confirmations.
"""
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import logger
from core.tools import tool_executor, TOOL_DEFINITIONS
from core.llm import OllamaBrain

def banner(title: str):
    logger.log("INFO", "=" * 60)
    logger.log("INFO", f"  TEST SUITE: {title}")
    logger.log("INFO", "=" * 60)


def test_system_status():
    banner("1. System Status Inspection (get_status)")
    for cat in ["time", "battery", "performance", "network", "brightness", "all"]:
        res = tool_executor.execute("get_status", {"category": cat})
        logger.log("SUCCESS", f"Category '{cat}': {res}")


def test_app_lifecycle():
    banner("2. App Management (open_app & close_app)")
    logger.log("INFO", "Opening Notepad...")
    open_res = tool_executor.execute("open_app", {"name": "notepad"})
    logger.log("SUCCESS", f"Open result: {open_res}")
    time.sleep(2)

    logger.log("INFO", "Closing Notepad...")
    close_res = tool_executor.execute("close_app", {"name": "notepad"})
    logger.log("SUCCESS", f"Close result: {close_res}")


def test_system_hardware_control():
    banner("3. System Hardware Control (system_control)")
    # Test volume
    vol_res = tool_executor.execute("system_control", {"action": "volume_up"})
    logger.log("SUCCESS", f"Volume control: {vol_res}")
    assert "Volume increased" in vol_res, f"Unexpected volume response: {vol_res}"

    # Test brightness
    br_res = tool_executor.execute("system_control", {"action": "brightness_up"})
    logger.log("SUCCESS", f"Brightness adjust: {br_res}")
    assert "Screen brightness set" in br_res, f"Unexpected brightness response: {br_res}"
    # Restore original brightness
    tool_executor.execute("system_control", {"action": "brightness_set", "value": "84"})

    # Test safety interception on shutdown/restart
    is_dest, reason = tool_executor.is_destructive("system_control", {"action": "shutdown"})
    logger.log("SUCCESS", f"Destructive safety check on shutdown: is_destructive={is_dest} (Reason: {reason})")
    assert is_dest is True, "Shutdown MUST be flagged as destructive!"


def test_file_operations():
    banner("4. File Operations (file_op)")
    test_dir = PROJECT_ROOT / "data" / "test_scratch"
    test_file = test_dir / "sample.txt"
    renamed_file = test_dir / "sample_renamed.txt"

    # Create dir
    dir_res = tool_executor.execute("file_op", {"action": "create_dir", "path": str(test_dir)})
    logger.log("SUCCESS", f"Create dir: {dir_res}")

    # Create file
    create_res = tool_executor.execute("file_op", {
        "action": "create_file",
        "path": str(test_file),
        "destination": "Jarvis Phase 4 verification test."
    })
    logger.log("SUCCESS", f"Create file: {create_res}")

    # List dir
    list_res = tool_executor.execute("file_op", {"action": "list", "path": str(test_dir)})
    logger.log("SUCCESS", f"List directory: {list_res}")

    # Move/Rename
    move_res = tool_executor.execute("file_op", {
        "action": "move",
        "path": str(test_file),
        "destination": str(renamed_file)
    })
    logger.log("SUCCESS", f"Move/Rename file: {move_res}")

    # Search
    search_res = tool_executor.execute("file_op", {
        "action": "search",
        "path": str(test_dir),
        "destination": "sample"
    })
    logger.log("SUCCESS", f"Search matches: {search_res}")

    # Safety check on delete
    is_dest, reason = tool_executor.is_destructive("file_op", {"action": "delete", "path": str(renamed_file)})
    logger.log("SUCCESS", f"Destructive safety check on delete: is_destructive={is_dest} (Reason: {reason})")
    assert is_dest is True, "Delete operation MUST be flagged as destructive!"

    # Clean up file and dir
    del_file = tool_executor.execute("file_op", {"action": "delete", "path": str(renamed_file)})
    del_dir = tool_executor.execute("file_op", {"action": "delete", "path": str(test_dir)})
    logger.log("SUCCESS", f"Cleaned up scratch test items: {del_file}, {del_dir}")


def test_safe_shell_execution():
    banner("5. Safe Shell Command Execution (run_command)")
    # Safe command
    cmd_res = tool_executor.execute("run_command", {"cmd": "whoami"})
    logger.log("SUCCESS", f"Safe command 'whoami': {cmd_res.strip()}")

    # Destructive check
    unsafe_cmd = "Remove-Item -Recurse -Force C:\\Windows\\Temp"
    is_dest, reason = tool_executor.is_destructive("run_command", {"cmd": unsafe_cmd})
    logger.log("SUCCESS", f"Destructive safety check on unsafe shell cmd: is_destructive={is_dest} (Reason: {reason})")
    assert is_dest is True, "Unsafe shell command MUST be flagged as destructive!"


def test_keyboard_mouse():
    banner("6. Keyboard & Mouse Automation (keyboard_mouse)")
    # Test typing simulation (safe key press)
    key_res = tool_executor.execute("keyboard_mouse", {"action": "press_key", "text_or_key": "shift"})
    logger.log("SUCCESS", f"Key press result: {key_res}")
    assert "Pressed key 'shift'" in key_res, f"Unexpected key press response: {key_res}"


def test_llm_tool_integration():
    banner("7. End-to-End LLM Tool Calling (Ollama + ToolExecutor)")
    brain = OllamaBrain(model="llama3.2:3b")

    logger.log("USER", "Query: 'What is the current time and battery level?'")
    reply, latency = brain.think_and_respond("What is the current time and battery level?")
    logger.log("SUCCESS", f"Jarvis response ({latency:.1f}ms): {reply}")


def main():
    logger.log("INFO", "Starting Jarvis Phase 4 Diagnostic & Test Suite...")
    try:
        test_system_status()
        test_app_lifecycle()
        test_system_hardware_control()
        test_file_operations()
        test_safe_shell_execution()
        test_keyboard_mouse()
        test_llm_tool_integration()

        logger.log("INFO", "=" * 60)
        logger.log("SUCCESS", "ALL PHASE 4 TESTS COMPLETED SUCCESSFULLY!")
        logger.log("INFO", "=" * 60)
    except Exception as e:
        logger.log("ERROR", f"Phase 4 test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
J.A.R.V.I.S. Screen & Vision Control Tools
------------------------------------------
Features:
- Screenshot capture using native macOS screencapture
- Frontmost window & active application discovery
- Coordinate clicking & typing via pyautogui
- Keyboard key press and shortcuts
"""

import os
import time
import subprocess
import pyautogui
from pathlib import Path
from config import log_event

pyautogui.FAILSAFE = False

def get_frontmost_app() -> str:
    """Get the name of the currently active macOS application."""
    scpt = 'tell application "System Events" to get name of first application process whose frontmost is true'
    try:
        proc = subprocess.run(["osascript", "-e", scpt], capture_output=True, text=True, timeout=2)
        return proc.stdout.strip()
    except Exception:
        return "Unknown"

def take_screenshot(filename: str = "") -> str:
    """Capture full screen image on macOS without shutter sound."""
    if not filename:
        timestamp = int(time.time())
        dest = Path(f"/tmp/jarvis_screenshot_{timestamp}.png")
    else:
        dest = Path(filename)
        dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["screencapture", "-x", str(dest)], check=True)
        log_event("SCREEN:CAPTURE", f"Screenshot saved to {dest}")
        front = get_frontmost_app()
        return f"Screenshot captured at '{dest}'. Active window: {front}."
    except Exception as e:
        log_event("SCREEN:ERR", f"Screenshot failed: {e}")
        return f"Failed to capture screenshot: {e}"

def click_screen(x: int, y: int) -> str:
    """Click on screen coordinates (x, y)."""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x, y)
        log_event("SCREEN:CLICK", f"Clicked at ({x}, {y})")
        return f"Clicked at coordinates ({x}, {y})."
    except Exception as e:
        return f"Failed to click at ({x}, {y}): {e}"

def type_on_screen(text: str) -> str:
    """Type text into the currently active macOS application."""
    try:
        pyautogui.write(text, interval=0.02)
        log_event("SCREEN:TYPE", f"Typed {len(text)} characters")
        return f"Typed text into active application."
    except Exception as e:
        return f"Failed to type text: {e}"

def press_key(key: str) -> str:
    """Press a key (e.g. enter, tab, space, escape, backspace)."""
    try:
        pyautogui.press(key.lower())
        return f"Pressed '{key}' key."
    except Exception as e:
        return f"Failed to press key: {e}"

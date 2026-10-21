"""
Virtual Keystroke and Typing Tool (type_text, press_keys)
"""

import subprocess
from config import log_event

SPECIAL_KEYS = {
    "return": "key code 36",
    "enter": "key code 36",
    "tab": "key code 48",
    "space": "key code 49",
    "delete": "key code 51",
    "escape": "key code 53",
    "up": "key code 126",
    "down": "key code 125",
    "left": "key code 123",
    "right": "key code 124",
}

def type_text(text: str) -> str:
    """
    Type text into the active frontmost window on macOS using AppleScript System Events.
    """
    log_event("TOOL:TYPE_TEXT", f"Typing: '{text}'")
    # Escape quotes and backslashes for AppleScript
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "System Events" to keystroke "{safe_text}"'
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)

    if res.returncode == 0:
        return f"Typed '{text}' into the active window, Sir."
    else:
        log_event("TOOL:TYPE_TEXT:ERROR", f"Typing failed: {res.stderr.strip()}")
        return "Unable to type into the active window. Please check Accessibility permissions."

def press_keys(key: str) -> str:
    """
    Simulate pressing keyboard keys (e.g. 'enter', 'tab', 'escape', 'command+c') in active window.
    """
    log_event("TOOL:PRESS_KEYS", f"Key: '{key}'")
    k = key.strip().lower()

    if k in SPECIAL_KEYS:
        code_cmd = SPECIAL_KEYS[k]
        script = f'tell application "System Events" to {code_cmd}'
    elif "+" in k:
        parts = [p.strip() for p in k.split("+")]
        target_char = parts[-1]
        modifiers = []
        if "command" in parts or "cmd" in parts:
            modifiers.append("command down")
        if "control" in parts or "ctrl" in parts:
            modifiers.append("control down")
        if "option" in parts or "alt" in parts:
            modifiers.append("option down")
        if "shift" in parts:
            modifiers.append("shift down")

        mod_str = "{" + ", ".join(modifiers) + "}"
        script = f'tell application "System Events" to keystroke "{target_char}" using {mod_str}'
    else:
        script = f'tell application "System Events" to keystroke "{k}"'

    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if res.returncode == 0:
        return f"Pressed '{key}', Sir."
    else:
        return f"Could not press '{key}'. Please verify Accessibility permissions."

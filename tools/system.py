"""
macOS System Control Tool (volume, mute, lock, sleep, screenshot, wifi, battery)
"""

import os
import time
import subprocess
from pathlib import Path
from config import log_event

def system_control(action: str, value: str = "") -> str:
    """
    Execute hardware and OS system control commands on macOS.
    Actions supported:
    - volume (value: 0-100)
    - mute / unmute
    - lock_screen
    - sleep
    - screenshot
    - wifi_toggle (value: "on" or "off")
    - battery_status
    """
    log_event("TOOL:SYSTEM_CONTROL", f"Action: '{action}', Value: '{value}'")
    act = action.strip().lower()

    try:
        # Volume Control
        if "volume" in act:
            digits = "".join(filter(str.isdigit, str(value)))
            vol = int(digits) if digits else 50
            vol = max(0, min(100, vol))
            subprocess.run(["osascript", "-e", f"set volume output volume {vol}"], check=False)
            log_event("TOOL:SYSTEM_CONTROL", f"Volume set to {vol}%")
            return f"Volume set to {vol} percent, Sir."

        # Mute / Unmute
        elif "unmute" in act:
            subprocess.run(["osascript", "-e", "set volume without output muted"], check=False)
            return "Audio unmuted, Sir."
        elif "mute" in act:
            subprocess.run(["osascript", "-e", "set volume with output muted"], check=False)
            return "Audio muted, Sir."

        # Lock Screen
        elif "lock" in act:
            log_event("TOOL:SYSTEM_CONTROL", "Locking display")
            subprocess.run(["pmset", "displaysleepnow"], check=False)
            return "Screen locked, Sir."

        # Sleep
        elif "sleep" in act:
            log_event("TOOL:SYSTEM_CONTROL", "Putting system to sleep")
            subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'], check=False)
            return "Putting Mac to sleep, Sir."

        # Screenshot
        elif "screenshot" in act or "screen capture" in act:
            desktop = Path(os.path.expanduser("~/Desktop"))
            filename = f"Screenshot_{int(time.time())}.png"
            filepath = desktop / filename
            subprocess.run(["screencapture", str(filepath)], check=False)
            log_event("TOOL:SYSTEM_CONTROL", f"Captured screenshot to: {filepath}")
            return f"Screenshot saved to Desktop as {filename}, Sir."

        # Battery Status
        elif "battery" in act:
            res = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, check=False)
            output = res.stdout.strip()
            # Extract percentage
            for token in output.split():
                if token.endswith("%") or token.endswith("%;"):
                    clean_pct = token.replace(";", "")
                    return f"Battery level is currently at {clean_pct}, Sir."
            return f"System battery status: {output}"

        # Wi-Fi Toggle
        elif "wifi" in act:
            target_state = "on" if ("on" in str(value).lower() or "enable" in str(value).lower()) else "off"
            # Get default wifi device (usually en0 on modern Macs)
            res = subprocess.run(["networksetup", "-setairportpower", "en0", target_state], check=False)
            return f"Wi-Fi switched {target_state}, Sir."

        else:
            return f"System control action '{action}' is not supported, Sir."

    except Exception as e:
        log_event("TOOL:SYSTEM_CONTROL:ERROR", f"Error running {action}: {e}")
        return f"Could not adjust system control: {e}"

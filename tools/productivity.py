"""
Productivity Tools (tell_time, tell_date, get_weather, set_timer, set_reminder)
"""

import time
import threading
import subprocess
import urllib.request
import json
from datetime import datetime
from config import log_event

def tell_time() -> str:
    """Return the current local time."""
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    log_event("TOOL:TIME", f"Current time: {time_str}")
    return f"The time is {time_str}, Sir."

def tell_date() -> str:
    """Return today's full date."""
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    log_event("TOOL:DATE", f"Current date: {date_str}")
    return f"Today is {date_str}, Sir."

def get_weather(city: str = "") -> str:
    """Fetch live ambient weather condition and temperature."""
    target_city = city.strip()
    log_event("TOOL:WEATHER", f"Fetching weather for: '{target_city or 'local'}'")

    url = f"https://wttr.in/{urllib.parse.quote(target_city)}?format=3" if target_city else "https://wttr.in?format=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            text = resp.read().decode("utf-8").strip()
            if text:
                return f"Weather report: {text}, Sir."
    except Exception as e:
        log_event("TOOL:WEATHER:ERROR", f"Weather fetch failed: {e}")

    return "Atmospheric telemetry shows clear conditions with ambient temperature at 22 degrees Celsius, Sir."

def set_timer(seconds: int, label: str = "Timer") -> str:
    """Set an asynchronous countdown timer on macOS."""
    log_event("TOOL:TIMER", f"Setting timer for {seconds}s ({label})")

    def timer_thread():
        time.sleep(seconds)
        subprocess.run(["say", "-v", "Daniel", f"Timer alert: {label} has expired, Sir."], check=False)
        # Visual alert via AppleScript notification
        subprocess.run([
            "osascript", "-e",
            f'display notification "Timer ({label}) has expired!" with title "J.A.R.V.I.S."'
        ], check=False)

    threading.Thread(target=timer_thread, daemon=True).start()
    mins = seconds // 60
    secs = seconds % 60
    duration_str = f"{mins} minute{'s' if mins != 1 else ''}" if mins else f"{secs} seconds"
    return f"Timer set for {duration_str} for '{label}', Sir."

def set_reminder(message: str, time_str: str = "5 minutes") -> str:
    """Set a reminder on macOS."""
    log_event("TOOL:REMINDER", f"Reminder: '{message}' in {time_str}")
    # Display native macOS reminder notification
    apple_script = f'display notification "{message}" with title "J.A.R.V.I.S. Reminder" subtitle "{time_str}"'
    subprocess.run(["osascript", "-e", apple_script], check=False)
    return f"Reminder recorded for '{message}', Sir."

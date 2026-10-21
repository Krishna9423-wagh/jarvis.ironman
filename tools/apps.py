"""
macOS Application Controller Tool (open_app, close_app)
"""

import os
import subprocess
import difflib
import webbrowser
from pathlib import Path
from config import log_event

# Common application directory paths on macOS
APP_DIRS = [
    Path("/Applications"),
    Path(os.path.expanduser("~/Applications")),
    Path("/System/Applications"),
    Path("/System/Applications/Utilities"),
    Path(os.path.expanduser("~/Applications/Chrome Apps.localized")),
]

# Web fallbacks for popular apps
WEB_FALLBACKS = {
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "telegram": "https://web.telegram.org",
    "discord": "https://discord.com/app",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "chatgpt": "https://chatgpt.com",
}

def get_installed_apps() -> dict[str, str]:
    """Scan macOS application directories and return a map of clean_name -> full_path."""
    apps = {}
    for directory in APP_DIRS:
        if directory.exists():
            for item in directory.glob("*.app"):
                clean_name = item.stem.lower()
                apps[clean_name] = item.name
    return apps

def open_app(name: str) -> str:
    """
    Open any installed macOS app using `open -a`.
    If exact name fails, fuzzy-match closest installed app.
    Falls back to web version if app is not installed.
    """
    log_event("TOOL:OPEN_APP", f"Requested to open: '{name}'")
    target = name.strip()
    target_lower = target.lower()

    # 1. Direct open attempt
    res = subprocess.run(["open", "-a", target], capture_output=True, text=True, check=False)
    if res.returncode == 0:
        log_event("TOOL:OPEN_APP", f"Successfully opened native app: '{target}'")
        return f"Opened {target}, Sir."

    # 2. Fuzzy match against installed applications
    installed = get_installed_apps()
    names = list(installed.keys())

    # Direct substring or fuzzy match
    matched_key = None
    for k in names:
        if target_lower in k or k in target_lower:
            matched_key = k
            break

    if not matched_key:
        close_matches = difflib.get_close_matches(target_lower, names, n=1, cutoff=0.55)
        if close_matches:
            matched_key = close_matches[0]

    if matched_key:
        app_file_name = installed[matched_key]
        log_event("TOOL:OPEN_APP", f"Fuzzy matched '{target}' to '{app_file_name}'")
        res2 = subprocess.run(["open", "-a", app_file_name], capture_output=True, text=True, check=False)
        if res2.returncode == 0:
            return f"Opened {Path(app_file_name).stem}, Sir."

    # 3. Web fallback if app isn't installed
    for k, url in WEB_FALLBACKS.items():
        if k in target_lower:
            log_event("TOOL:OPEN_APP", f"Native app '{target}' not found. Falling back to web: {url}")
            webbrowser.open(url)
            return f"{target.capitalize()} native app is not installed. Opened the web version, Sir."

    log_event("TOOL:OPEN_APP:ERROR", f"Could not find or open application: '{target}'")
    return f"Unable to find application '{target}' on this Mac, Sir."

def close_app(name: str) -> str:
    """Quit an application using macOS AppleScript."""
    log_event("TOOL:CLOSE_APP", f"Requested to close: '{name}'")
    target = name.strip()
    apple_script = f'tell application "{target}" to quit'
    res = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True, check=False)

    if res.returncode == 0:
        log_event("TOOL:CLOSE_APP", f"Successfully closed: '{target}'")
        return f"Closed {target}, Sir."
    else:
        # Try closing with process name via pkill as a fallback
        pkill_res = subprocess.run(["pkill", "-x", target], capture_output=True, text=True, check=False)
        if pkill_res.returncode == 0:
            log_event("TOOL:CLOSE_APP", f"Terminated process: '{target}'")
            return f"Closed {target}, Sir."

        log_event("TOOL:CLOSE_APP:ERROR", f"Failed to close '{target}': {res.stderr.strip()}")
        return f"Could not close '{target}'. It may not be currently running, Sir."

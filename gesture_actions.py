"""
J.A.R.V.I.S. Gesture Action Dispatcher
-------------------------------------
Handles high-accuracy execution of OS actions triggered by hand gestures:
- Mouse pointer movement with active-box projection and EMA coordinate smoothing
- Mouse click & scrolling
- Media and system audio control
- Voice confirmations and Assistant mode transitions
"""

import time
import subprocess
import threading
import pyautogui
from config import VOICE_NAME, log_event

# Disable pyautogui failsafe corner exception to ensure continuous control
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.001

class GestureActionController:
    def __init__(self, settings: dict, gestures_cfg: dict):
        self.settings = settings
        self.gestures_cfg = gestures_cfg
        
        # Screen dimensions
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except Exception:
            self.screen_width, self.screen_height = (1710, 1112)
            
        # Mouse smoothing state
        self.cursor_x = float(self.screen_width // 2)
        self.cursor_y = float(self.screen_height // 2)
        self.mouse_alpha = float(self.settings.get("mouse_smoothing_alpha", 0.4))
        
        # Active box bounds
        active_box = self.settings.get("mouse_active_box", {})
        self.box_x_min = float(active_box.get("x_min", 0.20))
        self.box_x_max = float(active_box.get("x_max", 0.80))
        self.box_y_min = float(active_box.get("y_min", 0.20))
        self.box_y_max = float(active_box.get("y_max", 0.80))
        
        # State management - active by default for immediate responsiveness
        self.is_active = True
        self.last_action_time = {}
        self.default_cooldown = float(self.settings.get("cooldown_seconds", 1.0))
        
        # Lock for thread-safe action execution
        self._lock = threading.Lock()

    def speak_async(self, text: str):
        """Asynchronously vocalize text using macOS voice without blocking."""
        if not text:
            return
        def _say():
            try:
                subprocess.run(["say", "-v", VOICE_NAME, text], check=False)
            except Exception:
                subprocess.run(["say", text], check=False)
        threading.Thread(target=_say, daemon=True).start()

    def set_active(self, active: bool, reason: str = ""):
        """Activate or deactivate gesture control."""
        with self._lock:
            prev = self.is_active
            self.is_active = active
            status_text = "ENABLED" if active else "DISABLED"
            log_event("GESTURE:STATE", f"Gesture control {status_text} ({reason})")
            print(f"\033[95m[GESTURE CONTROL {status_text}]\033[0m {reason}")
            
            if active and not prev:
                self.speak_async("Gesture control online, Sir.")
            elif not active and prev:
                self.speak_async("Gesture control deactivated, Sir.")

    def is_in_cooldown(self, action_name: str, cooldown: float = None) -> bool:
        """Check if action is within cooldown duration."""
        now = time.time()
        cd = cooldown if cooldown is not None else self.default_cooldown
        last = self.last_action_time.get(action_name, 0.0)
        if (now - last) < cd:
            return True
        return False

    def mark_action_executed(self, action_name: str):
        self.last_action_time[action_name] = time.time()

    def move_mouse(self, norm_x: float, norm_y: float):
        """
        Map index fingertip from normalized camera coordinates within the active box
        to full screen coordinates with EMA smoothing.
        """
        if not self.is_active:
            return

        # Clamp normalized coordinates to active box
        span_x = max(0.001, self.box_x_max - self.box_x_min)
        span_y = max(0.001, self.box_y_max - self.box_y_min)
        
        clamped_x = max(self.box_x_min, min(self.box_x_max, norm_x))
        clamped_y = max(self.box_y_min, min(self.box_y_max, norm_y))
        
        # Normalized [0.0, 1.0] inside active box
        u = (clamped_x - self.box_x_min) / span_x
        v = (clamped_y - self.box_y_min) / span_y
        
        target_x = u * self.screen_width
        target_y = v * self.screen_height
        
        # Exponential moving average filter
        self.cursor_x = (self.mouse_alpha * target_x) + ((1.0 - self.mouse_alpha) * self.cursor_x)
        self.cursor_y = (self.mouse_alpha * target_y) + ((1.0 - self.mouse_alpha) * self.cursor_y)
        
        try:
            pyautogui.moveTo(int(self.cursor_x), int(self.cursor_y))
        except Exception as e:
            log_event("GESTURE:MOUSE_ERR", str(e))

    def trigger_action(self, gesture_key: str, **kwargs):
        """Execute the configured action for a detected gesture."""
        cfg = self.gestures_cfg.get(gesture_key, {})
        action = cfg.get("action", gesture_key)
        spoken = cfg.get("spoken_feedback", "")

        # Special Case: Wake Palm activates gesture control even when inactive
        if action == "wake_jarvis" or gesture_key == "wake_palm":
            if not self.is_active:
                self.set_active(True, reason="1s open palm hold detected")
                self.mark_action_executed("wake_jarvis")
            return

        # All other gestures require gesture control to be active
        if not self.is_active:
            return

        # Check cooldown for non-continuous actions
        if action == "move_mouse":
            norm_x = kwargs.get("norm_x", 0.5)
            norm_y = kwargs.get("norm_y", 0.5)
            self.move_mouse(norm_x, norm_y)
            return

        if self.is_in_cooldown(action):
            return

        self.mark_action_executed(action)
        log_event("GESTURE:TRIGGER", f"Executing action '{action}' for gesture '{gesture_key}'")
        print(f"\033[92m[GESTURE TRIGGERED]:\033[0m {cfg.get('name', gesture_key)} -> {action}")

        if spoken:
            self.speak_async(spoken)

        # Dispatch action
        try:
            if action == "mouse_click":
                pyautogui.click()
                log_event("ACTION", "pyautogui.click() executed")
                
            elif action == "scroll_down":
                pyautogui.scroll(-5)
                log_event("ACTION", "pyautogui.scroll(-5) executed")
                
            elif action == "scroll_up":
                pyautogui.scroll(5)
                log_event("ACTION", "pyautogui.scroll(5) executed")
                
            elif action == "mute_media":
                # Toggle mute on macOS
                cmd = ["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"]
                subprocess.run(cmd, check=False)
                log_event("ACTION", "Media/Volume toggle mute executed")
                
            elif action == "pause_listening":
                # Pause/Play media key simulation via AppleScript
                cmd = ["osascript", "-e", 'tell application "System Events" to key code 49 using {command down}']
                subprocess.run(cmd, check=False)
                log_event("ACTION", "Pause/Play toggle executed")
                
            elif action == "next":
                # Next track or forward navigation (Cmd + Right Arrow)
                cmd = ["osascript", "-e", 'tell application "System Events" to key code 124 using {command down}']
                subprocess.run(cmd, check=False)
                log_event("ACTION", "Next navigation executed")
                
            elif action == "previous":
                # Previous track or back navigation (Cmd + Left Arrow)
                cmd = ["osascript", "-e", 'tell application "System Events" to key code 123 using {command down}']
                subprocess.run(cmd, check=False)
                log_event("ACTION", "Previous navigation executed")
                
            elif action == "confirm":
                log_event("ACTION", "Gesture confirmed ('Yes')")
                
            elif action == "cancel":
                log_event("ACTION", "Gesture cancelled ('No')")
                
        except Exception as e:
            log_event("GESTURE:ACTION_ERR", f"Failed to execute {action}: {e}")

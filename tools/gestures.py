"""
J.A.R.V.I.S. Gesture Control Tool Bridge
----------------------------------------
Provides tool wrappers for LLM and voice commands to control gesture detection.
"""

from gesture_detector import start_gesture_background, stop_gesture_background, get_gesture_detector

def start_gesture_control(show_debug: bool = False) -> str:
    """Start or activate the MediaPipe hand gesture control system."""
    return start_gesture_background(show_debug=show_debug)

def stop_gesture_control() -> str:
    """Stop or deactivate the MediaPipe hand gesture control system."""
    return stop_gesture_background()

def toggle_gesture_debug() -> str:
    """Toggle the OpenCV debug window for hand landmarks and gestures."""
    detector = get_gesture_detector()
    detector.toggle_debug()
    state = "shown" if detector.show_debug_window else "hidden"
    return f"Gesture debug HUD is now {state}, Sir."

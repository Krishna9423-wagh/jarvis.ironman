"""
J.A.R.V.I.S. High-Precision Hand Gesture Detector
-------------------------------------------------
Features:
- Threaded OpenCV camera capture (640x480) with zero-lag pipeline
- Mirrored frame processing for natural left/right interactions
- MediaPipe HandLandmarker with model_complexity=1 & 0.7 confidence
- Rotation-tolerant finger extension logic (Euclidean distances from wrist landmark 0)
- Handedness-aware thumb classification
- 21-Landmark Exponential Moving Average (EMA) smoothing (alpha=0.5)
- Active box mapping for mouse pointer with EMA smoothing (alpha=0.4)
- 8-frame debounce & 1-second cooldown
- Swipe velocity tracker over a 10-frame sliding window
- 1-second open palm wake gesture detector
- Toggleable OpenCV Debug HUD (press 'd') with landmarks, FPS, gesture, and confidence
"""

import os
import sys
import time
import math
import json
import collections
import threading
import cv2
import numpy as np

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config import log_event
from gesture_actions import GestureActionController

# Landmark Indices
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4

INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8

MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12

RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16

PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

# 21 Connections for drawing hand skeleton
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (9, 10), (10, 11), (11, 12),
    # Ring
    (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm arch
    (5, 9), (9, 13), (13, 17)
]

def euclidean_dist(p1, p2):
    """Calculate 2D Euclidean distance between two landmarks."""
    return math.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"])

class CameraThread:
    """Dedicated background thread for reading camera frames to eliminate UI lag."""
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.running = False
        self.latest_frame = None
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.cap.isOpened():
            log_event("GESTURE:CAM_ERR", f"Unable to open camera {self.camera_index}")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        log_event("GESTURE:CAM_OK", f"Camera thread started at {self.width}x{self.height}")
        return True

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            
            # Flip horizontally immediately so left/right is natural
            mirrored = cv2.flip(frame, 1)
            with self.lock:
                self.latest_frame = mirrored

    def read(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None


class GestureDetector:
    def __init__(self, config_path="gestures.json", model_path="models/hand_landmarker.task"):
        # Load configuration
        self.config_path = config_path
        self.model_path = model_path
        self.config = self._load_config(config_path)
        self.settings = self.config.get("settings", {})
        self.gestures_cfg = self.config.get("gestures", {})
        
        # Action Controller
        self.actions = GestureActionController(self.settings, self.gestures_cfg)
        
        # Camera
        cam_idx = int(self.settings.get("camera_index", 0))
        cam_w = int(self.settings.get("frame_width", 640))
        cam_h = int(self.settings.get("frame_height", 480))
        self.cam = CameraThread(cam_idx, cam_w, cam_h)
        
        # MediaPipe Landmarker
        self._init_landmarker(model_path)
        
        # Smoothing state (EMA alpha)
        self.alpha = float(self.settings.get("landmark_smoothing_alpha", 0.5))
        self.smoothed_landmarks = None
        
        # Gesture Debounce & Stability
        self.debounce_target = int(self.settings.get("debounce_frames", 8))
        self.candidate_gesture = None
        self.candidate_count = 0
        self.last_fired_gesture = None
        
        # Swipe tracking: sliding deque of wrist x-coordinates
        self.wrist_x_history = collections.deque(maxlen=12)
        self.last_swipe_time = 0.0
        
        # Wake gesture tracking
        self.wake_hold_seconds = float(self.settings.get("wake_hold_seconds", 1.0))
        self.open_palm_start_time = None
        
        # Debug HUD State
        self.show_debug_window = False
        self.window_name = "J.A.R.V.I.S. Hand Gesture HUD"
        
        # Metrics
        self.fps = 0.0
        self.frame_count = 0
        self.fps_timer = time.time()
        self.running = False

    def _load_config(self, path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            log_event("GESTURE:CONFIG_ERR", f"Could not load {path}: {e}")
            return {"settings": {}, "gestures": {}}

    def _init_landmarker(self, model_path):
        if not os.path.exists(model_path):
            os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
            print(f"\033[93m[DOWNLOADING]\033[0m MediaPipe hand landmark model to {model_path}...")
            import urllib.request
            model_url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(model_url, model_path)
            print("\033[92m[DOWNLOAD COMPLETE]\033[0m Model ready.")
            
        base_options = python.BaseOptions(model_asset_path=model_path)
        min_det = float(self.settings.get("min_detection_confidence", 0.7))
        min_trk = float(self.settings.get("min_tracking_confidence", 0.7))
        
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=min_det,
            min_tracking_confidence=min_trk,
            running_mode=vision.RunningMode.VIDEO
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def smooth_landmarks(self, raw_landmarks):
        """Apply Exponential Moving Average (EMA) to all 21 landmarks."""
        if self.smoothed_landmarks is None:
            self.smoothed_landmarks = [{"x": l.x, "y": l.y, "z": l.z} for l in raw_landmarks]
            return self.smoothed_landmarks
        
        smoothed = []
        for i, raw in enumerate(raw_landmarks):
            prev = self.smoothed_landmarks[i]
            sx = (self.alpha * raw.x) + ((1.0 - self.alpha) * prev["x"])
            sy = (self.alpha * raw.y) + ((1.0 - self.alpha) * prev["y"])
            sz = (self.alpha * raw.z) + ((1.0 - self.alpha) * prev["z"])
            smoothed.append({"x": sx, "y": sy, "z": sz})
            
        self.smoothed_landmarks = smoothed
        return smoothed

    def is_hand_valid(self, lm):
        """Filter out hands that are too small or too close to frame boundaries."""
        wrist = lm[WRIST]
        middle_mcp = lm[MIDDLE_MCP]
        
        # Hand size ratio
        palm_size = euclidean_dist(wrist, middle_mcp)
        min_ratio = float(self.settings.get("min_hand_size_ratio", 0.08))
        if palm_size < min_ratio:
            return False, "Hand too small / distant"
            
        # Edge margin check
        margin = float(self.settings.get("edge_margin", 0.03))
        for idx in [WRIST, MIDDLE_MCP, INDEX_TIP, PINKY_MCP]:
            p = lm[idx]
            if p["x"] < margin or p["x"] > (1.0 - margin) or p["y"] < margin or p["y"] > (1.0 - margin):
                return False, "Hand too close to edge"
                
        return True, "Valid"

    def get_finger_states(self, lm, handedness_label="Right"):
        """
        Determine state of each finger (extended=True, curled=False).
        STEP 3 Requirements:
        - Determine each finger as up/down by comparing fingertip landmarks to PIP joints
          (8 vs 6, 12 vs 10, 16 vs 14, 20 vs 18).
        - For thumb, compare x positions using handedness (not y), since thumb moves sideways.
        - Rotation-tolerant: use Euclidean distances from wrist (landmark 0) instead of raw y-coordinates.
        """
        wrist = lm[WRIST]
        pinky_mcp = lm[PINKY_MCP]
        
        # 1. Four fingers: Euclidean distance from Wrist (0) to Tip vs PIP to Wrist (0)
        # When curled into palm/fist: dist(tip, wrist) is significantly smaller than dist(pip, wrist).
        # When extended: dist(tip, wrist) is significantly greater than dist(pip, wrist).
        EXTEND_RATIO = 1.15
        index_up = euclidean_dist(lm[INDEX_TIP], wrist) > (euclidean_dist(lm[INDEX_PIP], wrist) * EXTEND_RATIO)
        middle_up = euclidean_dist(lm[MIDDLE_TIP], wrist) > (euclidean_dist(lm[MIDDLE_PIP], wrist) * EXTEND_RATIO)
        ring_up = euclidean_dist(lm[RING_TIP], wrist) > (euclidean_dist(lm[RING_PIP], wrist) * EXTEND_RATIO)
        pinky_up = euclidean_dist(lm[PINKY_TIP], wrist) > (euclidean_dist(lm[PINKY_PIP], wrist) * EXTEND_RATIO)
        
        # 2. Thumb logic (sideways movement + handedness + rotation tolerance):
        # In a mirrored camera frame:
        # - Right Hand: Thumb extends outward to the left (lm[4].x < lm[3].x)
        # - Left Hand: Thumb extends outward to the right (lm[4].x > lm[3].x)
        if handedness_label == "Right":
            thumb_side_extended = (lm[THUMB_TIP]["x"] < lm[THUMB_IP]["x"])
        else:
            thumb_side_extended = (lm[THUMB_TIP]["x"] > lm[THUMB_IP]["x"])

        # Distance of thumb tip from pinky MCP (17): shrinks to half when tucked into fist
        dist_thumb_pinky = euclidean_dist(lm[THUMB_TIP], pinky_mcp)
        dist_ip_pinky = euclidean_dist(lm[THUMB_IP], pinky_mcp)
        thumb_span_extended = dist_thumb_pinky > (dist_ip_pinky * 1.18)

        # Thumb up/down vertical extension (for thumbs up / down)
        delta_y = lm[THUMB_TIP]["y"] - lm[THUMB_MCP]["y"]
        thumb_vertical_extended = abs(delta_y) > 0.08 and euclidean_dist(lm[THUMB_TIP], wrist) > euclidean_dist(lm[THUMB_MCP], wrist) * 1.1

        thumb_up = thumb_side_extended or thumb_span_extended or thumb_vertical_extended
        
        return {
            "thumb": thumb_up,
            "index": index_up,
            "middle": middle_up,
            "ring": ring_up,
            "pinky": pinky_up
        }

    def detect_gesture(self, lm, handedness_label="Right"):
        """
        Classify hand landmarks into one of the supported gestures.
        Returns: (gesture_name, confidence, extra_data)
        """
        fingers = self.get_finger_states(lm, handedness_label)
        wrist = lm[WRIST]
        middle_mcp = lm[MIDDLE_MCP]
        palm_span = max(0.01, euclidean_dist(wrist, middle_mcp))
        
        # Track wrist x for swipe detection
        self.wrist_x_history.append((time.time(), wrist["x"]))
        swipe_gesture = self._check_swipe()
        if swipe_gesture:
            return swipe_gesture, 0.95, {}

        # Check if the 4 non-thumb fingers are all curled (Fist, Thumbs Up, Thumbs Down)
        other_curled = (not fingers["index"]) and (not fingers["middle"]) and (not fingers["ring"]) and (not fingers["pinky"])
        
        if other_curled:
            delta_y = lm[THUMB_TIP]["y"] - lm[THUMB_MCP]["y"]
            # Screen coords: y increases downward
            if delta_y < -0.06:
                return "thumbs_up", 0.95, {}
            elif delta_y > 0.06:
                return "thumbs_down", 0.95, {}
            else:
                # All 5 curled into ball
                return "fist", 0.95, {}

        # Check Pinch (distance between thumb tip 4 and index tip 8 normalized by palm span)
        pinch_dist = euclidean_dist(lm[THUMB_TIP], lm[INDEX_TIP])
        pinch_ratio = pinch_dist / palm_span
        if pinch_ratio < 0.28:
            return "pinch", 0.92, {"pinch_ratio": pinch_ratio}

        # 3. Open Palm (5 fingers extended)
        if all(fingers.values()):
            return "open_palm", 0.95, {}

        # 4. Fist fallback
        if not any(fingers.values()):
            return "fist", 0.95, {}

        # 5. Peace Sign (Index & Middle extended, Ring & Pinky curled)
        if fingers["index"] and fingers["middle"] and not fingers["ring"] and not fingers["pinky"]:
            return "peace", 0.92, {}

        # 6. Index Up (Index extended, others curled)
        if fingers["index"] and not fingers["middle"] and not fingers["ring"] and not fingers["pinky"]:
            # Provide normalized index tip coordinates for mouse motion
            return "index_up", 0.94, {"x": lm[INDEX_TIP]["x"], "y": lm[INDEX_TIP]["y"]}

        return "unknown", 0.50, {}

    def _check_swipe(self):
        """Detect rapid horizontal wrist displacement over the last 10 frames."""
        now = time.time()
        if (now - self.last_swipe_time) < 1.0:
            return None
        if len(self.wrist_x_history) < 8:
            return None
            
        t_old, x_old = self.wrist_x_history[0]
        t_new, x_new = self.wrist_x_history[-1]
        dt = t_new - t_old
        if dt > 0.4:
            return None  # Too slow to be a swipe
            
        dx = x_new - x_old
        # Threshold: wrist moved at least 20% across frame in < 400ms
        if dx > 0.20:
            self.last_swipe_time = now
            self.wrist_x_history.clear()
            return "swipe_right"
        elif dx < -0.20:
            self.last_swipe_time = now
            self.wrist_x_history.clear()
            return "swipe_left"
            
        return None

    def process_frame(self, frame, timestamp_ms):
        """Run landmark inference and gesture classification on a single frame."""
        h, w, _ = frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        detection_result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        
        detected_gesture = "none"
        confidence = 0.0
        landmarks = None
        handedness = "Right"
        extra = {}
        
        if detection_result.hand_landmarks:
            raw_lm = detection_result.hand_landmarks[0]
            landmarks = self.smooth_landmarks(raw_lm)
            
            # Handedness
            if detection_result.handedness:
                handedness = detection_result.handedness[0][0].category_name
                confidence = float(detection_result.handedness[0][0].score)
                
            is_valid, reason = self.is_hand_valid(landmarks)
            if is_valid:
                detected_gesture, g_conf, extra = self.detect_gesture(landmarks, handedness)
                confidence = min(confidence, g_conf)
            else:
                detected_gesture = "ignored_boundary"
                
        # Handle Wake Gesture (Open palm held for 1.0s)
        now = time.time()
        if detected_gesture == "open_palm":
            if self.open_palm_start_time is None:
                self.open_palm_start_time = now
            elif (now - self.open_palm_start_time) >= self.wake_hold_seconds:
                self.actions.trigger_action("wake_palm")
        else:
            self.open_palm_start_time = None

        # Continuous gesture: mouse movement does not wait for 8-frame debounce
        if detected_gesture == "index_up":
            norm_x = extra.get("x", 0.5)
            norm_y = extra.get("y", 0.5)
            self.actions.trigger_action("index_up", norm_x=norm_x, norm_y=norm_y)

        # Debounce for discrete gestures (8 frames)
        if detected_gesture in ["fist", "pinch", "peace", "thumbs_up", "thumbs_down", "swipe_left", "swipe_right", "open_palm"]:
            if detected_gesture == self.candidate_gesture:
                self.candidate_count += 1
                if self.candidate_count >= self.debounce_target:
                    # Fire discrete gesture
                    self.actions.trigger_action(detected_gesture)
                    self.candidate_count = 0  # reset after firing
            else:
                self.candidate_gesture = detected_gesture
                self.candidate_count = 1
        else:
            if detected_gesture != "index_up":
                self.candidate_gesture = None
                self.candidate_count = 0

        return {
            "gesture": detected_gesture,
            "confidence": confidence,
            "landmarks": landmarks,
            "handedness": handedness,
            "debounce_progress": self.candidate_count / float(self.debounce_target),
            "extra": extra
        }

    def render_debug_hud(self, frame, detection_info):
        """Draw landmarks, HUD elements, bounding box, and telemetry overlay."""
        hud = frame.copy()
        h, w, _ = hud.shape
        
        # 1. Draw Active Mouse Box
        box = self.settings.get("mouse_active_box", {})
        bx1 = int(box.get("x_min", 0.20) * w)
        bx2 = int(box.get("x_max", 0.80) * w)
        by1 = int(box.get("y_min", 0.20) * h)
        by2 = int(box.get("y_max", 0.80) * h)
        
        # Subtle active boundary
        cv2.rectangle(hud, (bx1, by1), (bx2, by2), (255, 180, 0), 1)
        cv2.putText(hud, "MOUSE ACTIVE AREA", (bx1 + 8, by1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 180, 0), 1)

        # 2. Draw Skeleton & Landmarks
        landmarks = detection_info.get("landmarks")
        if landmarks:
            # Draw Connections
            for p1_idx, p2_idx in HAND_CONNECTIONS:
                p1 = landmarks[p1_idx]
                p2 = landmarks[p2_idx]
                pt1 = (int(p1["x"] * w), int(p1["y"] * h))
                pt2 = (int(p2["x"] * w), int(p2["y"] * h))
                cv2.line(hud, pt1, pt2, (0, 200, 255), 2)
                
            # Draw Joints
            for i, lm in enumerate(landmarks):
                cx, cy = int(lm["x"] * w), int(lm["y"] * h)
                color = (0, 255, 0) if i in [4, 8, 12, 16, 20] else (255, 255, 255)
                radius = 5 if i in [4, 8, 12, 16, 20] else 3
                cv2.circle(hud, (cx, cy), radius, color, -1)
                cv2.circle(hud, (cx, cy), radius + 1, (0, 0, 0), 1)

        # 3. Top HUD Banner
        overlay = hud.copy()
        cv2.rectangle(overlay, (0, 0), (w, 75), (20, 20, 25), -1)
        cv2.addWeighted(overlay, 0.75, hud, 0.25, 0, hud)
        
        # Telemetry Text
        gesture = detection_info.get("gesture", "none").upper()
        conf = detection_info.get("confidence", 0.0) * 100
        handedness = detection_info.get("handedness", "")
        status_label = "ACTIVE" if self.actions.is_active else "STANDBY"
        status_color = (0, 255, 128) if self.actions.is_active else (100, 180, 255)
        
        cv2.putText(hud, f"J.A.R.V.I.S. GESTURE HUD: [{status_label}]", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)
        cv2.putText(hud, f"GESTURE: {gesture} ({conf:.0f}%)", (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 240, 255), 2)
        cv2.putText(hud, f"FPS: {self.fps:.1f} | Hand: {handedness}", (w - 230, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 220, 220), 1)
        cv2.putText(hud, "Press 'd' to hide debug | 'q' to quit", (w - 275, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1)

        # Debounce Progress Bar
        debounce_prog = detection_info.get("debounce_progress", 0.0)
        if debounce_prog > 0:
            bar_w = int(120 * debounce_prog)
            cv2.rectangle(hud, (15, 62), (135, 70), (50, 50, 50), -1)
            cv2.rectangle(hud, (15, 62), (15 + bar_w, 70), (0, 255, 0), -1)

        return hud

    def run(self):
        """Main loop reading from camera thread and processing frames."""
        print("\033[94m[GESTURE DETECTOR]\033[0m Initializing camera...")
        if not self.cam.start():
            print("\033[91m[CAMERA ERROR]\033[0m Could not open camera. Check macOS Camera permissions.")
            return

        self.running = True
        print("\033[92m[GESTURE DETECTOR READY]\033[0m Zero-lag pipeline online.")
        print("  - Press 'd' to toggle the OpenCV debug HUD window")
        print("  - Hold open palm for 1 second or say 'Jarvis, start gesture control' to activate")
        print("  - Supported gestures: Open Palm, Fist, Index Up, Pinch, Peace, Thumbs Up/Down, Swipes\n")

        start_time = time.time()
        while self.running:
            frame = self.cam.read()
            if frame is None:
                time.sleep(0.005)
                continue

            # Maintain accurate timestamp for video inference
            timestamp_ms = int((time.time() - start_time) * 1000)
            detection_info = self.process_frame(frame, timestamp_ms)

            # Calculate FPS
            self.frame_count += 1
            now = time.time()
            if (now - self.fps_timer) >= 1.0:
                self.fps = self.frame_count / (now - self.fps_timer)
                self.frame_count = 0
                self.fps_timer = now

            # Debug Window handling
            if self.show_debug_window:
                debug_frame = self.render_debug_hud(frame, detection_info)
                cv2.imshow(self.window_name, debug_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('d') or key == ord('D'):
                    self.show_debug_window = False
                    cv2.destroyWindow(self.window_name)
                    print("\033[93m[DEBUG VIEW]\033[0m Debug window hidden. Press 'd' again to restore.")
                elif key == ord('q') or key == 27:
                    break
            else:
                # Still check keys if any window exists
                time.sleep(0.005)

    def toggle_debug(self):
        """Toggle debug HUD display state."""
        self.show_debug_window = not self.show_debug_window
        if not self.show_debug_window:
            try:
                cv2.destroyWindow(self.window_name)
            except Exception:
                pass
        state = "SHOWN" if self.show_debug_window else "HIDDEN"
        print(f"\033[93m[DEBUG HUD {state}]\033[0m Toggle key 'd' pressed.")

    def stop(self):
        self.running = False
        self.cam.stop()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


# Global detector instance for integration
_global_detector = None
_detector_thread = None

def get_gesture_detector():
    global _global_detector
    if _global_detector is None:
        _global_detector = GestureDetector()
    return _global_detector

def start_gesture_background(show_debug=False):
    """Start gesture detection in a separate thread so voice assistant never blocks."""
    global _detector_thread
    detector = get_gesture_detector()
    if detector.running:
        detector.actions.set_active(True, reason="Voice command")
        if show_debug:
            detector.show_debug_window = True
        return "Gesture control is already running and now active, Sir."

    detector.show_debug_window = show_debug
    _detector_thread = threading.Thread(target=detector.run, daemon=True)
    _detector_thread.start()
    detector.actions.set_active(True, reason="Voice command")
    return "Gesture control initialized and active, Sir. Camera tracking online."

def stop_gesture_background():
    """Stop/deactivate gesture control."""
    detector = get_gesture_detector()
    if detector.running:
        detector.actions.set_active(False, reason="User deactivated")
        return "Gesture control deactivated, Sir. Standing down."
    return "Gesture control is not currently active, Sir."

if __name__ == "__main__":
    detector = get_gesture_detector()
    # If run directly with python gesture_detector.py, open with debug window enabled by default
    detector.show_debug_window = True
    try:
        detector.run()
    except KeyboardInterrupt:
        detector.stop()

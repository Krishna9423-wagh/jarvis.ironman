"""
J.A.R.V.I.S. Background Gesture QThread Worker
----------------------------------------------
Executes MediaPipe HandLandmarker inference in an independent thread
and delivers frame pixmaps and telemetry to the UI at 30+ FPS.
"""

import time
import cv2
import numpy as np
from PyQt6 import QtCore, QtGui
from gesture_detector import GestureDetector, get_gesture_detector
from config import log_event

class GestureWorkerThread(QtCore.QThread):
    frame_ready = QtCore.pyqtSignal(QtGui.QPixmap)
    detection_event = QtCore.pyqtSignal(dict)
    action_triggered = QtCore.pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.detector = get_gesture_detector()
        self.running = True
        self.gesture_enabled = True
        self.last_action_desc = ""

    def run(self):
        log_event("UI:WORKER", "Starting background gesture detection thread...")
        if not self.detector.cam.start():
            log_event("UI:WORKER:WARN", "Camera could not be opened directly. Falling back to diagnostic loop.")

        start_time = time.time()
        frame_idx = 0
        fps_timer = time.time()
        fps_val = 30.0

        while self.running:
            raw_frame = self.detector.cam.read()
            if raw_frame is None:
                # Synthetic/Standby frame if camera access is pending
                time.sleep(0.02)
                raw_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(raw_frame, "STANDBY / CHECK CAMERA PERMISSION", (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 229, 255), 2)

            timestamp_ms = int((time.time() - start_time) * 1000)
            
            # Run inference if gesture control enabled
            if self.gesture_enabled:
                detection_info = self.detector.process_frame(raw_frame, timestamp_ms)
            else:
                detection_info = {
                    "gesture": "none",
                    "confidence": 0.0,
                    "landmarks": None,
                    "handedness": "",
                    "debounce_progress": 0.0
                }

            # Calculate FPS
            frame_idx += 1
            now = time.time()
            if (now - fps_timer) >= 1.0:
                fps_val = frame_idx / (now - fps_timer)
                frame_idx = 0
                fps_timer = now

            # Determine human-readable status
            gesture = detection_info.get("gesture", "none")
            progress = detection_info.get("debounce_progress", 0.0)
            landmarks = detection_info.get("landmarks")

            if not landmarks:
                status = "No hand detected"
            elif progress >= 0.99 or gesture in ["index_up", "pinch"]:
                status = "Gesture recognized"
            elif progress > 0.1:
                status = "Hold steady..."
            else:
                status = "Tracking hand"

            # Check if an action was fired by GestureDetector
            triggered = False
            action_desc = ""
            if progress >= 0.95 and gesture not in ["none", "unknown", "ignored_boundary"]:
                triggered = True
                cfg = self.detector.gestures_cfg.get(gesture, {})
                action_desc = f"{cfg.get('name', gesture)} -> {cfg.get('action', gesture)}"
                self.last_action_desc = action_desc
                self.action_triggered.emit(gesture, detection_info)

            # Convert BGR frame to QPixmap
            rgb_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_img = QtGui.QImage(rgb_frame.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(q_img)

            # Emit to UI
            self.frame_ready.emit(pixmap)
            self.detection_event.emit({
                "gesture": gesture,
                "confidence": detection_info.get("confidence", 0.0),
                "landmarks": landmarks,
                "handedness": detection_info.get("handedness", ""),
                "debounce_progress": progress,
                "fps": fps_val,
                "status": status,
                "triggered": triggered,
                "action_desc": action_desc or self.last_action_desc
            })

            # Maintain ~30 FPS cadence
            time.sleep(0.015)

    def set_gesture_enabled(self, enabled: bool):
        self.gesture_enabled = enabled
        self.detector.actions.set_active(enabled, reason="UI toggle")

    def stop(self):
        self.running = False
        self.detector.cam.stop()
        self.wait(1000)

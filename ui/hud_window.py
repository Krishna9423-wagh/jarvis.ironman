"""
J.A.R.V.I.S. Iron Man Tactical Gesture HUD Main Window
------------------------------------------------------
Features:
- 3-Column Holographic Layout (Gesture Guide | Camera Viewport | Gesture Control)
- Top HUD bracket with animated Arc Reactor Core and AI Configuration
- Bottom status bar with live telemetry chips and recent actions marquee
- Compact Mode floating always-on-top window toggle ('C')
- Global hotkeys: 'G' (Gestures), 'D' (Debug), 'Esc' (Stop all actions)
- Toast notifications for calibration hints ("Move hand closer / improve lighting")
"""

import sys
import os
from PyQt6 import QtWidgets, QtGui, QtCore

from ui.theme import (
    HUD_STYLESHEET, CYAN_ACCENT, NEON_GREEN, AMBER_WARN, RED_ALERT,
    BG_DARK, BG_CARD, BORDER_NEON, get_title_font, get_tech_font
)
from ui.arc_reactor import ArcReactorOrb
from ui.camera_feed import CameraViewport
from ui.gesture_guide import GestureGuidePanel
from ui.gesture_control_panel import GestureControlPanel
from ui.bottom_bar import BottomStatusBar
from ui.settings_drawer import SettingsDrawer
from ui.worker import GestureWorkerThread

class ToastNotification(QtWidgets.QFrame):
    """Floating holographic toast for alerts & calibration hints."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(10, 24, 42, 0.92);
                border: 1px solid #FFB300;
                border-radius: 8px;
                padding: 10px 18px;
            }
        """)
        self.hide()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.icon_lbl = QtWidgets.QLabel("💡")
        self.icon_lbl.setFont(QtGui.QFont("Apple Color Emoji", 14))
        layout.addWidget(self.icon_lbl)

        self.text_lbl = QtWidgets.QLabel("Move hand closer / improve lighting")
        self.text_lbl.setFont(get_tech_font(11, bold=True))
        self.text_lbl.setStyleSheet("color: #FFE082;")
        layout.addWidget(self.text_lbl)

        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_hint(self, message: str, duration_ms: int = 3500):
        self.text_lbl.setText(message)
        self.adjustSize()
        parent = self.parent()
        if parent:
            px = int((parent.width() - self.width()) / 2)
            py = int(parent.height() - 140)
            self.move(px, py)
        self.show()
        self.raise_()
        self.timer.start(duration_ms)


class JarvisGestureHUD(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S. // TACTICAL HAND GESTURE HUD")
        self.resize(1140, 720)
        self.setMinimumSize(880, 560)
        self.setStyleSheet(HUD_STYLESHEET)

        self.is_compact = False
        self.normal_geometry = None
        self.fail_streak = 0
        self.last_toast_time = 0

        # Background Worker Thread
        self.worker = GestureWorkerThread(self)

        # Build UI
        self._build_ui()
        self._connect_signals()

        # Start Gesture Engine
        self.worker.start()

    def _build_ui(self):
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(12)

        # 1. Top HUD Header Bracket
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setSpacing(14)

        # Animated Arc Reactor Core Orb
        self.arc_reactor = ArcReactorOrb(size=64)
        top_bar.addWidget(self.arc_reactor)

        # Title & Sub-Telemetry
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        
        main_title = QtWidgets.QLabel("J.A.R.V.I.S. TACTICAL GESTURE INTERFACE")
        main_title.setFont(get_title_font(16, bold=True))
        main_title.setStyleSheet(f"color: {CYAN_ACCENT}; letter-spacing: 2.5px;")
        
        sub_telemetry = QtWidgets.QLabel("MARK VII AUTONOMOUS AVIONICS • MEDIAPIPE NEURAL ENGINE • ZERO-LAG PIPELINE")
        sub_telemetry.setFont(get_tech_font(10))
        sub_telemetry.setStyleSheet("color: #80DEEA; letter-spacing: 1px;")

        title_box.addWidget(main_title)
        title_box.addWidget(sub_telemetry)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        # Top Action Buttons
        self.btn_compact = QtWidgets.QPushButton("❐ COMPACT MODE ('C')")
        self.btn_compact.setProperty("class", "hud-btn")
        self.btn_compact.setFont(get_tech_font(10, bold=True))
        self.btn_compact.clicked.connect(self.toggle_compact_mode)
        top_bar.addWidget(self.btn_compact)

        self.btn_settings = QtWidgets.QPushButton("⚙ SETTINGS")
        self.btn_settings.setProperty("class", "hud-btn")
        self.btn_settings.setFont(get_tech_font(10, bold=True))
        self.btn_settings.clicked.connect(self.open_settings)
        top_bar.addWidget(self.btn_settings)

        root_layout.addLayout(top_bar)

        # 2. Main 3-Column HUD Body
        self.body_layout = QtWidgets.QHBoxLayout()
        self.body_layout.setSpacing(14)

        # Left: Gesture Guide Panel
        self.guide_panel = GestureGuidePanel(self)
        self.body_layout.addWidget(self.guide_panel)

        # Center: Live Camera Viewport
        self.camera_feed = CameraViewport(self)
        self.body_layout.addWidget(self.camera_feed, 1)

        # Right: Gesture Control Telemetry Panel
        self.control_panel = GestureControlPanel(self)
        self.body_layout.addWidget(self.control_panel)

        root_layout.addLayout(self.body_layout, 1)

        # 3. Bottom Status Bar & Log Stream
        self.bottom_bar = BottomStatusBar(self)
        root_layout.addWidget(self.bottom_bar)

        # Toast notification floating overlay
        self.toast = ToastNotification(central)

    def _connect_signals(self):
        self.worker.frame_ready.connect(self._on_frame_ready)
        self.worker.detection_event.connect(self._on_detection_event)
        self.worker.action_triggered.connect(self._on_action_triggered)
        self.bottom_bar.gesture_toggled.connect(self.worker.set_gesture_enabled)

    def _on_frame_ready(self, pixmap: QtGui.QPixmap):
        self.camera_feed.current_frame = pixmap
        self.camera_feed.update()

    def _on_detection_event(self, data: dict):
        gesture = data.get("gesture", "none")
        conf = data.get("confidence", 0.0)
        landmarks = data.get("landmarks")
        progress = data.get("debounce_progress", 0.0)
        fps = data.get("fps", 30.0)
        status = data.get("status", "No hand detected")
        handedness = data.get("handedness", "")

        # Update Center Camera Viewport
        self.camera_feed.landmarks = landmarks
        self.camera_feed.gesture_name = gesture
        self.camera_feed.confidence = conf
        self.camera_feed.status_state = status

        # Update Right Control Panel
        self.control_panel.update_gesture_data(gesture, conf, progress, handedness, triggered=data.get("triggered", False))

        # Highlight Left Guide Panel Row
        self.guide_panel.set_active_gesture(gesture)

        # Update Bottom Bar Telemetry
        has_hand = bool(landmarks)
        self.bottom_bar.update_telemetry(fps, has_hand)

        # Arc Reactor Mode
        if has_hand:
            self.arc_reactor.set_mode("gesture_active")
            self.fail_streak = 0
        else:
            self.arc_reactor.set_mode("standby")
            self.fail_streak += 1
            if self.fail_streak > 120 and (QtCore.QTime.currentTime().msec() % 5000 < 50):
                self.toast.show_hint("Calibration Hint: Move hand closer and ensure good lighting.")

    def _on_action_triggered(self, gesture: str, data: dict):
        """Action execution hook."""
        self.camera_feed.trigger_action_ripple()
        self.arc_reactor.set_mode("action")
        cfg = self.worker.detector.gestures_cfg.get(gesture, {})
        action_name = cfg.get("action", gesture).upper()
        self.bottom_bar.lbl_recent_action.setText(f"Triggered: {gesture.upper()} -> {action_name}")

    def toggle_compact_mode(self):
        """Toggle between full 3-column tactical workstation and compact floating widget."""
        self.is_compact = not self.is_compact
        if self.is_compact:
            self.normal_geometry = self.geometry()
            self.guide_panel.hide()
            self.control_panel.hide()
            self.bottom_bar.hide()
            self.btn_compact.setText("❐ FULL HUD ('C')")
            self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
            self.resize(380, 290)
            self.show()
        else:
            self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, False)
            self.guide_panel.show()
            self.control_panel.show()
            self.bottom_bar.show()
            self.btn_compact.setText("❐ COMPACT MODE ('C')")
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            self.show()

    def open_settings(self):
        drawer = SettingsDrawer(parent=self)
        drawer.exec()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        if key == QtCore.Qt.Key.Key_G:
            # Toggle gestures on/off
            new_state = not self.worker.gesture_enabled
            self.worker.set_gesture_enabled(new_state)
            self.bottom_bar.set_gesture_active(new_state)
            status_text = "ENABLED" if new_state else "DISABLED"
            self.toast.show_hint(f"Gesture Control {status_text}")
        elif key == QtCore.Qt.Key.Key_D:
            # Toggle landmark debugging overlay
            self.camera_feed.show_debug = not self.camera_feed.show_debug
            debug_text = "SHOWN" if self.camera_feed.show_debug else "HIDDEN"
            self.toast.show_hint(f"Landmark Skeleton Overlay {debug_text}")
        elif key == QtCore.Qt.Key.Key_C:
            self.toggle_compact_mode()
        elif key == QtCore.Qt.Key.Key_Escape:
            # Emergency Stop
            self.worker.detector.actions.trigger_action("pause_listening")
            self.toast.show_hint("EMERGENCY STOP EXECUTED")
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

def launch_gesture_hud():
    """Application entry point."""
    app = QtWidgets.QApplication(sys.argv)
    window = JarvisGestureHUD()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_gesture_hud()

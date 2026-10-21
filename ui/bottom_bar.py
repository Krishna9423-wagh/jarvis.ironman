"""
J.A.R.V.I.S. HUD Status Bar & Action Telemetry
----------------------------------------------
Features:
- Telemetry status chips:
  1. Gesture [ONLINE / STANDBY]
  2. Voice Assistant [LISTENING / STANDBY]
  3. Camera FPS [30 FPS]
  4. Hand Tracking [LOCKED / SEARCHING]
- Real-time scrolling recent-actions log stream
- Gesture control toggle switch
"""

from PyQt6 import QtWidgets, QtGui, QtCore
from ui.theme import (
    CYAN_ACCENT, NEON_GREEN, AMBER_WARN, RED_ALERT,
    TEXT_PRIMARY, TEXT_MUTED, BG_CARD, BORDER_NEON,
    get_tech_font
)

class StatusChip(QtWidgets.QFrame):
    def __init__(self, label: str, value: str, color=CYAN_ACCENT, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(10, 22, 38, 0.75);
                border: 1px solid rgba(0, 229, 255, 0.30);
                border-radius: 6px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.dot = QtWidgets.QLabel("●")
        self.dot.setFont(get_tech_font(10))
        self.dot.setStyleSheet(f"color: {color};")
        layout.addWidget(self.dot)

        self.lbl = QtWidgets.QLabel(label)
        self.lbl.setFont(get_tech_font(10))
        self.lbl.setStyleSheet("color: #90A4AE;")
        layout.addWidget(self.lbl)

        self.val = QtWidgets.QLabel(value)
        self.val.setFont(get_tech_font(11, bold=True))
        self.val.setStyleSheet(f"color: {color};")
        layout.addWidget(self.val)

    def set_value(self, value: str, color=None):
        self.val.setText(value)
        if color:
            self.dot.setStyleSheet(f"color: {color};")
            self.val.setStyleSheet(f"color: {color};")


class BottomStatusBar(QtWidgets.QFrame):
    gesture_toggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setProperty("class", "hud-card")
        self.setStyleSheet("""
            QFrame {
                background: rgba(8, 16, 28, 0.85);
                border-top: 1px solid rgba(0, 229, 255, 0.35);
            }
        """)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 8)
        main_layout.setSpacing(14)

        # 1. Status Chips Group
        chips_layout = QtWidgets.QHBoxLayout()
        chips_layout.setSpacing(8)

        self.chip_gesture = StatusChip("GESTURE:", "ONLINE", NEON_GREEN)
        self.chip_voice = StatusChip("VOICE:", "LISTENING", CYAN_ACCENT)
        self.chip_fps = StatusChip("FPS:", "30.0", CYAN_ACCENT)
        self.chip_hand = StatusChip("HAND:", "LOCKED", NEON_GREEN)

        chips_layout.addWidget(self.chip_gesture)
        chips_layout.addWidget(self.chip_voice)
        chips_layout.addWidget(self.chip_fps)
        chips_layout.addWidget(self.chip_hand)
        main_layout.addLayout(chips_layout)

        # 2. Recent Action Telemetry Marquee
        action_box = QtWidgets.QFrame()
        action_box.setStyleSheet("background: rgba(0, 0, 0, 0.40); border: 1px solid rgba(0, 229, 255, 0.15); border-radius: 6px; padding: 4px 10px;")
        ab_layout = QtWidgets.QHBoxLayout(action_box)
        ab_layout.setContentsMargins(8, 2, 8, 2)
        ab_layout.setSpacing(6)

        tag = QtWidgets.QLabel("RECENT ACTION:")
        tag.setFont(get_tech_font(10, bold=True))
        tag.setStyleSheet("color: #00E5FF;")
        ab_layout.addWidget(tag)

        self.lbl_recent_action = QtWidgets.QLabel("System operational and standing by.")
        self.lbl_recent_action.setFont(get_tech_font(11))
        self.lbl_recent_action.setStyleSheet("color: #FFFFFF;")
        ab_layout.addWidget(self.lbl_recent_action)
        ab_layout.addStretch()

        main_layout.addWidget(action_box, 1)

        # 3. Gesture Toggle Button
        self.btn_toggle = QtWidgets.QPushButton("GESTURE: ON")
        self.btn_toggle.setProperty("class", "hud-btn hud-btn-active")
        self.btn_toggle.setFont(get_tech_font(11, bold=True))
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        main_layout.addWidget(self.btn_toggle)

    def _on_toggle_clicked(self):
        is_on = self.btn_toggle.isChecked()
        self.set_gesture_active(is_on)
        self.gesture_toggled.emit(is_on)

    def set_gesture_active(self, active: bool):
        self.btn_toggle.setChecked(active)
        if active:
            self.btn_toggle.setText("GESTURE: ON")
            self.btn_toggle.setStyleSheet(f"background: {CYAN_ACCENT}; color: #050B14; font-weight: bold; border-radius: 6px; padding: 6px 12px;")
            self.chip_gesture.set_value("ONLINE", NEON_GREEN)
        else:
            self.btn_toggle.setText("GESTURE: OFF")
            self.btn_toggle.setStyleSheet("background: rgba(255, 61, 113, 0.2); color: #FF3D71; border: 1px solid #FF3D71; font-weight: bold; border-radius: 6px; padding: 6px 12px;")
            self.chip_gesture.set_value("STANDBY", "#78909C")

    def update_telemetry(self, fps: float, hand_detected: bool, latest_action: str = ""):
        self.chip_fps.set_value(f"{fps:.1f}", CYAN_ACCENT)
        if hand_detected:
            self.chip_hand.set_value("LOCKED", NEON_GREEN)
        else:
            self.chip_hand.set_value("SEARCHING", "#78909C")

        if latest_action:
            self.lbl_recent_action.setText(latest_action)

"""
J.A.R.V.I.S. Gesture Control Telemetry Panel
-------------------------------------------
Features:
- Large glowing holographic icon of the active gesture
- Circular confidence / debounce progress ring that fills as gesture is held
- Action preview and execution trigger readout
- Handedness and confidence telemetry
"""

import math
from PyQt6 import QtWidgets, QtGui, QtCore
from ui.theme import (
    CYAN_ACCENT, NEON_GREEN, AMBER_WARN, RED_ALERT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BG_CARD, BORDER_NEON,
    get_title_font, get_tech_font, get_body_font
)

GESTURE_ICONS = {
    "open_palm": "🖐",
    "fist": "✊",
    "index_up": "☝",
    "pinch": "🤏",
    "peace": "✌",
    "thumbs_up": "👍",
    "thumbs_down": "👎",
    "swipe_left": "👈",
    "swipe_right": "👉",
    "wake_palm": "✨",
    "none": "⏳",
    "unknown": "❓"
}

GESTURE_TITLES = {
    "open_palm": "OPEN PALM",
    "fist": "FIST",
    "index_up": "INDEX UP",
    "pinch": "PINCH",
    "peace": "PEACE SIGN",
    "thumbs_up": "THUMBS UP",
    "thumbs_down": "THUMBS DOWN",
    "swipe_left": "SWIPE LEFT",
    "swipe_right": "SWIPE RIGHT",
    "wake_palm": "WAKE PALM",
    "none": "SEARCHING...",
    "unknown": "ANALYZING..."
}

GESTURE_ACTIONS = {
    "open_palm": "PAUSE / STOP LISTENING",
    "fist": "MUTE AUDIO / STOP MEDIA",
    "index_up": "MOVE MOUSE POINTER",
    "pinch": "MOUSE CLICK (LMB)",
    "peace": "SCROLL DOWN / NEXT",
    "thumbs_up": "CONFIRM / 'YES'",
    "thumbs_down": "CANCEL / 'NO'",
    "swipe_left": "PREVIOUS NAVIGATION",
    "swipe_right": "NEXT NAVIGATION",
    "wake_palm": "WAKE GESTURE CONTROL",
    "none": "HOLD STEADY TO ENGAGE",
    "unknown": "ALIGN HAND IN FRAME"
}

class CircularConfidenceRing(QtWidgets.QWidget):
    """Circular ring that fills from 0 to 360 degrees as debounce counter advances."""
    def __init__(self, size=150, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.progress = 0.0  # 0.0 to 1.0
        self.current_icon = "⏳"
        self.color = QtGui.QColor(CYAN_ACCENT)

    def set_progress(self, progress: float, icon: str, active: bool = False):
        self.progress = max(0.0, min(1.0, progress))
        self.current_icon = icon
        if active:
            self.color = QtGui.QColor(NEON_GREEN)
        elif self.progress > 0.4:
            self.color = QtGui.QColor(AMBER_WARN)
        else:
            self.color = QtGui.QColor(CYAN_ACCENT)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = min(cx, cy) - 10

        rect = QtCore.QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        # 1. Background Track Ring
        track_pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 18), 6.0)
        painter.setPen(track_pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        # 2. Glowing Active Arc
        if self.progress > 0.01:
            arc_span = int(-self.progress * 360 * 16)
            
            # Glow pass
            glow_pen = QtGui.QPen(self.color, 10.0)
            glow_color = QtGui.QColor(self.color)
            glow_color.setAlpha(60)
            glow_pen.setColor(glow_color)
            painter.setPen(glow_pen)
            painter.drawArc(rect, 90 * 16, arc_span)

            # Solid arc pass
            solid_pen = QtGui.QPen(self.color, 6.0, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(solid_pen)
            painter.drawArc(rect, 90 * 16, arc_span)

        # 3. Center Gesture Icon
        painter.setPen(QtGui.QColor("#FFFFFF"))
        icon_font = QtGui.QFont("Apple Color Emoji", 44)
        painter.setFont(icon_font)
        painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.current_icon)


class GestureControlPanel(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gesture-control-panel")
        self.setProperty("class", "hud-card")
        self.setFixedWidth(310)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header
        head_layout = QtWidgets.QHBoxLayout()
        head_layout.setSpacing(8)
        title = QtWidgets.QLabel("GESTURE CONTROL")
        title.setProperty("class", "hud-title")
        title.setFont(get_title_font(11, bold=True))
        
        self.tag_label = QtWidgets.QLabel("READY")
        self.tag_label.setStyleSheet(f"background: rgba(0, 229, 255, 0.15); color: {CYAN_ACCENT}; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px;")
        
        head_layout.addWidget(title)
        head_layout.addStretch()
        head_layout.addWidget(self.tag_label)
        layout.addLayout(head_layout)

        # Divider
        div = QtWidgets.QFrame()
        div.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        div.setStyleSheet("color: rgba(0, 229, 255, 0.2);")
        layout.addWidget(div)

        # Circular Confidence Ring Container
        ring_container = QtWidgets.QHBoxLayout()
        ring_container.addStretch()
        self.ring = CircularConfidenceRing(size=140)
        ring_container.addWidget(self.ring)
        ring_container.addStretch()
        layout.addLayout(ring_container)

        # Gesture Name Display
        self.name_label = QtWidgets.QLabel("NO GESTURE")
        self.name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(get_title_font(15, bold=True))
        self.name_label.setStyleSheet(f"color: {CYAN_ACCENT}; letter-spacing: 2px;")
        layout.addWidget(self.name_label)

        # Trigger Action Card
        action_card = QtWidgets.QFrame()
        action_card.setStyleSheet("background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(0, 229, 255, 0.15); border-radius: 8px; padding: 10px;")
        ac_layout = QtWidgets.QVBoxLayout(action_card)
        ac_layout.setContentsMargins(8, 8, 8, 8)
        ac_layout.setSpacing(4)
        
        act_sub = QtWidgets.QLabel("ASSIGNED ACTION")
        act_sub.setFont(get_tech_font(10))
        act_sub.setStyleSheet("color: #80DEEA; letter-spacing: 1px;")
        
        self.action_label = QtWidgets.QLabel("STANDBY")
        self.action_label.setFont(get_tech_font(12, bold=True))
        self.action_label.setStyleSheet("color: #FFFFFF;")
        self.action_label.setWordWrap(True)
        
        ac_layout.addWidget(act_sub)
        ac_layout.addWidget(self.action_label)
        layout.addWidget(action_card)

        # Telemetry Stats (Confidence, Hand, Latency)
        stats_layout = QtWidgets.QGridLayout()
        stats_layout.setSpacing(8)

        lbl_c = QtWidgets.QLabel("CONFIDENCE:")
        lbl_c.setFont(get_tech_font(11))
        lbl_c.setStyleSheet("color: #90A4AE;")
        self.val_conf = QtWidgets.QLabel("0%")
        self.val_conf.setFont(get_tech_font(11, bold=True))
        self.val_conf.setStyleSheet(f"color: {CYAN_ACCENT};")

        lbl_h = QtWidgets.QLabel("HAND DETECTED:")
        lbl_h.setFont(get_tech_font(11))
        lbl_h.setStyleSheet("color: #90A4AE;")
        self.val_hand = QtWidgets.QLabel("NONE")
        self.val_hand.setFont(get_tech_font(11, bold=True))
        self.val_hand.setStyleSheet("color: #FFFFFF;")

        stats_layout.addWidget(lbl_c, 0, 0)
        stats_layout.addWidget(self.val_conf, 0, 1)
        stats_layout.addWidget(lbl_h, 1, 0)
        stats_layout.addWidget(self.val_hand, 1, 1)

        layout.addLayout(stats_layout)
        layout.addStretch()

    def update_gesture_data(self, gesture_key: str, confidence: float, progress: float, handedness: str, triggered: bool = False):
        """Update telemetry view from detection event."""
        icon = GESTURE_ICONS.get(gesture_key, "❓")
        title = GESTURE_TITLES.get(gesture_key, gesture_key.upper())
        action = GESTURE_ACTIONS.get(gesture_key, "NONE")

        self.ring.set_progress(progress, icon, active=triggered)
        self.name_label.setText(title)
        self.action_label.setText(action)
        self.val_conf.setText(f"{int(confidence * 100)}%")
        self.val_hand.setText(f"{handedness.upper()} HAND" if handedness else "NONE")

        if triggered:
            self.tag_label.setText("ACTION TRIGGERED")
            self.tag_label.setStyleSheet(f"background: rgba(0, 255, 157, 0.2); color: {NEON_GREEN}; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        elif progress > 0.1:
            self.tag_label.setText("HOLDING...")
            self.tag_label.setStyleSheet(f"background: rgba(255, 179, 0, 0.2); color: {AMBER_WARN}; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        else:
            self.tag_label.setText("TRACKING")
            self.tag_label.setStyleSheet(f"background: rgba(0, 229, 255, 0.15); color: {CYAN_ACCENT}; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")

"""
J.A.R.V.I.S. Tactical Camera Viewport
------------------------------------
Features:
- Live 640x480 mirrored video feed inside a sleek rounded frame
- High-precision tactical HUD corner brackets
- Animated holographic scanning beam
- Real-time 21 hand landmarks (glowing neon joints + skeleton connections)
- Mouse active-box bounding guide
- Visual ripple flash on action execution
- Multi-state telemetry banner ('No hand detected', 'Hold steady...', 'Gesture recognized', 'Action done')
"""

import math
import time
from PyQt6 import QtWidgets, QtGui, QtCore
from ui.theme import (
    CYAN_ACCENT, NEON_GREEN, AMBER_WARN, RED_ALERT,
    BG_DARK, BG_CARD, BORDER_NEON, get_tech_font
)

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (9, 10), (10, 11), (11, 12),           # Middle
    (13, 14), (14, 15), (15, 16),          # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17)              # Palm arch
]

class CameraViewport(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        
        self.current_frame: QtGui.QPixmap = None
        self.landmarks = None
        self.gesture_name = "none"
        self.confidence = 0.0
        self.status_state = "No hand detected"
        self.show_debug = True
        
        # Scan-line animation
        self.scan_y = 0.0
        self.scan_direction = 1
        self.scan_timer = QtCore.QTimer(self)
        self.scan_timer.timeout.connect(self._step_scanline)
        self.scan_timer.start(30)
        
        # Visual action ripple animation
        self.ripple_radius = 0.0
        self.ripple_alpha = 0
        self.ripple_center = QtCore.QPointF(0, 0)
        self.ripple_timer = QtCore.QTimer(self)
        self.ripple_timer.timeout.connect(self._step_ripple)

    def trigger_action_ripple(self, center_norm=None):
        """Trigger an expanding circular shockwave on action fire."""
        w = self.width()
        h = self.height()
        if center_norm and "x" in center_norm and "y" in center_norm:
            self.ripple_center = QtCore.QPointF(center_norm["x"] * w, center_norm["y"] * h)
        else:
            self.ripple_center = QtCore.QPointF(w / 2.0, h / 2.0)
            
        self.ripple_radius = 10.0
        self.ripple_alpha = 240
        if not self.ripple_timer.isActive():
            self.ripple_timer.start(25)

    def _step_ripple(self):
        self.ripple_radius += 12.0
        self.ripple_alpha = max(0, self.ripple_alpha - 15)
        if self.ripple_alpha <= 0:
            self.ripple_timer.stop()
        self.update()

    def _step_scanline(self):
        h = self.height()
        if h > 0:
            self.scan_y += 3.5 * self.scan_direction
            if self.scan_y > h - 10:
                self.scan_y = h - 10
                self.scan_direction = -1
            elif self.scan_y < 10:
                self.scan_y = 10
                self.scan_direction = 1
        self.update()

    def update_telemetry(self, pixmap, landmarks, gesture_name, confidence, status):
        """Receive video frame and detection telemetry from worker thread."""
        self.current_frame = pixmap
        self.landmarks = landmarks
        self.gesture_name = gesture_name
        self.confidence = confidence
        self.status_state = status
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        rect = QtCore.QRectF(0, 0, w, h)

        # 1. Background Fill & Clip Path for Rounded Screen
        clip_path = QtGui.QPainterPath()
        clip_path.addRoundedRect(rect, 14, 14)
        painter.setClipPath(clip_path)

        if self.current_frame and not self.current_frame.isNull():
            scaled = self.current_frame.scaled(
                w, h,
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            # Center image
            ix = int((w - scaled.width()) / 2)
            iy = int((h - scaled.height()) / 2)
            painter.drawPixmap(ix, iy, scaled)
        else:
            # Standby dark HUD canvas
            painter.fillRect(self.rect(), QtGui.QColor("#08101C"))
            painter.setPen(QtGui.QColor(CYAN_ACCENT))
            painter.setFont(get_tech_font(14, bold=True))
            painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "[CAMERA OFFLINE / INITIALIZING]")

        # 2. Scanning Beam Hologram
        scan_rect = QtCore.QRectF(0, self.scan_y - 12, w, 24)
        scan_grad = QtGui.QLinearGradient(0, self.scan_y - 12, 0, self.scan_y + 12)
        scan_grad.setColorAt(0.0, QtGui.QColor(0, 229, 255, 0))
        scan_grad.setColorAt(0.5, QtGui.QColor(0, 229, 255, 75))
        scan_grad.setColorAt(1.0, QtGui.QColor(0, 229, 255, 0))
        painter.fillRect(scan_rect, QtGui.QBrush(scan_grad))
        
        # Bright center laser line
        painter.setPen(QtGui.QPen(QtGui.QColor(CYAN_ACCENT), 1.2))
        painter.drawLine(0, int(self.scan_y), w, int(self.scan_y))

        # 3. Mouse Active Box Guide
        bx1 = int(0.20 * w)
        bx2 = int(0.80 * w)
        by1 = int(0.20 * h)
        by2 = int(0.80 * h)
        
        active_pen = QtGui.QPen(QtGui.QColor(0, 229, 255, 100), 1.0, QtCore.Qt.PenStyle.DashLine)
        painter.setPen(active_pen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 229, 255, 8)))
        painter.drawRect(bx1, by1, bx2 - bx1, by2 - by1)
        
        painter.setFont(get_tech_font(10))
        painter.setPen(QtGui.QColor(0, 229, 255, 140))
        painter.drawText(bx1 + 8, by1 + 18, "MOUSE TRACKING ZONE")

        # 4. Hand Landmarks & Skeleton Rendering
        if self.landmarks and self.show_debug:
            # Bones
            bone_pen = QtGui.QPen(QtGui.QColor(0, 229, 255, 220), 2.0)
            painter.setPen(bone_pen)
            for p1_idx, p2_idx in HAND_CONNECTIONS:
                if p1_idx < len(self.landmarks) and p2_idx < len(self.landmarks):
                    p1 = self.landmarks[p1_idx]
                    p2 = self.landmarks[p2_idx]
                    pt1 = QtCore.QPointF(p1["x"] * w, p1["y"] * h)
                    pt2 = QtCore.QPointF(p2["x"] * w, p2["y"] * h)
                    painter.drawLine(pt1, pt2)

            # Joints
            tip_indices = [4, 8, 12, 16, 20]
            for i, lm in enumerate(self.landmarks):
                cx = lm["x"] * w
                cy = lm["y"] * h
                is_tip = i in tip_indices
                
                # Glowing halo
                halo_color = QtGui.QColor(NEON_GREEN if is_tip else CYAN_ACCENT)
                halo_color.setAlpha(120)
                painter.setBrush(QtGui.QBrush(halo_color))
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.drawEllipse(QtCore.QPointF(cx, cy), 6 if is_tip else 4, 6 if is_tip else 4)
                
                # Solid Core
                core_color = QtGui.QColor("#FFFFFF" if is_tip else CYAN_ACCENT)
                painter.setBrush(QtGui.QBrush(core_color))
                painter.drawEllipse(QtCore.QPointF(cx, cy), 3 if is_tip else 2, 3 if is_tip else 2)

        # 5. Expanding Action Ripple
        if self.ripple_alpha > 0:
            ripple_pen = QtGui.QPen(QtGui.QColor(0, 255, 157, self.ripple_alpha), 3.0)
            painter.setPen(ripple_pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.ripple_center, self.ripple_radius, self.ripple_radius)

        # Unclip for outer border overlay
        painter.setClipping(False)

        # 6. High-Tech Corner HUD Brackets
        bracket_len = 24
        pen_bracket = QtGui.QPen(QtGui.QColor(CYAN_ACCENT), 2.5)
        painter.setPen(pen_bracket)
        
        # Top-Left ┌
        painter.drawLine(4, 4, 4 + bracket_len, 4)
        painter.drawLine(4, 4, 4, 4 + bracket_len)
        # Top-Right ┐
        painter.drawLine(w - 4, 4, w - 4 - bracket_len, 4)
        painter.drawLine(w - 4, 4, w - 4, 4 + bracket_len)
        # Bottom-Left └
        painter.drawLine(4, h - 4, 4 + bracket_len, h - 4)
        painter.drawLine(4, h - 4, 4, h - 4 - bracket_len)
        # Bottom-Right ┘
        painter.drawLine(w - 4, h - 4, w - 4 - bracket_len, h - 4)
        painter.drawLine(w - 4, h - 4, w - 4, h - 4 - bracket_len)

        # 7. Bottom Detection Status Pill
        pill_w = 260
        pill_h = 32
        pill_x = int((w - pill_w) / 2)
        pill_y = int(h - pill_h - 14)
        
        state_color = QtGui.QColor("#78909C")
        if "Action done" in self.status_state:
            state_color = QtGui.QColor(NEON_GREEN)
        elif "Gesture recognized" in self.status_state:
            state_color = QtGui.QColor(CYAN_ACCENT)
        elif "Hold steady" in self.status_state:
            state_color = QtGui.QColor(AMBER_WARN)

        pill_rect = QtCore.QRectF(pill_x, pill_y, pill_w, pill_h)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(10, 20, 32, 210)))
        painter.setPen(QtGui.QPen(state_color, 1.2))
        painter.drawRoundedRect(pill_rect, 16, 16)
        
        # Status indicator dot
        painter.setBrush(QtGui.QBrush(state_color))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(pill_x + 20, pill_y + 16), 5, 5)

        # Status text
        painter.setPen(QtGui.QColor("#FFFFFF"))
        painter.setFont(get_tech_font(11, bold=True))
        painter.drawText(QtCore.QRectF(pill_x + 32, pill_y, pill_w - 40, pill_h), QtCore.Qt.AlignmentFlag.AlignVCenter, self.status_state.upper())

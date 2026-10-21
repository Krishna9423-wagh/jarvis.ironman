"""
J.A.R.V.I.S. Arc Reactor Core Orb
---------------------------------
Concentric rotating holographic rings with glowing pulse states:
- Breathing pulse on voice listening
- High-speed spin on thinking / inference
- Chromatic color shifts on gesture control activation
"""

import math
from PyQt6 import QtWidgets, QtGui, QtCore
from ui.theme import CYAN_ACCENT, NEON_GREEN, AMBER_WARN, RED_ALERT, BG_DARK

class ArcReactorOrb(QtWidgets.QWidget):
    def __init__(self, size=90, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        
        self.angle_inner = 0.0
        self.angle_outer = 0.0
        self.pulse_phase = 0.0
        
        # Mode states: "standby", "listening", "thinking", "gesture_active", "action"
        self.mode = "gesture_active"
        self.core_color = QtGui.QColor(CYAN_ACCENT)
        self.ring_color = QtGui.QColor("#00B0FF")
        
        # 40 FPS smooth rotation timer
        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(25)

    def set_mode(self, mode: str):
        """Update animation state and color scheme."""
        self.mode = mode
        if mode == "gesture_active":
            self.core_color = QtGui.QColor(CYAN_ACCENT)
            self.ring_color = QtGui.QColor(NEON_GREEN)
        elif mode == "listening":
            self.core_color = QtGui.QColor(NEON_GREEN)
            self.ring_color = QtGui.QColor(CYAN_ACCENT)
        elif mode == "thinking":
            self.core_color = QtGui.QColor(AMBER_WARN)
            self.ring_color = QtGui.QColor(CYAN_ACCENT)
        elif mode == "action":
            self.core_color = QtGui.QColor(NEON_GREEN)
            self.ring_color = QtGui.QColor("#FFFFFF")
        else:
            self.core_color = QtGui.QColor("#546E7A")
            self.ring_color = QtGui.QColor("#37474F")
        self.update()

    def _update_animation(self):
        speed_mult = 2.5 if self.mode == "thinking" else 1.0
        self.angle_inner = (self.angle_inner + 1.2 * speed_mult) % 360
        self.angle_outer = (self.angle_outer - 0.7 * speed_mult) % 360
        self.pulse_phase = (self.pulse_phase + 0.08) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = min(cx, cy) - 4

        # 1. Outer Glow Aura
        pulse_scale = 0.85 + 0.15 * math.sin(self.pulse_phase)
        aura_rad = radius * pulse_scale
        aura_grad = QtGui.QRadialGradient(cx, cy, aura_rad)
        aura_color = QtGui.QColor(self.core_color)
        aura_color.setAlpha(int(60 * pulse_scale))
        aura_grad.setColorAt(0.0, aura_color)
        aura_grad.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        painter.setBrush(QtGui.QBrush(aura_grad))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), aura_rad, aura_rad)

        # 2. Outer Segmented Ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_outer)
        
        outer_pen = QtGui.QPen(self.ring_color, 1.8)
        painter.setPen(outer_pen)
        for i in range(12):
            rad_angle = math.radians(i * 30)
            x1 = math.cos(rad_angle) * (radius - 2)
            y1 = math.sin(rad_angle) * (radius - 2)
            x2 = math.cos(rad_angle) * (radius - 6)
            y2 = math.sin(rad_angle) * (radius - 6)
            painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))
        painter.restore()

        # 3. Middle Rotating Vanes Ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle_inner)
        
        mid_pen = QtGui.QPen(QtGui.QColor(self.core_color), 2.2)
        painter.setPen(mid_pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius * 0.65, radius * 0.65)
        
        # 6 Arc vanes
        vane_color = QtGui.QColor(self.ring_color)
        vane_color.setAlpha(180)
        painter.setBrush(QtGui.QBrush(vane_color))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for i in range(6):
            deg = i * 60
            painter.save()
            painter.rotate(deg)
            path = QtGui.QPainterPath()
            path.moveTo(radius * 0.40, -3)
            path.lineTo(radius * 0.62, -2)
            path.lineTo(radius * 0.62, 2)
            path.lineTo(radius * 0.40, 3)
            path.closeSubpath()
            painter.drawPath(path)
            painter.restore()
        painter.restore()

        # 4. Core Palladium Center with Radial Gradient
        core_rad = radius * 0.32
        core_grad = QtGui.QRadialGradient(cx, cy, core_rad)
        c_white = QtGui.QColor("#FFFFFF")
        c_white.setAlpha(255)
        c_glow = QtGui.QColor(self.core_color)
        c_glow.setAlpha(220)
        c_rim = QtGui.QColor(self.core_color)
        c_rim.setAlpha(40)
        core_grad.setColorAt(0.0, c_white)
        core_grad.setColorAt(0.5, c_glow)
        core_grad.setColorAt(1.0, c_rim)
        
        painter.setBrush(QtGui.QBrush(core_grad))
        painter.setPen(QtGui.QPen(self.core_color, 1.5))
        painter.drawEllipse(QtCore.QPointF(cx, cy), core_rad, core_rad)

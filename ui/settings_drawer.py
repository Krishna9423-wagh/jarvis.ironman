"""
J.A.R.V.I.S. Settings Drawer & Calibration Panel
------------------------------------------------
Features:
- Debounce sensitivity slider (4 to 16 frames)
- Cooldown timer slider (0.5s to 3.0s)
- Landmark smoothing alpha slider (0.1 to 0.9)
- Camera index selector & mirror toggle
- Enable/disable individual gestures checkboxes
- Direct persistence to gestures.json
"""

import json
import os
from PyQt6 import QtWidgets, QtGui, QtCore
from ui.theme import (
    CYAN_ACCENT, NEON_GREEN, TEXT_PRIMARY, BG_CARD,
    BORDER_NEON, get_title_font, get_tech_font
)

class SettingsDrawer(QtWidgets.QDialog):
    settings_saved = QtCore.pyqtSignal(dict)

    def __init__(self, config_path="gestures.json", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("J.A.R.V.I.S. // CALIBRATION & SETTINGS")
        self.setFixedSize(420, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #070F1C;
                border: 2px solid #00E5FF;
                border-radius: 12px;
            }
        """)

        self.cfg = self._load_config()
        self.settings = self.cfg.get("settings", {})
        self.gestures = self.cfg.get("gestures", {})

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Title
        title = QtWidgets.QLabel("TACTICAL GESTURE SETTINGS")
        title.setFont(get_title_font(13))
        title.setStyleSheet(f"color: {CYAN_ACCENT}; letter-spacing: 2px;")
        main_layout.addWidget(title)

        div = QtWidgets.QFrame()
        div.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        div.setStyleSheet("color: rgba(0, 229, 255, 0.3);")
        main_layout.addWidget(div)

        # 1. Debounce Sensitivity Slider
        self.lbl_debounce = QtWidgets.QLabel(f"Debounce Frames: {self.settings.get('debounce_frames', 8)}")
        self.lbl_debounce.setFont(get_tech_font(11, bold=True))
        main_layout.addWidget(self.lbl_debounce)

        self.slider_debounce = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_debounce.setRange(4, 16)
        self.slider_debounce.setValue(int(self.settings.get("debounce_frames", 8)))
        self.slider_debounce.valueChanged.connect(lambda v: self.lbl_debounce.setText(f"Debounce Frames: {v}"))
        main_layout.addWidget(self.slider_debounce)

        # 2. Action Cooldown Slider
        cooldown_val = float(self.settings.get("cooldown_seconds", 1.0))
        self.lbl_cooldown = QtWidgets.QLabel(f"Cooldown: {cooldown_val:.1f}s")
        self.lbl_cooldown.setFont(get_tech_font(11, bold=True))
        main_layout.addWidget(self.lbl_cooldown)

        self.slider_cooldown = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_cooldown.setRange(5, 30)  # 0.5s to 3.0s
        self.slider_cooldown.setValue(int(cooldown_val * 10))
        self.slider_cooldown.valueChanged.connect(lambda v: self.lbl_cooldown.setText(f"Cooldown: {v / 10:.1f}s"))
        main_layout.addWidget(self.slider_cooldown)

        # 3. Landmark Smoothing Alpha Slider
        alpha_val = float(self.settings.get("landmark_smoothing_alpha", 0.5))
        self.lbl_alpha = QtWidgets.QLabel(f"Landmark Smoothing Alpha: {alpha_val:.2f}")
        self.lbl_alpha.setFont(get_tech_font(11, bold=True))
        main_layout.addWidget(self.lbl_alpha)

        self.slider_alpha = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_alpha.setRange(1, 9)
        self.slider_alpha.setValue(int(alpha_val * 10))
        self.slider_alpha.valueChanged.connect(lambda v: self.lbl_alpha.setText(f"Landmark Smoothing Alpha: {v / 10:.2f}"))
        main_layout.addWidget(self.slider_alpha)

        # 4. Camera & Mirror Options
        opts_layout = QtWidgets.QHBoxLayout()
        self.chk_mirror = QtWidgets.QCheckBox("Mirror Camera")
        self.chk_mirror.setChecked(bool(self.settings.get("mirror_camera", True)))
        self.chk_mirror.setFont(get_tech_font(11))
        
        lbl_cam = QtWidgets.QLabel("Camera Index:")
        lbl_cam.setFont(get_tech_font(11))
        self.spin_cam = QtWidgets.QSpinBox()
        self.spin_cam.setRange(0, 4)
        self.spin_cam.setValue(int(self.settings.get("camera_index", 0)))
        self.spin_cam.setStyleSheet("background: rgba(10, 22, 38, 0.8); color: #FFF; padding: 4px;")

        opts_layout.addWidget(self.chk_mirror)
        opts_layout.addStretch()
        opts_layout.addWidget(lbl_cam)
        opts_layout.addWidget(self.spin_cam)
        main_layout.addLayout(opts_layout)

        # 5. Gesture Toggles
        lbl_g = QtWidgets.QLabel("ACTIVE GESTURES:")
        lbl_g.setFont(get_tech_font(11, bold=True))
        lbl_g.setStyleSheet("color: #80DEEA;")
        main_layout.addWidget(lbl_g)

        self.gesture_checks = {}
        gest_grid = QtWidgets.QGridLayout()
        gest_grid.setSpacing(6)
        
        row = 0
        col = 0
        for k, v in self.gestures.items():
            chk = QtWidgets.QCheckBox(v.get("name", k))
            chk.setChecked(True)
            chk.setFont(get_tech_font(10))
            self.gesture_checks[k] = chk
            gest_grid.addWidget(chk, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        main_layout.addLayout(gest_grid)

        main_layout.addStretch()

        # Save Button
        btn_save = QtWidgets.QPushButton("APPLY & SAVE SETTINGS")
        btn_save.setProperty("class", "hud-btn hud-btn-active")
        btn_save.setFont(get_title_font(11))
        btn_save.setStyleSheet(f"background: {CYAN_ACCENT}; color: #050B14; font-weight: bold; padding: 10px; border-radius: 8px;")
        btn_save.clicked.connect(self._save_settings)
        main_layout.addWidget(btn_save)

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            return {"settings": {}, "gestures": {}}

    def _save_settings(self):
        self.settings["debounce_frames"] = self.slider_debounce.value()
        self.settings["cooldown_seconds"] = self.slider_cooldown.value() / 10.0
        self.settings["landmark_smoothing_alpha"] = self.slider_alpha.value() / 10.0
        self.settings["mirror_camera"] = self.chk_mirror.isChecked()
        self.settings["camera_index"] = self.spin_cam.value()

        self.cfg["settings"] = self.settings
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.cfg, f, indent=2)
            self.settings_saved.emit(self.settings)
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Save Error", f"Could not save settings: {e}")

"""
J.A.R.V.I.S. Gesture Guide Panel
--------------------------------
Features:
- High-tech interactive gesture directory
- Real-time active pose highlighting with electric cyan glow and badge
- Displays gesture icon, human label, and mapped system action
"""

from PyQt6 import QtWidgets, QtGui, QtCore
from ui.theme import (
    CYAN_ACCENT, NEON_GREEN, AMBER_WARN, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_MUTED, BG_CARD, BORDER_NEON,
    get_title_font, get_tech_font, get_body_font
)

GUIDE_ENTRIES = [
    {"key": "wake_palm", "icon": "✨", "name": "Wake Palm", "desc": "Hold palm 1s to wake"},
    {"key": "open_palm", "icon": "🖐", "name": "Open Palm", "desc": "Pause / stop listening"},
    {"key": "fist", "icon": "✊", "name": "Fist", "desc": "Mute / stop media"},
    {"key": "index_up", "icon": "☝", "name": "Index Up", "desc": "Move mouse cursor"},
    {"key": "pinch", "icon": "🤏", "name": "Pinch", "desc": "Mouse click (LMB)"},
    {"key": "peace", "icon": "✌", "name": "Peace Sign", "desc": "Scroll down / next"},
    {"key": "thumbs_up", "icon": "👍", "name": "Thumbs Up", "desc": "Confirm / 'Yes'"},
    {"key": "thumbs_down", "icon": "👎", "name": "Thumbs Down", "desc": "Cancel / 'No'"},
    {"key": "swipe_left", "icon": "👈", "name": "Swipe Left", "desc": "Previous navigation"},
    {"key": "swipe_right", "icon": "👉", "name": "Swipe Right", "desc": "Next navigation"},
]

class GestureGuideRow(QtWidgets.QFrame):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.key = entry["key"]
        self.is_active = False

        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame {
                background: rgba(10, 22, 38, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Icon
        lbl_icon = QtWidgets.QLabel(entry["icon"])
        lbl_icon.setFont(QtGui.QFont("Apple Color Emoji", 16))
        layout.addWidget(lbl_icon)

        # Name and Description
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        
        self.lbl_name = QtWidgets.QLabel(entry["name"])
        self.lbl_name.setFont(get_tech_font(12, bold=True))
        self.lbl_name.setStyleSheet("color: #E0F7FA;")
        
        self.lbl_desc = QtWidgets.QLabel(entry["desc"])
        self.lbl_desc.setFont(get_tech_font(10))
        self.lbl_desc.setStyleSheet("color: #78909C;")

        text_layout.addWidget(self.lbl_name)
        text_layout.addWidget(self.lbl_desc)
        layout.addLayout(text_layout)

        layout.addStretch()

        # Active indicator pill
        self.active_pill = QtWidgets.QLabel("ACTIVE")
        self.active_pill.setFont(get_tech_font(9, bold=True))
        self.active_pill.setStyleSheet(f"""
            background: {CYAN_ACCENT};
            color: #050B14;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        self.active_pill.setVisible(False)
        layout.addWidget(self.active_pill)

    def set_active(self, active: bool):
        if self.is_active == active:
            return
        self.is_active = active
        self.active_pill.setVisible(active)

        if active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: rgba(0, 229, 255, 0.18);
                    border: 1px solid {CYAN_ACCENT};
                    border-radius: 8px;
                }}
            """)
            self.lbl_name.setStyleSheet(f"color: {CYAN_ACCENT}; font-weight: bold;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(10, 22, 38, 0.45);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                }
            """)
            self.lbl_name.setStyleSheet("color: #E0F7FA;")


class GestureGuidePanel(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gesture-guide-panel")
        self.setProperty("class", "hud-card")
        self.setFixedWidth(280)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(10)

        # Header
        head_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("GESTURE GUIDE")
        title.setProperty("class", "hud-title")
        title.setFont(get_title_font(13))
        
        shortcut_tag = QtWidgets.QLabel("KEY 'G'")
        shortcut_tag.setFont(get_tech_font(10))
        shortcut_tag.setStyleSheet("color: #80DEEA; background: rgba(0, 229, 255, 0.10); padding: 2px 6px; border-radius: 4px;")
        
        head_layout.addWidget(title)
        head_layout.addStretch()
        head_layout.addWidget(shortcut_tag)
        layout.addLayout(head_layout)

        # Divider
        div = QtWidgets.QFrame()
        div.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        div.setStyleSheet("color: rgba(0, 229, 255, 0.2);")
        layout.addWidget(div)

        # Scrollable list of rows
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QtWidgets.QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QtWidgets.QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)

        self.rows: dict[str, GestureGuideRow] = {}
        for entry in GUIDE_ENTRIES:
            row = GestureGuideRow(entry)
            self.rows[entry["key"]] = row
            c_layout.addWidget(row)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def set_active_gesture(self, gesture_key: str):
        """Highlight current detected gesture row."""
        for key, row in self.rows.items():
            row.set_active(key == gesture_key)

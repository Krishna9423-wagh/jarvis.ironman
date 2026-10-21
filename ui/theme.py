"""
J.A.R.V.I.S. Iron Man HUD Theme & Design System
-----------------------------------------------
Contains:
- Futuristic Stark Industries color palette
- Typography configuration (Orbitron, Rajdhani, SF Pro / Inter)
- Glassmorphism stylesheets with neon borders and soft glows
- Dynamic widget styling tokens
"""

import os
from PyQt6 import QtGui, QtCore

# ---------------------------------------------------------------------------
# Core Color Palette
# ---------------------------------------------------------------------------
BG_DARK = "#050B14"               # Deep navy / void black background
BG_SURFACE = "#091322"            # Dark HUD panel base
BG_CARD = "rgba(10, 22, 38, 0.78)"  # Translucent glassmorphic card
BG_CARD_HOVER = "rgba(16, 36, 62, 0.90)"
BG_CARD_ACTIVE = "rgba(0, 229, 255, 0.15)"

CYAN_ACCENT = "#00E5FF"           # Electric Arc Reactor Cyan
CYAN_GLOW = "rgba(0, 229, 255, 0.50)"
CYAN_MUTED = "#1A5C7A"

NEON_GREEN = "#00FF9D"            # Successful trigger & action confirmation
GREEN_GLOW = "rgba(0, 255, 157, 0.45)"

AMBER_WARN = "#FFB300"            # Holding steady / debounce countdown
AMBER_GLOW = "rgba(255, 179, 0, 0.45)"

RED_ALERT = "#FF3D71"             # Mute / Cancel / Emergency stop
RED_GLOW = "rgba(255, 61, 113, 0.45)"

TEXT_PRIMARY = "#E0F7FA"          # Crisp luminous white/cyan
TEXT_SECONDARY = "#80DEEA"        # Subdued cyan
TEXT_MUTED = "#455A64"            # Telemetry dark grey

BORDER_NEON = "rgba(0, 229, 255, 0.32)"
BORDER_ACTIVE = "rgba(0, 229, 255, 0.95)"
BORDER_MUTED = "rgba(255, 255, 255, 0.08)"

# ---------------------------------------------------------------------------
# Font Initialization
# ---------------------------------------------------------------------------
_FONTS_LOADED = False

def init_theme_fonts():
    """Register custom Google Fonts (Orbitron, Rajdhani) if available."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    
    orbitron_path = os.path.join(fonts_dir, "Orbitron.ttf")
    rajdhani_path = os.path.join(fonts_dir, "Rajdhani.ttf")

    if os.path.exists(orbitron_path):
        QtGui.QFontDatabase.addApplicationFont(orbitron_path)
    if os.path.exists(rajdhani_path):
        QtGui.QFontDatabase.addApplicationFont(rajdhani_path)

    _FONTS_LOADED = True

def get_title_font(size=14, bold=True) -> QtGui.QFont:
    init_theme_fonts()
    font = QtGui.QFont("Orbitron", size)
    font.setBold(bold)
    font.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 1.5)
    return font

def get_tech_font(size=12, bold=False) -> QtGui.QFont:
    init_theme_fonts()
    font = QtGui.QFont("Rajdhani", size)
    font.setBold(bold)
    font.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 1.0)
    return font

def get_body_font(size=11, bold=False) -> QtGui.QFont:
    font = QtGui.QFont("Helvetica Neue", size)
    font.setBold(bold)
    return font

# ---------------------------------------------------------------------------
# Global QSS Glassmorphic Stylesheet
# ---------------------------------------------------------------------------
HUD_STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    color: {TEXT_PRIMARY};
    font-family: 'Rajdhani', 'Helvetica Neue', 'Arial';
}}

/* Glassmorphism Card Panels */
QFrame.hud-card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_NEON};
    border-radius: 12px;
}}

QFrame.hud-card:hover {{
    border: 1px solid {BORDER_ACTIVE};
}}

/* Header Label */
QLabel.hud-title {{
    font-family: 'Orbitron', 'Helvetica Neue', 'Arial';
    color: {CYAN_ACCENT};
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}}

QLabel.hud-subtitle {{
    font-family: 'Rajdhani', 'Helvetica Neue', 'Arial';
    color: {TEXT_SECONDARY};
    font-size: 11px;
    letter-spacing: 1px;
}}

/* Buttons */
QPushButton.hud-btn {{
    background-color: rgba(0, 229, 255, 0.12);
    border: 1px solid {CYAN_ACCENT};
    border-radius: 8px;
    color: {CYAN_ACCENT};
    font-family: 'Orbitron', sans-serif;
    font-size: 11px;
    font-weight: bold;
    padding: 8px 16px;
    letter-spacing: 1px;
}}

QPushButton.hud-btn:hover {{
    background-color: rgba(0, 229, 255, 0.28);
    border: 1px solid #80F4FF;
}}

QPushButton.hud-btn:pressed {{
    background-color: rgba(0, 229, 255, 0.40);
}}

QPushButton.hud-btn-active {{
    background-color: {CYAN_ACCENT};
    border: 1px solid #80F4FF;
    color: {BG_DARK};
    font-weight: bold;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 4px;
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {CYAN_ACCENT};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {TEXT_PRIMARY};
    border: 2px solid {CYAN_ACCENT};
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}

/* Checkboxes */
QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_NEON};
    border-radius: 4px;
    background: rgba(10, 22, 38, 0.6);
}}

QCheckBox::indicator:checked {{
    background: {CYAN_ACCENT};
    border: 1px solid {CYAN_ACCENT};
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: rgba(0, 229, 255, 0.25);
    border-radius: 3px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: {CYAN_ACCENT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

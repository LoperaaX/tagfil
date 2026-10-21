"""
theme.py — Paleta de colores y estilos globales QSS de TagFil.
Importar desde cualquier módulo: from theme import C, QSS
"""


class C:
    BG           = "#0D0C14"
    BG2          = "#131220"
    BG3          = "#1A1928"
    BG4          = "#201F30"
    BG5          = "#252438"
    BORDER       = "#2C2B42"
    BORDER2      = "#383660"
    PURPLE       = "#7C3AED"
    PURPLE2      = "#9D5EF0"
    PURPLE3      = "#B07EF5"
    PURPLE_DIM   = "#2D1F4E"
    PURPLE_DIM2  = "#3D2A65"
    PURPLE_GLOW  = "rgba(124,58,237,0.18)"
    TEXT         = "#F0EEF8"
    TEXT2        = "#A09DBF"
    TEXT3        = "#5E5C7A"
    TEXT4        = "#3D3B56"
    GREEN        = "#22C55E"
    GREEN_DIM    = "#14532D"
    AMBER        = "#F59E0B"
    AMBER_DIM    = "#78350F"
    RED          = "#EF4444"
    RED_DIM      = "#7F1D1D"
    SIDEBAR_ACT  = "#1E1B35"
    CARD_GRAD1   = "#1E1C2F"
    CARD_GRAD2   = "#181729"


QSS = f"""
* {{
    font-family: 'Segoe UI', 'SF Pro Display', 'Inter', sans-serif;
    color: {C.TEXT};
    outline: none;
}}
QMainWindow, QWidget {{
    background-color: {C.BG};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C.BORDER2};
    border-radius: 2px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C.PURPLE};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; background: none; }}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ height: 0; background: transparent; }}

QLineEdit {{
    background: {C.BG4};
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    padding: 9px 16px;
    font-size: 13px;
    color: {C.TEXT};
    selection-background-color: {C.PURPLE_DIM2};
}}
QLineEdit:focus {{
    border-color: {C.PURPLE};
    background: {C.BG5};
}}
QLineEdit::placeholder {{
    color: {C.TEXT3};
}}

QPushButton {{
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    background: transparent;
    color: {C.TEXT2};
}}
QPushButton#btn_primary {{
    background: {C.PURPLE};
    color: white;
}}
QPushButton#btn_primary:hover {{
    background: {C.PURPLE2};
}}
QPushButton#btn_primary:pressed {{
    background: {C.PURPLE};
}}
QPushButton#btn_ghost {{
    background: transparent;
    color: {C.TEXT2};
    border: 1px solid {C.BORDER};
    padding: 7px 16px;
}}
QPushButton#btn_ghost:hover {{
    background: {C.BG4};
    color: {C.TEXT};
    border-color: {C.BORDER2};
}}
QPushButton#btn_sort_active {{
    background: {C.PURPLE_DIM2};
    color: {C.PURPLE3};
    border: 1px solid {C.PURPLE_DIM2};
    padding: 7px 16px;
}}

QLabel#page_title {{
    font-size: 28px;
    font-weight: 700;
    color: {C.TEXT};
    letter-spacing: -0.8px;
    background: transparent;
}}
QLabel#section_title {{
    font-size: 11px;
    font-weight: 700;
    color: {C.TEXT3};
    letter-spacing: 1.2px;
    background: transparent;
}}
QLabel#card_label {{
    font-size: 13px;
    font-weight: 500;
    color: {C.TEXT2};
    background: transparent;
}}

QStatusBar {{
    background: {C.BG2};
    color: {C.TEXT3};
    border-top: 1px solid {C.BORDER};
    font-size: 11px;
    padding: 2px 16px;
}}
"""

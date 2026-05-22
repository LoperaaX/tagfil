"""
main_window.py — Ventana principal de TagFil

Layout:
  ┌─────────────┬──────────────────────────────┐
  │   Sidebar   │      Área de contenido        │
  │  (fijo 230) │   (QStackedWidget por página) │
  └─────────────┴──────────────────────────────┘

Páginas disponibles:
  0 → ResumenPage      — stats + archivos recientes
  1 → ArchivosPage     — grid de archivos + panel lateral de tipos
  2 → EtiquetasPage    — grid de tag cards + ranking completo
  3 → BusquedaPage     — búsqueda avanzada con filtros
  4 → ConfigPage       — configuración (placeholder)
"""

import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF, QSize, QEvent
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap, QBrush, QKeySequence, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
    QStatusBar, QSpacerItem,
)

import database as db
from config import get_logger, APP_NAME, ICON_PATH, SEARCH_DEBOUNCE_MS, SEARCH_MAX_RESULTS

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# PALETA DE COLORES — TagFil Premium
# ══════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════
# ESTILOS GLOBALES QSS
# ══════════════════════════════════════════════════════════════════════

QSS = f"""
* {{
    font-family: 'Segoe UI', 'SF Pro Display', 'Inter', sans-serif;
    color: {C.TEXT};
    outline: none;
    box-sizing: border-box;
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


# ══════════════════════════════════════════════════════════════════════
# HELPERS DE UI
# ══════════════════════════════════════════════════════════════════════

def _sep(horizontal: bool = True, parent=None) -> QFrame:
    f = QFrame(parent)
    f.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
    f.setStyleSheet(f"background: {C.BORDER}; max-height: 1px; border: none; margin: 0;")
    f.setFixedHeight(1)
    return f


def _shadow(radius: int = 20, color: str = "#00000070") -> QGraphicsDropShadowEffect:
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(radius)
    eff.setOffset(0, 2)
    eff.setColor(QColor(color))
    return eff


def _ext_icon_str(path: str) -> str:
    """Retorna un emoji según la extensión del archivo."""
    ext = Path(path).suffix.lower()
    return {
        ".pdf":  "📄", ".docx": "📝", ".doc":  "📝",
        ".xlsx": "📊", ".xls":  "📊", ".pptx": "📋",
        ".txt":  "📃", ".py":   "🐍", ".jpg":  "🖼️",
        ".png":  "🖼️", ".gif":  "🖼️", ".zip":  "🗜️",
        ".mp4":  "🎬", ".mp3":  "🎵", ".csv":  "📊",
        ".js":   "📜", ".ts":   "📜", ".html": "🌐",
        ".css":  "🎨", ".json": "📋", ".xml":  "📋",
    }.get(ext, "📄")


def _tag_icon(tag_name: str) -> str:
    """Retorna un emoji temático según el nombre de la etiqueta."""
    n = tag_name.lower()
    if any(x in n for x in ["segur", "lock", "crypt", "password"]):
        return "🔒"
    if any(x in n for x in ["finanz", "dinero", "pago", "contab"]):
        return "💰"
    if any(x in n for x in ["foto", "image", "pic"]):
        return "🖼️"
    if any(x in n for x in ["viaj", "travel", "vacation", "vacac"]):
        return "✈️"
    if any(x in n for x in ["doc", "word", "texto"]):
        return "📄"
    if any(x in n for x in ["music", "musi", "song", "audio"]):
        return "🎵"
    if any(x in n for x in ["dev", "code", "progr", "desarr"]):
        return "<>"
    if any(x in n for x in ["person", "gente", "user"]):
        return "👤"
    if any(x in n for x in ["trabajo", "work", "ofic"]):
        return "💼"
    return "🏷️"


# ══════════════════════════════════════════════════════════════════════
# WORKER DE BÚSQUEDA
# ══════════════════════════════════════════════════════════════════════

class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error         = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query      = query
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            if self._cancelled:
                return
            results = db.search(self.query, check_exists=True)[:SEARCH_MAX_RESULTS]
            if not self._cancelled:
                self.results_ready.emit(results)
        except Exception as e:
            logger.exception(f"Error en búsqueda: {e}")
            if not self._cancelled:
                self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR — Logo + navegación premium
# ══════════════════════════════════════════════════════════════════════

class SidebarButton(QPushButton):
    """Botón de navegación del sidebar con estilo TagFil."""

    def __init__(self, icon_char: str, text: str, parent=None):
        super().__init__(parent)
        self._active = False
        self._icon_char = icon_char
        self._text_str  = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self._lbl_icon = QLabel(icon_char)
        self._lbl_icon.setFixedSize(18, 18)
        self._lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_icon.setStyleSheet("background: transparent; font-size: 15px;")

        self._lbl_text = QLabel(text)
        self._lbl_text.setStyleSheet(
            f"background: transparent; font-size: 13.5px; font-weight: 500;"
        )

        layout.addWidget(self._lbl_icon)
        layout.addWidget(self._lbl_text)
        layout.addStretch()

        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._refresh()

    def _refresh(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PURPLE_DIM};
                    border: none;
                    border-radius: 10px;
                    border-left: 3px solid {C.PURPLE2};
                    padding-left: 13px;
                }}
            """)
            self._lbl_text.setStyleSheet(
                f"background: transparent; font-size: 13.5px; font-weight: 700; color: {C.TEXT};"
            )
            self._lbl_icon.setStyleSheet(
                f"background: transparent; font-size: 15px; color: {C.PURPLE3};"
            )
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background: {C.BG3};
                }}
            """)
            self._lbl_text.setStyleSheet(
                f"background: transparent; font-size: 13.5px; font-weight: 500; color: {C.TEXT2};"
            )
            self._lbl_icon.setStyleSheet(
                "background: transparent; font-size: 15px;"
            )


class Sidebar(QWidget):
    page_changed = pyqtSignal(int)

    _NAV_ITEMS = [
        ("🏠", "Resumen",              0),
        ("📁", "Todos los archivos",   1),
        ("🏷️", "Etiquetas",            2),
        ("🔍", "Buscar",               3),
    ]
    _BOTTOM_ITEMS = [
        ("🗑️", "Papelera",             None),
        ("⚙️", "Configuración",        4),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background: {C.BG2};
                border-right: 1px solid {C.BORDER};
            }}
        """)
        self._buttons: list[tuple[SidebarButton, int | None]] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 18)
        layout.setSpacing(2)

        # ── Logo ──
        logo_frame = QWidget()
        logo_frame.setFixedHeight(72)
        ll = QHBoxLayout(logo_frame)
        ll.setContentsMargins(10, 0, 0, 0)
        ll.setSpacing(10)

        # Icono "T" estilizado
        logo_icon = QLabel()
        logo_icon.setFixedSize(34, 34)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setText("T")
        logo_icon.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {C.PURPLE}, stop:1 #5B21B6);
            border-radius: 9px;
            font-size: 18px;
            font-weight: 800;
            color: white;
            letter-spacing: -1px;
        """)

        logo_text = QLabel("TagFil")
        logo_text.setStyleSheet(f"""
            font-size: 20px; font-weight: 800;
            color: {C.TEXT}; letter-spacing: -0.5px;
            background: transparent;
        """)
        ll.addWidget(logo_icon)
        ll.addWidget(logo_text)
        ll.addStretch()
        layout.addWidget(logo_frame)

        for icon, text, page_idx in self._NAV_ITEMS:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda _, i=page_idx: self._on_nav(i))
            self._buttons.append((btn, page_idx))
            layout.addWidget(btn)

        layout.addStretch()

        # ── Línea divisora ──
        layout.addWidget(_sep())
        layout.addSpacing(8)

        for icon, text, page_idx in self._BOTTOM_ITEMS:
            btn = SidebarButton(icon, text)
            if page_idx is not None:
                btn.clicked.connect(lambda _, i=page_idx: self._on_nav(i))
            self._buttons.append((btn, page_idx))
            layout.addWidget(btn)

        self._set_active(0)

    def _on_nav(self, page_idx: int) -> None:
        self._set_active(page_idx)
        self.page_changed.emit(page_idx)

    def _set_active(self, page_idx: int) -> None:
        for btn, idx in self._buttons:
            btn.set_active(idx == page_idx)

    def navigate_to(self, page_idx: int) -> None:
        self._set_active(page_idx)


# ══════════════════════════════════════════════════════════════════════
# PÁGINA 0 — RESUMEN
# ══════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════
# ICONOS SVG — sin emojis, estilo Fluent/Line plano
# ══════════════════════════════════════════════════════════════════════

# Stroke color interpolado en tiempo de render mediante reemplazo de string
_IC = "#9D5EF0"  # color base de iconos

_SVG_ICONS: dict[str, str] = {
    # Archivos totales — documento con líneas de contenido
    "files": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'"
        " stroke='_IC' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z'/>"
        "<polyline points='15 2 15 8 21 8'/>"
        "<line x1='9' y1='13' x2='15' y2='13'/>"
        "<line x1='9' y1='17' x2='13' y2='17'/>"
        "</svg>"
    ),
    # Etiquetas — tag shape Fluent con punto interior
    "tags": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'"
        " stroke='_IC' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'/>"
        "<circle cx='7' cy='7' r='1.3' fill='_IC' stroke='none'/>"
        "</svg>"
    ),
    # Espacio en disco — cilindro de almacenamiento con línea interna
    "space": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'"
        " stroke='_IC' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'>"
        "<ellipse cx='12' cy='5' rx='9' ry='3'/>"
        "<path d='M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5'/>"
        "<path d='M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3'/>"
        "<line x1='12' y1='15' x2='12' y2='18'/>"
        "</svg>"
    ),
    # Archivos recientes — reloj con marcas cardinales y agujas a las 3
    "recent": (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'"
        " stroke='_IC' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'>"
        "<circle cx='12' cy='12' r='9'/>"
        "<polyline points='12 6.5 12 12 16 14.5'/>"
        "<line x1='12' y1='2' x2='12' y2='4'/>"
        "<line x1='12' y1='20' x2='12' y2='22'/>"
        "<line x1='2' y1='12' x2='4' y2='12'/>"
        "<line x1='20' y1='12' x2='22' y2='12'/>"
        "</svg>"
    ),
}

# Icono de archivo genérico para listas (stroke muted)
_SVG_FILE_MUTED = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'"
    " stroke='#5E5C7A' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>"
    "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/>"
    "<polyline points='14 2 14 8 20 8'/>"
    "</svg>"
)


def _svg_pixmap(svg_str: str, size: int = 22, color: str = _IC) -> QPixmap:
    """Renderiza SVG string → QPixmap. Sustituye _IC por el color dado."""
    svg_str = svg_str.replace("_IC", color)
    try:
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtCore import QByteArray
        renderer = QSvgRenderer(QByteArray(svg_str.encode()))
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        return pix
    except Exception:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        return pix


# ══════════════════════════════════════════════════════════════════════
# GLOW CARD — base widget con paintEvent premium
# ══════════════════════════════════════════════════════════════════════

class GlowCard(QWidget):
    """
    Base de tarjeta con fondo degradado profundo y halo morado multicapa.
    • Reposo:  3 capas difusas + borde 80 alpha + accent top corto
    • Hover:   5 capas difusas + borde 200 alpha + accent más ancho + punto brillante
    """

    _RADIUS   = 20.0
    _BG_TOP   = QColor("#1C1A30")   # fondo más frío para que el glow resalte
    _BG_BOT   = QColor("#0F0E1C")   # casi negro-azul
    _GLOW_COL = QColor("#7C3AED")
    _ACC_COL  = QColor("#A78BFA")   # lila más claro, más visible sobre oscuro

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAutoFillBackground(False)

    def event(self, e):
        if e.type() == QEvent.Type.HoverEnter:
            self._hovered = True
            self.update()
        elif e.type() == QEvent.Type.HoverLeave:
            self._hovered = False
            self.update()
        return super().event(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = self.rect().adjusted(4, 4, -4, -4)
        rad = self._RADIUS

        # ── Fondo degradado profundo ──────────────────────────────
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, self._BG_TOP)
        grad.setColorAt(1.0, self._BG_BOT)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, rad, rad)

        # ── Glow exterior multicapa ───────────────────────────────
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self._hovered:
            layers = [(45, 1.5), (28, 3), (16, 5.5), (9, 8), (4, 12)]
        else:
            layers = [(28, 1.2), (14, 3.5), (6, 6)]
        for alpha, width in layers:
            gc = QColor(self._GLOW_COL)
            gc.setAlpha(alpha)
            p.setPen(QPen(gc, width))
            exp = int(width * 0.5)
            p.drawRoundedRect(
                r.adjusted(-exp, -exp, exp, exp),
                rad + exp, rad + exp
            )

        # ── Borde nítido ─────────────────────────────────────────
        bc = QColor(self._GLOW_COL)
        bc.setAlpha(200 if self._hovered else 80)
        p.setPen(QPen(bc, 1.0))
        p.drawRoundedRect(r, rad, rad)

        # ── Línea accent top centrada (se ensancha en hover) ──────
        acc = QColor(self._ACC_COL)
        acc.setAlpha(255 if self._hovered else 180)
        pen_acc = QPen(acc, 2.2)
        pen_acc.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_acc)
        cx = w // 2
        half = min(80, w // 3) if self._hovered else min(55, w // 4)
        p.drawLine(cx - half, r.top() + 1, cx + half, r.top() + 1)

        # ── Punto brillante en el centro del accent (hover only) ──
        if self._hovered:
            dot_c = QColor(self._ACC_COL)
            dot_c.setAlpha(255)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(dot_c))
            p.drawEllipse(cx - 3, r.top() - 2, 6, 6)

        p.end()


# ══════════════════════════════════════════════════════════════════════
# STAT CARD — tarjeta individual del dashboard
# ══════════════════════════════════════════════════════════════════════

class ResumenStatCard(GlowCard):
    """
    Tarjeta premium: icono SVG 26px en caja 54×54 con degradado interno,
    número 72px/800, subtítulo con punto de acento de color.
    """

    def __init__(self, icon_key: str, title: str, value: str, subtitle: str,
                 accent: str = "#B07EF5", parent=None):
        super().__init__(parent)
        self._accent    = accent
        self._icon_key  = icon_key
        self.setMinimumHeight(230)
        self.setMinimumWidth(260)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(icon_key, title, value, subtitle)

    @property
    def _ACC_COL(self):              # noqa: N802
        return QColor(self._accent)

    @property
    def _GLOW_COL(self):             # noqa: N802
        return QColor(self._accent)

    def _build(self, icon_key, title, value, subtitle):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 30, 32, 28)
        root.setSpacing(0)

        # ── Fila superior: caja de icono + badge título ───────────
        top = QHBoxLayout()
        top.setSpacing(0)
        top.setContentsMargins(0, 0, 0, 0)

        # Caja icono 54×54 con degradado y borde translúcido
        icon_box = QWidget()
        icon_box.setFixedSize(54, 54)
        icon_box.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2D1F52, stop:1 #1E1640);
            border-radius: 15px;
            border: 1px solid rgba(160,120,255,0.25);
        """)
        ibl = QHBoxLayout(icon_box)
        ibl.setContentsMargins(0, 0, 0, 0)
        svg_lbl = QLabel()
        svg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        svg_lbl.setStyleSheet("background: transparent; border: none;")
        pix = _svg_pixmap(
            _SVG_ICONS.get(icon_key, _SVG_ICONS["files"]),
            size=26, color=self._accent
        )
        if not pix.isNull():
            svg_lbl.setPixmap(pix)
        else:
            svg_lbl.setText("◈")
            svg_lbl.setStyleSheet(
                f"background: transparent; border: none; color: {self._accent}; font-size: 20px;"
            )
        ibl.addWidget(svg_lbl)
        top.addWidget(icon_box)
        top.addStretch()

        # Badge de etiqueta arriba-derecha
        lbl_badge = QLabel(title.upper())
        lbl_badge.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: #f8fafc;
            letter-spacing: 1.0px;
            background: transparent;
        """)
        lbl_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        top.addWidget(lbl_badge)
        root.addLayout(top)

        root.addSpacing(24)

        # ── Número principal 72px ─────────────────────────────────
        self._val_lbl = QLabel(value)
        self._val_lbl.setStyleSheet(f"""
            font-size: 72px;
            font-weight: 800;
            color: {C.TEXT};
            letter-spacing: -4px;
            background: transparent;
        """)
        root.addWidget(self._val_lbl)

        root.addSpacing(8)

        # ── Subtítulo con punto de acento ─────────────────────────
        sub_row = QHBoxLayout()
        sub_row.setSpacing(8)
        sub_row.setContentsMargins(0, 0, 0, 0)

        dot = QLabel("●")
        dot.setStyleSheet(f"font-size: 7px; color: {self._accent}; background: transparent;")
        dot.setFixedWidth(10)
        sub_row.addWidget(dot)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"""
            font-size: 12.5px;
            color: {C.TEXT3};
            background: transparent;
            letter-spacing: 0.1px;
        """)
        sub_row.addWidget(sub_lbl, 1)
        root.addLayout(sub_row)

        root.addStretch()

    def set_value(self, v: str):
        self._val_lbl.setText(v)


# ══════════════════════════════════════════════════════════════════════
# PÁGINA 0 — RESUMEN (solo 4 tarjetas 2×2, sin archivos recientes)
# ══════════════════════════════════════════════════════════════════════

class ResumenPage(QWidget):

    # (key, icon_key, title, initial_value, subtitle, accent_hex)
    _CARD_CFG = [
        ("total",  "files",  "Archivos totales",   "—", "Archivos en tu biblioteca",          "#B07EF5"),
        ("tags",   "tags",   "Etiquetas usadas",   "—", "Etiquetas activas",                  "#9D5EF0"),
        ("space",  "space",  "Espacio usado",      "—", "Almacenamiento total ocupado",        "#7C6AF0"),
        ("recent", "recent", "Archivos recientes", "—", "Registrados en los últimos 30 días",  "#6D5CE8"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, ResumenStatCard] = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        header_w = QWidget()
        header_w.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(header_w)
        hl.setContentsMargins(44, 36, 44, 0)
        hl.setSpacing(0)

        # Título con tagline apilados
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title = QLabel("Resumen")
        title.setObjectName("page_title")
        title_col.addWidget(title)
        tagline = QLabel("Vista general de tu biblioteca de archivos")
        tagline.setStyleSheet(
            f"font-size: 13px; color: {C.TEXT3}; background: transparent; letter-spacing: 0.1px;"
        )
        title_col.addWidget(tagline)
        hl.addLayout(title_col)
        hl.addStretch()

        # Fecha + botón alineados a la derecha
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        date_lbl = QLabel(datetime.now().strftime("%A, %d %b %Y"))
        date_lbl.setStyleSheet(
            f"font-size: 12px; color: {C.TEXT3}; background: transparent;"
        )
        date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(date_lbl)
        btn_trash = QPushButton("Vaciar Papelera")
        btn_trash.setObjectName("btn_ghost")
        btn_trash.setFixedHeight(34)
        right_col.addWidget(btn_trash)
        hl.addLayout(right_col)

        root.addWidget(header_w)
        root.addSpacing(20)

        # ── Separador glow más dramático ────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0    transparent,
                stop:0.12 #7C3AED,
                stop:0.88 #7C3AED,
                stop:1    transparent);
            border: none;
        """)
        sep_wrap = QWidget()
        sep_wrap.setStyleSheet("background: transparent;")
        sw = QHBoxLayout(sep_wrap)
        sw.setContentsMargins(44, 0, 44, 0)
        sw.addWidget(sep)
        root.addWidget(sep_wrap)

        root.addSpacing(6)

        # ── Grid 2×2 de tarjetas ────────────────────────────────────
        grid_wrap = QWidget()
        grid_wrap.setStyleSheet("background: transparent;")
        gw_layout = QVBoxLayout(grid_wrap)
        gw_layout.setContentsMargins(44, 28, 44, 44)
        gw_layout.setSpacing(0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(24)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, (key, icon_key, title_t, val, sub, accent) in enumerate(self._CARD_CFG):
            card = ResumenStatCard(icon_key, title_t, val, sub, accent)
            self._cards[key] = card
            grid.addWidget(card, i // 2, i % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        gw_layout.addLayout(grid, 1)
        root.addWidget(grid_wrap, 1)

    def refresh(self):
        try:
            stats = db.get_stats()
            total = stats.get("total_files", 0)
            tags  = stats.get("total_tags",  0)
            self._cards["total"].set_value(f"{total:,}".replace(",", "."))
            self._cards["tags"].set_value(f"{tags:,}".replace(",", "."))
            self._cards["space"].set_value("—")
            self._cards["recent"].set_value(str(total))
        except Exception as e:
            logger.exception(f"Error actualizando resumen: {e}")


# ══════════════════════════════════════════════════════════════════════
# PÁGINA 1 — TODOS LOS ARCHIVOS
# ══════════════════════════════════════════════════════════════════════

class FileCard(QWidget):
    edit_requested = pyqtSignal(dict)

    def __init__(self, record: dict, parent=None):
        super().__init__(parent)
        self._record = record
        self.setObjectName("file_card")
        self.setStyleSheet(f"""
            QWidget#file_card {{
                background: {C.BG3};
                border: 1px solid {C.BORDER};
                border-radius: 14px;
            }}
            QWidget#file_card:hover {{
                border-color: {C.BORDER2};
                background: {C.BG4};
            }}
        """)
        self.setFixedHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(record)

    def _build(self, r: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(6)

        # Top: ícono + nombre + ext
        top = QHBoxLayout()
        top.setSpacing(10)

        icon_lbl = QLabel(_ext_icon_str(r["path"]))
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"background: {C.PURPLE_DIM}; border-radius: 10px; font-size: 16px;")
        top.addWidget(icon_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name = r["name"]
        name_lbl = QLabel(name if len(name) <= 24 else name[:22] + "…")
        name_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        name_col.addWidget(name_lbl)

        ext = Path(r["path"]).suffix.upper().lstrip(".") or "FILE"
        ext_lbl = QLabel(f"{ext}")
        ext_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {C.TEXT3}; background: transparent;"
        )
        name_col.addWidget(ext_lbl)
        top.addLayout(name_col, 1)

        exists = r.get("file_exists")
        if exists is not None:
            st = QLabel("✔" if exists else "✘")
            st.setStyleSheet(
                f"font-size: 13px; color: {C.GREEN if exists else C.RED}; background: transparent;"
            )
            top.addWidget(st)
        layout.addLayout(top)

        # Descripción
        desc = r.get("description", "").strip()
        dt = (desc[:58] + "…") if len(desc) > 58 else (desc or "Sin descripción")
        dl = QLabel(dt)
        dl.setStyleSheet(
            f"font-size: 12px; color: {C.TEXT2}; background: transparent;"
        )
        dl.setWordWrap(True)
        layout.addWidget(dl)
        layout.addStretch()

        # Tags + botón editar
        tr = QHBoxLayout()
        tr.setSpacing(5)
        for tag in r.get("tags", [])[:3]:
            chip = QLabel(f"#{tag}")
            chip.setStyleSheet(f"""
                background: {C.PURPLE_DIM}; color: {C.PURPLE3};
                border-radius: 5px; padding: 2px 8px;
                font-size: 10px; font-weight: 600;
            """)
            tr.addWidget(chip)
        tr.addStretch()
        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(26, 26)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.BG5};
                border: 1px solid {C.BORDER};
                border-radius: 7px;
                font-size: 11px;
                color: {C.TEXT3};
            }}
            QPushButton:hover {{
                background: {C.PURPLE_DIM2};
                color: {C.PURPLE3};
                border-color: {C.PURPLE_DIM2};
            }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._record))
        tr.addWidget(edit_btn)
        layout.addLayout(tr)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.edit_requested.emit(self._record)


class ExtTypeRow(QWidget):
    """Fila de tipo de archivo en el panel lateral de ArchivosPage."""

    def __init__(self, ext: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(0)
        lbl = QLabel(ext.upper())
        lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {C.TEXT2}; background: transparent;")
        top.addWidget(lbl)
        top.addStretch()
        cnt = QLabel(str(count))
        cnt.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        top.addWidget(cnt)
        layout.addLayout(top)

        # Barra de progreso
        bar_bg = QFrame()
        bar_bg.setFixedHeight(3)
        bar_bg.setStyleSheet(f"background: {C.BG4}; border-radius: 2px; border: none;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setFixedHeight(3)
        bar_inner.setStyleSheet(f"background: {C.PURPLE}; border-radius: 2px;")
        pct = max(4, int(count / max_count * 100)) if max_count else 4
        bar_inner.setFixedWidth(int(140 * pct / 100))
        layout.addWidget(bar_bg)


class ArchivosPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_files: list[dict] = []
        self._worker: SearchWorker | None = None
        self._search_id  = 0
        self._active_ext: str | None = None
        self._filter_widgets: dict[str, QPushButton] = {}
        self._build()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel principal ──
        main_panel = QWidget()
        main_panel.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(main_panel)
        ml.setContentsMargins(32, 28, 24, 24)
        ml.setSpacing(0)

        # Header
        header = QHBoxLayout()
        title = QLabel("Todos los archivos")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        # Barra de búsqueda en header
        sf = QFrame()
        sf.setStyleSheet(f"""
            QFrame {{
                background: {C.BG3};
                border: 1px solid {C.BORDER};
                border-radius: 10px;
            }}
        """)
        sf.setFixedWidth(280)
        sf.setFixedHeight(38)
        sfl = QHBoxLayout(sf)
        sfl.setContentsMargins(12, 0, 12, 0)
        sfl.setSpacing(8)
        si = QLabel("🔍")
        si.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        sfl.addWidget(si)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar archivos y etiquetas...")
        self._search_input.setStyleSheet(f"""
            background: transparent; border: none;
            font-size: 13px; color: {C.TEXT}; padding: 0;
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        sfl.addWidget(self._search_input, 1)
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(18, 18)
        self._clear_btn.setStyleSheet(
            f"background: transparent; border: none; color: {C.TEXT3}; font-size: 11px;"
        )
        self._clear_btn.clicked.connect(lambda: self._search_input.clear())
        self._clear_btn.setVisible(False)
        sfl.addWidget(self._clear_btn)
        header.addWidget(sf)
        header.addSpacing(10)

        # Botones sort
        for text, obj_name in [("Más usados", "btn_ghost"), ("A-Z", "btn_ghost")]:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(38)
            header.addWidget(btn)

        ml.addLayout(header)
        ml.addSpacing(18)

        # ── Filtros de extensión ──
        self._filter_bar = QHBoxLayout()
        self._filter_bar.setSpacing(8)
        self._filter_bar.setContentsMargins(0, 0, 0, 0)
        ml.addLayout(self._filter_bar)
        ml.addSpacing(16)

        # ── Grid de archivos ──
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent; margin-bottom: 6px;"
        )
        ml.addWidget(self._count_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(14)
        scroll.setWidget(self._grid_container)
        ml.addWidget(scroll, 1)

        root.addWidget(main_panel, 1)

        # ── Panel lateral derecho ──
        right_panel = QFrame()
        right_panel.setFixedWidth(190)
        right_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.BG2};
                border-left: 1px solid {C.BORDER};
            }}
        """)
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(16, 28, 16, 24)
        rl.setSpacing(12)

        self._type_title = QLabel("TIPOS DE ARCHIVOS MÁS USADOS")
        self._type_title.setObjectName("section_title")
        self._type_title.setWordWrap(True)
        rl.addWidget(self._type_title)

        self._types_layout = QVBoxLayout()
        self._types_layout.setSpacing(6)
        rl.addLayout(self._types_layout)
        rl.addStretch()

        root.addWidget(right_panel)

    def refresh(self):
        self._run_search()

    def _run_search(self):
        query = self._search_input.text().strip()
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.quit()
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None
        self._search_id += 1
        current_id = self._search_id
        self._worker = SearchWorker(query)
        self._worker.results_ready.connect(
            lambda r, sid=current_id: self._on_results(r, sid)
        )
        self._worker.start()

    def _on_results(self, results: list, search_id: int):
        if search_id != self._search_id:
            return
        self._all_files = results
        self._build_ext_filters(results)
        self._render_grid(self._apply_ext_filter(results))
        self._render_types_panel(results)

    def _apply_ext_filter(self, files):
        if not self._active_ext:
            return files
        return [f for f in files if Path(f["path"]).suffix.lower() == self._active_ext]

    def _build_ext_filters(self, files):
        exts = Counter(Path(f["path"]).suffix.lower() for f in files if Path(f["path"]).suffix)
        top = [e for e, _ in exts.most_common(7)]
        for i in reversed(range(self._filter_bar.count())):
            item = self._filter_bar.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._filter_widgets.clear()
        all_labels = [("Todos", None)] + [(e.lstrip(".").upper(), e) for e in top]
        for label, ext in all_labels:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, e=ext: self._set_ext_filter(e))
            key = "__all__" if ext is None else ext
            self._filter_widgets[key] = btn
            self._filter_bar.addWidget(btn)
        self._filter_bar.addStretch()
        self._refresh_filter_styles()

    def _set_ext_filter(self, ext):
        self._active_ext = ext
        self._refresh_filter_styles()
        self._render_grid(self._apply_ext_filter(self._all_files))

    def _refresh_filter_styles(self):
        for key, btn in self._filter_widgets.items():
            is_active = (key == "__all__" and self._active_ext is None) or (key == self._active_ext)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.PURPLE3};
                        border: 1.5px solid {C.PURPLE};
                        border-radius: 20px;
                        padding: 0 16px;
                        font-size: 12px;
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.TEXT2};
                        border: 1px solid {C.BORDER};
                        border-radius: 20px;
                        padding: 0 16px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        border-color: {C.BORDER2};
                        color: {C.TEXT};
                    }}
                """)

    def _render_grid(self, files):
        for i in reversed(range(self._grid.count())):
            item = self._grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        total = len(files)
        q = self._search_input.text().strip()
        label = f"{total} archivo{'s' if total != 1 else ''}"
        if q:
            label += f'  —  "{q}"'
        self._count_lbl.setText(label)

        if not files:
            empty = QLabel("No se encontraron archivos.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {C.TEXT3}; font-size: 14px; background: transparent; padding: 40px;"
            )
            self._grid.addWidget(empty, 0, 0, 1, 3)
            return

        COLS = 3
        for i, record in enumerate(files):
            card = FileCard(record)
            card.edit_requested.connect(self._on_edit)
            self._grid.addWidget(card, i // COLS, i % COLS)

    def _render_types_panel(self, files):
        for i in reversed(range(self._types_layout.count())):
            item = self._types_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        exts = Counter(Path(f["path"]).suffix.lower() for f in files if Path(f["path"]).suffix)
        top = exts.most_common(8)
        max_count = top[0][1] if top else 1
        for ext, count in top:
            row = ExtTypeRow(ext.lstrip("."), count, max_count)
            self._types_layout.addWidget(row)

    def _on_search_changed(self, text):
        self._clear_btn.setVisible(bool(text))
        self._debounce.start(SEARCH_DEBOUNCE_MS)

    def _on_edit(self, record):
        try:
            from dialogs import MetadataDialog
            dlg = MetadataDialog(record["path"], parent=self)
            dlg.exec()
            self._run_search()
        except Exception as e:
            logger.exception(f"Error abriendo diálogo: {e}")


# ══════════════════════════════════════════════════════════════════════
# PÁGINA 2 — ETIQUETAS (grid de tarjetas + ranking)
# ══════════════════════════════════════════════════════════════════════

class TagCard(QWidget):
    """Tarjeta grande de etiqueta con barra de progreso inferior."""

    clicked = pyqtSignal(str)

    def __init__(self, name: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self._name = name
        self.setObjectName("tag_card")
        self.setStyleSheet(f"""
            QWidget#tag_card {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {C.BG3}, stop:1 {C.BG4});
                border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
            QWidget#tag_card:hover {{
                border-color: {C.BORDER2};
            }}
        """)
        self.setFixedHeight(165)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(name, count, max_count)

    def _build(self, name, count, max_count):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 0)
        layout.setSpacing(6)

        # Ícono
        icon_text = _tag_icon(name)
        icon_box = QLabel(icon_text)
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(f"""
            background: {C.PURPLE_DIM};
            border-radius: 11px;
            font-size: 17px;
        """)
        layout.addWidget(icon_box)

        # Nombre
        nm = QLabel(name)
        nm.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {C.TEXT}; background: transparent; letter-spacing: -0.5px;"
        )
        layout.addWidget(nm)

        # Conteo
        cnt = QLabel(f"{count} archivos")
        cnt.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        layout.addWidget(cnt)

        layout.addStretch()

        # Barra progreso inferior
        pct = max(3, int(count / max_count * 100)) if max_count else 3
        bar_bg = QWidget()
        bar_bg.setFixedHeight(18)
        bar_bg.setStyleSheet("background: transparent;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setStyleSheet(f"background: {C.PURPLE}; border-radius: 2px;")
        bar_inner.setFixedHeight(3)
        bar_inner.setGeometry(0, 10, int(self.width() * pct / 100) or 20, 3)
        self._bar_inner = bar_inner
        self._pct = pct
        layout.addWidget(bar_bg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_bar_inner"):
            w = int((self.width() - 40) * self._pct / 100)
            self._bar_inner.setFixedWidth(max(6, w))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._name)


class RankingRow(QWidget):
    """Fila del panel 'Ranking Completo'."""

    def __init__(self, name: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border-bottom: 1px solid {C.BORDER};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 4)
        layout.setSpacing(4)

        top = QHBoxLayout()
        nm = QLabel(name)
        nm.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {C.TEXT2}; background: transparent;")
        top.addWidget(nm)
        top.addStretch()
        cnt = QLabel(f"{count} archivos")
        cnt.setStyleSheet(f"font-size: 11px; color: {C.TEXT3}; background: transparent;")
        top.addWidget(cnt)
        layout.addLayout(top)

        bar_bg = QFrame()
        bar_bg.setFixedHeight(3)
        bar_bg.setStyleSheet(f"background: {C.BG4}; border-radius: 2px; border: none;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setFixedHeight(3)
        bar_inner.setStyleSheet(f"background: {C.PURPLE}; border-radius: 2px;")
        pct = max(4, int(count / max_count * 100)) if max_count else 4
        bar_inner.setFixedWidth(int(155 * pct / 100))
        layout.addWidget(bar_bg)


class EtiquetasPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags_data: list[dict] = []
        self._sort_mode = "count"
        self._search_query = ""
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel principal ──
        main_panel = QWidget()
        main_panel.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(main_panel)
        ml.setContentsMargins(32, 28, 24, 24)
        ml.setSpacing(0)

        # Header
        header = QHBoxLayout()
        title = QLabel("Etiquetas")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        # Búsqueda
        sf = QFrame()
        sf.setStyleSheet(f"""
            QFrame {{ background: {C.BG3}; border: 1px solid {C.BORDER}; border-radius: 10px; }}
        """)
        sf.setFixedWidth(240)
        sf.setFixedHeight(38)
        sfl = QHBoxLayout(sf)
        sfl.setContentsMargins(12, 0, 12, 0)
        sfl.setSpacing(8)
        si = QLabel("🔍")
        si.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        sfl.addWidget(si)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar etiquetas...")
        self._search_input.setStyleSheet(
            f"background: transparent; border: none; font-size: 13px; color: {C.TEXT}; padding: 0;"
        )
        self._search_input.textChanged.connect(self._on_search)
        sfl.addWidget(self._search_input, 1)
        header.addWidget(sf)
        header.addSpacing(10)

        # Botones sort
        self._btn_mas_usados = QPushButton("⭐  Más usados")
        self._btn_mas_usados.setObjectName("btn_sort_active")
        self._btn_mas_usados.setFixedHeight(38)
        self._btn_mas_usados.clicked.connect(lambda: self._set_sort("count"))
        header.addWidget(self._btn_mas_usados)

        self._btn_az = QPushButton("⇅  A-Z")
        self._btn_az.setObjectName("btn_ghost")
        self._btn_az.setFixedHeight(38)
        self._btn_az.clicked.connect(lambda: self._set_sort("alpha"))
        header.addWidget(self._btn_az)

        ml.addLayout(header)
        ml.addSpacing(6)

        lbl_mis = QLabel("Mis Etiquetas")
        lbl_mis.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {C.TEXT2}; background: transparent; padding: 12px 0 8px 0;"
        )
        ml.addWidget(lbl_mis)

        # Grid de tarjetas de etiquetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(14)
        scroll.setWidget(self._grid_container)
        ml.addWidget(scroll, 1)

        root.addWidget(main_panel, 1)

        # ── Panel ranking derecho ──
        right_panel = QFrame()
        right_panel.setFixedWidth(200)
        right_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.BG2};
                border-left: 1px solid {C.BORDER};
            }}
        """)
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(16, 28, 16, 24)
        rl.setSpacing(0)

        rank_title = QLabel("RANKING COMPLETO")
        rank_title.setObjectName("section_title")
        rl.addWidget(rank_title)
        rl.addSpacing(14)

        scroll_r = QScrollArea()
        scroll_r.setWidgetResizable(True)
        scroll_r.setFrameShape(QFrame.Shape.NoFrame)
        scroll_r.setStyleSheet("background: transparent;")
        self._rank_container = QWidget()
        self._rank_container.setStyleSheet("background: transparent;")
        self._rank_layout = QVBoxLayout(self._rank_container)
        self._rank_layout.setContentsMargins(0, 0, 0, 0)
        self._rank_layout.setSpacing(0)
        self._rank_layout.addStretch()
        scroll_r.setWidget(self._rank_container)
        rl.addWidget(scroll_r, 1)

        root.addWidget(right_panel)

    def refresh(self):
        try:
            raw_tags = db.get_all_tags()
            self._tags_data = [
                {"name": tag, "count": len(db.search(tag))}
                for tag in raw_tags
            ]
            self._apply_sort()
            self._render()
        except Exception as e:
            logger.exception(f"Error cargando etiquetas: {e}")

    def _apply_sort(self):
        if self._sort_mode == "count":
            self._tags_data.sort(key=lambda t: t["count"], reverse=True)
        else:
            self._tags_data.sort(key=lambda t: t["name"].lower())

    def _filtered_tags(self):
        q = self._search_query.strip().lower()
        return [t for t in self._tags_data if q in t["name"].lower()] if q else self._tags_data

    def _render(self):
        filtered = self._filtered_tags()
        max_count = max((t["count"] for t in filtered), default=1)

        # Render grid
        for i in reversed(range(self._grid.count())):
            item = self._grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if not filtered:
            empty = QLabel("No se encontraron etiquetas.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {C.TEXT3}; font-size: 14px; background: transparent; padding: 40px;"
            )
            self._grid.addWidget(empty, 0, 0, 1, 3)
        else:
            COLS = 3
            for i, tag in enumerate(filtered):
                card = TagCard(tag["name"], tag["count"], max_count)
                self._grid.addWidget(card, i // COLS, i % COLS)
            remainder = len(filtered) % COLS
            if remainder:
                for j in range(COLS - remainder):
                    filler = QWidget()
                    filler.setStyleSheet("background: transparent;")
                    self._grid.addWidget(filler, len(filtered) // COLS, remainder + j)

        # Render ranking
        for i in reversed(range(self._rank_layout.count())):
            item = self._rank_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for tag in filtered:
            row = RankingRow(tag["name"], tag["count"], max_count)
            self._rank_layout.insertWidget(self._rank_layout.count() - 1, row)
        if not filtered:
            self._rank_layout.insertWidget(0, QLabel(""))

    def _on_search(self, text):
        self._search_query = text
        self._render()

    def _set_sort(self, mode: str):
        self._sort_mode = mode
        self._btn_mas_usados.setObjectName(
            "btn_sort_active" if mode == "count" else "btn_ghost"
        )
        self._btn_az.setObjectName(
            "btn_sort_active" if mode == "alpha" else "btn_ghost"
        )
        # Re-apply stylesheet to trigger object name change
        self._btn_mas_usados.setStyle(self._btn_mas_usados.style())
        self._btn_az.setStyle(self._btn_az.style())
        self._apply_sort()
        self._render()


# ══════════════════════════════════════════════════════════════════════
# PÁGINA 3 — BÚSQUEDA AVANZADA
# ══════════════════════════════════════════════════════════════════════

class BusquedaPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_files: list[dict] = []
        self._worker: SearchWorker | None = None
        self._search_id = 0
        self._active_ext: str | None = None
        self._filter_widgets: dict[str, QPushButton] = {}
        self._build()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)

    def _build(self):
        # ── Header ──
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(header_widget)
        hl.setContentsMargins(32, 28, 32, 16)
        hl.setSpacing(12)

        title = QLabel("Avanzados de búsqueda")
        title.setObjectName("page_title")
        hl.addWidget(title)
        hl.addStretch()

        sf = QFrame()
        sf.setStyleSheet(f"""
            QFrame {{ background: {C.BG3}; border: 1px solid {C.BORDER}; border-radius: 10px; }}
        """)
        sf.setFixedWidth(260)
        sf.setFixedHeight(40)
        sfl = QHBoxLayout(sf)
        sfl.setContentsMargins(12, 0, 12, 0)
        sfl.setSpacing(8)
        si = QLabel("🔍")
        si.setStyleSheet(f"font-size: 13px; color: {C.PURPLE3}; background: transparent;")
        sfl.addWidget(si)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar...")
        self._search_input.setStyleSheet(
            f"background: transparent; border: none; font-size: 13px; color: {C.TEXT}; padding: 0;"
        )
        self._search_input.textChanged.connect(self._on_search_changed)
        sfl.addWidget(self._search_input, 1)
        hl.addWidget(sf)

        self._btn_mas = QPushButton("Más usados")
        self._btn_mas.setObjectName("btn_ghost")
        self._btn_mas.setFixedHeight(40)
        hl.addWidget(self._btn_mas)

        self._btn_az = QPushButton("A-Z")
        self._btn_az.setObjectName("btn_ghost")
        self._btn_az.setFixedHeight(40)
        hl.addWidget(self._btn_az)

        root_layout.addWidget(header_widget)

        # ── Filtros de extensión ──
        filter_widget = QWidget()
        filter_widget.setStyleSheet("background: transparent;")
        self._filter_bar = QHBoxLayout(filter_widget)
        self._filter_bar.setContentsMargins(32, 0, 32, 12)
        self._filter_bar.setSpacing(8)
        root_layout.addWidget(filter_widget)

        # ── Cuerpo: panel izq + resultados ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Panel izquierdo de filtros avanzados
        left_panel = QFrame()
        left_panel.setFixedWidth(220)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background: {C.BG2};
                border-right: 1px solid {C.BORDER};
            }}
        """)
        ll = QVBoxLayout(left_panel)
        ll.setContentsMargins(18, 20, 18, 20)
        ll.setSpacing(16)

        ft = QLabel("FILTROS AVANZADOS")
        ft.setObjectName("section_title")
        ll.addWidget(ft)

        # Fecha
        date_lbl = QLabel("FECHA")
        date_lbl.setObjectName("section_title")
        ll.addWidget(date_lbl)

        for placeholder in ["dd/mm/aaaa", "dd/mm/aaaa"]:
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(34)
            ll.addWidget(inp)

        # Tamaño
        size_lbl = QLabel("TAMAÑO")
        size_lbl.setObjectName("section_title")
        ll.addWidget(size_lbl)

        self._tag_filters_layout = QVBoxLayout()
        self._tag_filters_layout.setSpacing(6)
        ll.addLayout(self._tag_filters_layout)

        # Etiquetas adicionales
        add_tags_lbl = QLabel("ETIQUETAS ADICIONALES")
        add_tags_lbl.setObjectName("section_title")
        ll.addWidget(add_tags_lbl)

        self._tag_scroll = QScrollArea()
        self._tag_scroll.setWidgetResizable(True)
        self._tag_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._tag_scroll.setFixedHeight(120)
        self._tag_scroll.setStyleSheet("background: transparent;")
        self._tags_container = QWidget()
        self._tags_container.setStyleSheet("background: transparent;")
        self._tags_vl = QVBoxLayout(self._tags_container)
        self._tags_vl.setContentsMargins(0, 0, 0, 0)
        self._tags_vl.setSpacing(4)
        self._tags_vl.addStretch()
        self._tag_scroll.setWidget(self._tags_container)
        ll.addWidget(self._tag_scroll)
        ll.addStretch()

        body.addWidget(left_panel)

        # Panel de resultados
        results_panel = QWidget()
        results_panel.setStyleSheet("background: transparent;")
        rl = QVBoxLayout(results_panel)
        rl.setContentsMargins(24, 16, 24, 24)
        rl.setSpacing(10)

        self._results_title = QLabel("RESULTADOS DE BÚSQUEDA")
        self._results_title.setObjectName("section_title")
        rl.addWidget(self._results_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._res_container = QWidget()
        self._res_container.setStyleSheet("background: transparent;")
        self._res_grid = QGridLayout(self._res_container)
        self._res_grid.setContentsMargins(0, 0, 0, 0)
        self._res_grid.setSpacing(12)
        scroll.setWidget(self._res_container)
        rl.addWidget(scroll, 1)

        body.addWidget(results_panel, 1)
        root_layout.addLayout(body, 1)

    def refresh(self):
        self._run_search()

    def _run_search(self):
        query = self._search_input.text().strip()
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.quit()
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None
        self._search_id += 1
        current_id = self._search_id
        self._worker = SearchWorker(query)
        self._worker.results_ready.connect(
            lambda r, sid=current_id: self._on_results(r, sid)
        )
        self._worker.start()

    def _on_results(self, results, search_id):
        if search_id != self._search_id:
            return
        self._all_files = results
        self._build_ext_filters(results)
        self._render_results(self._apply_ext_filter(results))
        self._render_tag_filters(results)

        q = self._search_input.text().strip()
        q_part = f' - "{q}"' if q else ""
        label = f"RESULTADOS DE BÚSQUEDA{q_part}"
        self._results_title.setText(label)

    def _apply_ext_filter(self, files):
        if not self._active_ext:
            return files
        return [f for f in files if Path(f["path"]).suffix.lower() == self._active_ext]

    def _build_ext_filters(self, files):
        exts = Counter(Path(f["path"]).suffix.lower() for f in files if Path(f["path"]).suffix)
        top = [e for e, _ in exts.most_common(7)]
        for i in reversed(range(self._filter_bar.count())):
            item = self._filter_bar.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._filter_widgets.clear()
        all_labels = [("Todos", None)] + [(e.lstrip(".").upper(), e) for e in top]
        for label, ext in all_labels:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, e=ext: self._set_ext_filter(e))
            key = "__all__" if ext is None else ext
            self._filter_widgets[key] = btn
            self._filter_bar.addWidget(btn)
        self._filter_bar.addStretch()
        self._refresh_filter_styles()

    def _set_ext_filter(self, ext):
        self._active_ext = ext
        self._refresh_filter_styles()
        self._render_results(self._apply_ext_filter(self._all_files))

    def _refresh_filter_styles(self):
        for key, btn in self._filter_widgets.items():
            is_active = (key == "__all__" and self._active_ext is None) or (key == self._active_ext)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.PURPLE3};
                        border: 1.5px solid {C.PURPLE};
                        border-radius: 20px;
                        padding: 0 16px;
                        font-size: 12px;
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.TEXT2};
                        border: 1px solid {C.BORDER};
                        border-radius: 20px;
                        padding: 0 16px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{ border-color: {C.BORDER2}; color: {C.TEXT}; }}
                """)

    def _render_results(self, files):
        for i in reversed(range(self._res_grid.count())):
            item = self._res_grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if not files:
            empty = QLabel("No se encontraron archivos.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {C.TEXT3}; font-size: 14px; background: transparent; padding: 40px;"
            )
            self._res_grid.addWidget(empty, 0, 0, 1, 3)
            return

        COLS = 3
        for i, record in enumerate(files):
            card = self._make_result_card(record)
            self._res_grid.addWidget(card, i // COLS, i % COLS)

    def _make_result_card(self, r: dict) -> QWidget:
        card = QWidget()
        card.setObjectName("res_card")
        card.setStyleSheet(f"""
            QWidget#res_card {{
                background: {C.BG3};
                border: 1px solid {C.BORDER};
                border-radius: 14px;
            }}
            QWidget#res_card:hover {{
                border-color: {C.BORDER2};
                background: {C.BG4};
            }}
        """)
        card.setFixedHeight(130)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(10)
        icon_lbl = QLabel(_ext_icon_str(r["path"]))
        icon_lbl.setFixedSize(34, 34)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background: {C.PURPLE_DIM}; border-radius: 9px; font-size: 15px;"
        )
        top.addWidget(icon_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name = r["name"]
        nm = QLabel(name if len(name) <= 22 else name[:20] + "…")
        nm.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        ext = Path(r["path"]).suffix.upper().lstrip(".")
        desc = r.get("description", "").strip()
        sub = f"{ext} - {desc[:28]}…" if len(desc) > 28 else f"{ext} - {desc}" if desc else ext
        sl = QLabel(sub)
        sl.setStyleSheet(f"font-size: 11px; color: {C.TEXT3}; background: transparent;")
        name_col.addWidget(nm)
        name_col.addWidget(sl)
        top.addLayout(name_col, 1)
        layout.addLayout(top)
        layout.addStretch()

        tr = QHBoxLayout()
        tr.setSpacing(5)
        for tag in r.get("tags", [])[:3]:
            chip = QLabel(tag)
            chip.setStyleSheet(f"""
                background: {C.PURPLE_DIM}; color: {C.PURPLE3};
                border-radius: 5px; padding: 2px 8px;
                font-size: 10px; font-weight: 600;
            """)
            tr.addWidget(chip)
        tr.addStretch()
        layout.addLayout(tr)
        return card

    def _render_tag_filters(self, files):
        all_tags: list[str] = []
        for f in files:
            all_tags.extend(f.get("tags", []))
        top_tags = [t for t, _ in Counter(all_tags).most_common(8)]

        for i in reversed(range(self._tags_vl.count())):
            item = self._tags_vl.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for tag in top_tags:
            btn = QPushButton(f"  {tag}")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.BG4};
                    color: {C.TEXT2};
                    border: 1px solid {C.BORDER};
                    border-radius: 7px;
                    font-size: 12px;
                    text-align: left;
                    padding-left: 8px;
                }}
                QPushButton:hover {{
                    background: {C.PURPLE_DIM};
                    color: {C.PURPLE3};
                    border-color: {C.PURPLE_DIM2};
                }}
            """)
            self._tags_vl.insertWidget(self._tags_vl.count() - 1, btn)

    def _on_search_changed(self, text):
        self._debounce.start(SEARCH_DEBOUNCE_MS)


# ══════════════════════════════════════════════════════════════════════
# PÁGINA PLACEHOLDER
# ══════════════════════════════════════════════════════════════════════

class PlaceholderPage(QWidget):
    def __init__(self, title: str, icon: str = "🚧", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 52px; background: transparent;")
        layout.addWidget(icon_lbl)
        layout.addSpacing(20)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        layout.addWidget(title_lbl)
        layout.addSpacing(10)

        sub = QLabel("Esta sección está en desarrollo")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            f"font-size: 14px; color: {C.TEXT3}; background: transparent;"
        )
        layout.addWidget(sub)


# ══════════════════════════════════════════════════════════════════════
# VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        self._setup_shortcuts()
        db.init_db()
        QTimer.singleShot(100, self._pages[0].refresh)

    def _setup_window(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(960, 600)
        self.resize(1150, 720)
        self.setStyleSheet(QSS)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width()  - 1150) // 2 + geo.x(),
                (geo.height() - 720)  // 2 + geo.y(),
            )

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._navigate_to)
        root.addWidget(self._sidebar)

        content_wrap = QWidget()
        content_wrap.setStyleSheet(f"background: {C.BG};")
        cl = QVBoxLayout(content_wrap)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        self._pages: list[QWidget] = [
            ResumenPage(),     # 0
            ArchivosPage(),    # 1
            EtiquetasPage(),   # 2
            BusquedaPage(),    # 3
            PlaceholderPage("Configuración", "⚙️"),  # 4
        ]
        for page in self._pages:
            self._stack.addWidget(page)

        cl.addWidget(self._stack, 1)
        root.addWidget(content_wrap, 1)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._set_status("Listo")

    def _setup_shortcuts(self):
        for i in range(1, 6):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda _, idx=i-1: self._navigate_to(idx))
        QShortcut(QKeySequence("F5"), self, self._refresh_current)

    def _navigate_to(self, page_idx: int):
        self._stack.setCurrentIndex(page_idx)
        self._sidebar.navigate_to(page_idx)
        self._refresh_current()

    def _refresh_current(self):
        idx  = self._stack.currentIndex()
        page = self._pages[idx]
        if hasattr(page, "refresh"):
            page.refresh()
        self._set_status(f"Página {idx + 1} de {len(self._pages)}")

    def _set_status(self, msg: str):
        self._status.showMessage(f"  {msg}")


# ══════════════════════════════════════════════════════════════════════
# DEBUG
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
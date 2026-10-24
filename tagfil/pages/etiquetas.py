"""
pages/etiquetas.py — Página de Etiquetas rediseñada v2.

Novedades:
  - StatsBar: 5 métricas clickeables (total, cobertura, top, sin etiquetar, reciente)
  - Alerta roja proactiva cuando hay archivos sin etiquetar
  - TagCard: hover con acciones rápidas (Ver / Eliminar)
  - TagCard: menú contextual con clic derecho
  - RankingModal: top-3 con medallas dorado/plata/bronce + footer
  - EmptyState: estado vacío con botón para crear etiqueta
  - 4 columnas, barra de color arriba, pill de conteo
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QEvent, QRectF, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMenu, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

import database as db
from config import get_logger
from theme import C

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# SVG ICONS
# ══════════════════════════════════════════════════════════════════════

_SVG_WORK     = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>"""
_SVG_PERSONAL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>"""
_SVG_FINANCE  = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>"""
_SVG_DEV      = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>"""
_SVG_DESIGN   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r="1"/><circle cx="17.5" cy="10.5" r="1"/><circle cx="8.5" cy="7.5" r="1"/><circle cx="6.5" cy="12.5" r="1"/><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10c1.1 0 2-.9 2-2v-.5c0-.55.45-1 1-1h1c3.31 0 6-2.69 6-6 0-5.52-4.48-10-10-10z"/></svg>"""
_SVG_SECURITY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>"""
_SVG_TRAVEL   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.9 13.5a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.81 2.7h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 10.09a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>"""
_SVG_LEGAL    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>"""
_SVG_PHOTO    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>"""
_SVG_MUSIC    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>"""
_SVG_BACKUP   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 16 20 20 4 20 4 16"/><polyline points="8 12 12 8 16 12"/><line x1="12" y1="8" x2="12" y2="20"/></svg>"""
_SVG_PYTHON   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/><line x1="12" y1="2" x2="12" y2="22"/></svg>"""
_SVG_TAG      = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>"""
_SVG_STAR     = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>"""
_SVG_SEARCH   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>"""
_SVG_RANKING  = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>"""
_SVG_CLOSE    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>"""
_SVG_FILES    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>"""
_SVG_TRASH    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>"""
_SVG_ALERT    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>"""
_SVG_TROPHY   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/></svg>"""
_SVG_CLOCK    = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>"""
_SVG_PLUS     = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>"""
_SVG_TAGOFF   = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M11.16 11.16 2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82l-7.17 7.17a2 2 0 0 1-2.83 0l-2.72-2.72"/></svg>"""


def _svg_pixmap(svg_data: str, size: int, color: str) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p, QRectF(0, 0, size, size))
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(0, 0, size, size, QColor(color))
    p.end()
    return pm


# ── Paleta mate ────────────────────────────────────────────────────────
_MATTE_RED    = "#C0485A"
_MATTE_PINK   = "#B05080"
_MATTE_PURPLE = "#7A5BAD"
_MATTE_BLUE   = "#4A72B0"
_MATTE_CYAN   = "#3A8A9A"
_MATTE_TEAL   = "#3A9070"
_MATTE_GREEN  = "#4A8A50"
_MATTE_AMBER  = "#9A7030"
_MATTE_ORANGE = "#A85A30"
_MATTE_SLATE  = "#5A6A8A"

_TAG_SVG_MAP: list[tuple[list[str], str, str]] = [
    (["trabajo", "work", "ofic", "empleo", "laboral"],           _SVG_WORK,     _MATTE_BLUE),
    (["personal", "privado", "yo", "familia"],                   _SVG_PERSONAL, _MATTE_PURPLE),
    (["finanz", "dinero", "pago", "contab", "presup", "factur"], _SVG_FINANCE,  _MATTE_TEAL),
    (["dev", "code", "progr", "desarr", "software"],             _SVG_DEV,      _MATTE_CYAN),
    (["diseño", "design", "ui", "ux", "arte", "logo"],           _SVG_DESIGN,   _MATTE_PINK),
    (["segur", "lock", "crypt", "password"],                     _SVG_SECURITY, _MATTE_RED),
    (["viaj", "travel", "vacation", "vuelo", "hotel"],           _SVG_TRAVEL,   _MATTE_CYAN),
    (["legal", "contrat", "docum", "acta", "identid"],           _SVG_LEGAL,    _MATTE_SLATE),
    (["foto", "image", "pic", "captura", "png", "jpg"],          _SVG_PHOTO,    _MATTE_PURPLE),
    (["music", "audio", "song", "playlist", "mp3"],              _SVG_MUSIC,    _MATTE_PINK),
    (["backup", "respaldo", "copia", "archiv"],                  _SVG_BACKUP,   _MATTE_AMBER),
    (["python", "py", "script", "js", "ts", "html", "css"],      _SVG_PYTHON,   _MATTE_CYAN),
    (["2024", "2025", "2026", "año", "trimest"],                 _SVG_STAR,     _MATTE_AMBER),
    (["tagfil", "app", "proyecto", "project"],                   _SVG_TAG,      _MATTE_PURPLE),
    (["marketing", "cliente", "ventas", "propuesta"],            _SVG_WORK,     _MATTE_ORANGE),
    (["salud", "medic", "seguro", "hospital"],                   _SVG_SECURITY, _MATTE_RED),
    (["sqlite", "base", "datos", "database", "db"],              _SVG_DEV,      _MATTE_TEAL),
    (["tarea", "pendiente", "todo", "lista"],                    _SVG_TAG,      _MATTE_ORANGE),
    (["tutorial", "aprend", "curso", "educac"],                  _SVG_STAR,     _MATTE_AMBER),
    (["video", "youtube", "stream", "grabac"],                   _SVG_PHOTO,    _MATTE_RED),
    (["web", "internet", "url", "sitio", "pagina"],              _SVG_DEV,      _MATTE_BLUE),
    (["script", "automatiz", "bot"],                             _SVG_PYTHON,   _MATTE_GREEN),
]


def _tag_svg(name: str) -> tuple[str, str]:
    n = name.lower()
    for keywords, svg, color in _TAG_SVG_MAP:
        if any(k in n for k in keywords):
            return svg, color
    return _SVG_TAG, C.PURPLE3


# ══════════════════════════════════════════════════════════════════════
# HELPERS DE UI
# ══════════════════════════════════════════════════════════════════════

def _rgba(hex_color: str, alpha: float) -> str:
    """'#RRGGBB' + alfa 0–1 → 'rgba(r,g,b,a)'.

    Qt interpreta '#RRGGBBAA' como '#AARRGGBB': por eso los colores con sufijo
    hexadecimal (p. ej. '{color}22') salían con la transparencia al revés.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{int(max(0.0, min(1.0, alpha)) * 255)})"


class _ElidedLabel(QLabel):
    """QLabel de una línea que recorta con «…» en vez de ensanchar el layout."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self._refit()

    def set_full_text(self, text: str):
        self._full = text
        self.setToolTip(text if text and text != "—" else "")
        self._refit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refit()

    def _refit(self):
        shown = self.fontMetrics().elidedText(
            self._full, Qt.TextElideMode.ElideRight, max(0, self.width())
        )
        if shown != self.text():
            super().setText(shown)


class _UsageBar(QWidget):
    """Barra fina de uso relativo (pista + relleno), dibujada a mano."""

    def __init__(self, pct: int, color: str, parent=None):
        super().__init__(parent)
        self._pct, self._color = pct, color
        self.setFixedHeight(4)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C.BG5))
        p.drawRoundedRect(QRectF(0, 0, self.width(), 4), 2, 2)
        p.setBrush(QColor(self._color))
        p.drawRoundedRect(QRectF(0, 0, max(6, self.width() * self._pct / 100), 4), 2, 2)
        p.end()


# ══════════════════════════════════════════════════════════════════════
# TAG CARD — sobria, con acciones al pasar el ratón y menú contextual
# ══════════════════════════════════════════════════════════════════════

class TagCard(QFrame):
    clicked        = pyqtSignal(str)
    request_delete = pyqtSignal(str)

    HEIGHT = 132

    def __init__(self, name: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self._name  = name
        self._count = count
        self._pct   = max(3, int(count / max_count * 100)) if max_count else 3
        svg, color  = _tag_svg(name)
        self._color = color
        self._svg   = svg

        self.setObjectName("tag_card")
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)
        self._build()

    def _apply_style(self, hovered: bool):
        border = _rgba(self._color, 0.70) if hovered else C.BORDER
        bg     = C.BG3 if hovered else C.BG2
        self.setStyleSheet(f"""
            QFrame#tag_card {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)

    def enterEvent(self, e):
        self._apply_style(True)
        self._action_bar.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._apply_style(False)
        self._action_bar.setVisible(False)
        super().leaveEvent(e)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setSpacing(0)

        ic = QLabel()
        ic.setFixedSize(34, 34)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setPixmap(_svg_pixmap(self._svg, 18, self._color))
        ic.setStyleSheet(
            f"background: {_rgba(self._color, 0.14)}; border: none; border-radius: 9px;"
        )
        top_row.addWidget(ic)
        top_row.addStretch()

        pill = QLabel(str(self._count))
        pill.setFixedHeight(20)
        pill.setMinimumWidth(28)
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.setStyleSheet(
            f"background: {C.BG4}; color: {C.TEXT2}; border: none; "
            f"border-radius: 10px; font-size: 11px; font-weight: 600; padding: 0 8px;"
        )
        top_row.addWidget(pill, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top_row)
        layout.addSpacing(10)

        nm = _ElidedLabel(self._name)
        nm.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {C.TEXT}; "
            f"background: transparent; border: none;"
        )
        nm.set_full_text(self._name)
        layout.addWidget(nm)

        n = self._count
        cnt = QLabel(f"{n} archivo{'s' if n != 1 else ''}")
        cnt.setStyleSheet(
            f"font-size: 11.5px; color: {C.TEXT3}; background: transparent; border: none;"
        )
        layout.addWidget(cnt)
        layout.addStretch()

        layout.addWidget(_UsageBar(self._pct, self._color))

        # Barra de acciones (solo al pasar el ratón)
        self._action_bar = QFrame(self)
        self._action_bar.setObjectName("tag_actions")
        self._action_bar.setStyleSheet(f"""
            QFrame#tag_actions {{
                background: {C.BG3};
                border: none;
                border-top: 1px solid {C.BORDER};
                border-bottom-left-radius: 11px;
                border-bottom-right-radius: 11px;
            }}
        """)
        self._action_bar.setFixedHeight(30)
        self._action_bar.setVisible(False)
        ab = QHBoxLayout(self._action_bar)
        ab.setContentsMargins(10, 0, 10, 0)
        ab.setSpacing(6)

        btn_ver = QPushButton("Ver archivos")
        btn_ver.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ver.setStyleSheet(f"""
            QPushButton {{
                background: {_rgba(C.PURPLE, 0.16)}; color: {C.PURPLE3};
                border: none; border-radius: 6px;
                font-size: 11px; font-weight: 600; padding: 3px 10px;
            }}
            QPushButton:hover {{ background: {_rgba(C.PURPLE, 0.30)}; }}
        """)
        btn_ver.clicked.connect(lambda: self.clicked.emit(self._name))
        ab.addWidget(btn_ver, 1)

        btn_del = QPushButton()
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("Eliminar etiqueta")
        btn_del.setFixedSize(22, 22)
        btn_del.setIcon(QIcon(_svg_pixmap(_SVG_TRASH, 13, _MATTE_RED)))
        btn_del.setIconSize(QSize(13, 13))
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 6px; padding: 0;
            }}
            QPushButton:hover {{ background: {_rgba(_MATTE_RED, 0.22)}; }}
        """)
        btn_del.clicked.connect(lambda: self.request_delete.emit(self._name))
        ab.addWidget(btn_del)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {C.BG2}; border: 1px solid {C.BORDER2};
                border-radius: 10px; padding: 4px;
            }}
            QMenu::item {{
                padding: 7px 16px; font-size: 12px;
                color: {C.TEXT2}; border-radius: 6px;
            }}
            QMenu::item:selected {{ background: {C.BG3}; color: {C.TEXT}; }}
            QMenu::separator {{ height: 1px; background: {C.BORDER}; margin: 3px 8px; }}
        """)
        menu.addAction(
            QIcon(_svg_pixmap(_SVG_FILES, 14, C.PURPLE3)),
            "Ver archivos",
            lambda: self.clicked.emit(self._name)
        )
        menu.addSeparator()
        menu.addAction(
            QIcon(_svg_pixmap(_SVG_TRASH, 14, _MATTE_RED)),
            "Eliminar etiqueta",
            lambda: self.request_delete.emit(self._name)
        )
        menu.exec(e.globalPos())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._action_bar.setGeometry(1, self.height() - 31, self.width() - 2, 30)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._name)


# ══════════════════════════════════════════════════════════════════════
# STATS BAR — un único panel con 5 métricas clicables
# ══════════════════════════════════════════════════════════════════════

class _StatItem(QFrame):
    """Una métrica. Se construye UNA vez y luego solo se actualizan sus textos."""
    clicked = pyqtSignal()

    def __init__(self, svg: str, label: str, parent=None):
        super().__init__(parent)
        self._svg = svg
        self.setObjectName("stat_item")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self._icon = QLabel()
        self._icon.setFixedSize(36, 36)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)

        self._lbl = _ElidedLabel(label)
        self._lbl.setStyleSheet(
            f"font-size: 11.5px; font-weight: 500; "
            f"color: {C.TEXT3}; background: transparent; border: none;"
        )
        self._val = _ElidedLabel("—")
        self._val.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {C.TEXT}; "
            f"background: transparent; border: none;"
        )
        self._delta = _ElidedLabel("")
        self._delta.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent; border: none;"
        )
        col.addWidget(self._lbl)
        col.addWidget(self._val)
        col.addWidget(self._delta)
        layout.addLayout(col, 1)

        self.set_data(C.PURPLE3, "—")

    def _apply_style(self, hovered: bool):
        bg = C.BG3 if hovered else "transparent"
        self.setStyleSheet(
            f"QFrame#stat_item {{ background: {bg}; border: none; border-radius: 10px; }}"
        )

    def enterEvent(self, e):
        self._apply_style(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._apply_style(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def show_icon(self, visible: bool):
        self._icon.setVisible(visible)

    def set_data(self, color: str, value: str, delta: str = "", delta_color: str = ""):
        self._icon.setPixmap(_svg_pixmap(self._svg, 18, color))
        self._icon.setStyleSheet(
            f"background: {_rgba(color, 0.14)}; border: none; border-radius: 10px;"
        )
        self._val.set_full_text(value)
        self._delta.set_full_text(delta)
        self._delta.setVisible(bool(delta))
        self._delta.setStyleSheet(
            f"font-size: 11px; color: {delta_color or C.TEXT3}; "
            f"background: transparent; border: none;"
        )


class StatsBar(QWidget):
    stat_clicked = pyqtSignal(str)  # "total"|"coverage"|"top"|"untagged"|"recent"

    _COMPACT_BELOW = 760  # por debajo de este ancho se ocultan los iconos

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # ── Panel único ───────────────────────────────────────────────
        panel = QFrame()
        panel.setObjectName("stats_panel")
        panel.setStyleSheet(f"""
            QFrame#stats_panel {{
                background: {C.BG2};
                border: 1px solid {C.BORDER};
                border-radius: 12px;
            }}
        """)
        rl = QHBoxLayout(panel)
        rl.setContentsMargins(6, 6, 6, 6)
        rl.setSpacing(0)

        self._s_total    = _StatItem(_SVG_TAG,    "Total etiquetas")
        self._s_coverage = _StatItem(_SVG_FILES,  "Cobertura")
        self._s_top      = _StatItem(_SVG_TROPHY, "Más usada")
        self._s_untagged = _StatItem(_SVG_TAGOFF, "Sin etiquetar")
        self._s_recent   = _StatItem(_SVG_CLOCK,  "Último cambio")
        self._items = [self._s_total, self._s_coverage, self._s_top,
                       self._s_untagged, self._s_recent]

        pairs = list(zip(self._items, ("total", "coverage", "top", "untagged", "recent")))
        for i, (w, key) in enumerate(pairs):
            w.clicked.connect(lambda k=key: self.stat_clicked.emit(k))
            rl.addWidget(w, 1)
            if i < len(pairs) - 1:
                wrap = QWidget()
                wrap.setFixedWidth(1)
                wrap.setStyleSheet("background: transparent;")
                wl = QVBoxLayout(wrap)
                wl.setContentsMargins(0, 12, 0, 12)
                line = QFrame()
                line.setStyleSheet(f"background: {C.BORDER}; border: none;")
                wl.addWidget(line)
                rl.addWidget(wrap)
        root.addWidget(panel)

        # ── Aviso (debajo del panel, solo si hay archivos sin etiquetar) ──
        self._alert = QFrame()
        self._alert.setObjectName("alert_bar")
        self._alert.setStyleSheet(f"""
            QFrame#alert_bar {{
                background: {_rgba(C.AMBER, 0.08)};
                border: 1px solid {_rgba(C.AMBER, 0.28)};
                border-radius: 10px;
            }}
        """)
        self._alert.setFixedHeight(40)
        self._alert.setVisible(False)
        al = QHBoxLayout(self._alert)
        al.setContentsMargins(14, 0, 8, 0)
        al.setSpacing(10)

        aic = QLabel()
        aic.setFixedSize(14, 14)
        aic.setPixmap(_svg_pixmap(_SVG_ALERT, 14, C.AMBER))
        aic.setStyleSheet("background: transparent; border: none;")
        al.addWidget(aic)

        self._alert_lbl = _ElidedLabel()
        self._alert_lbl.setStyleSheet(
            f"font-size: 12px; color: {C.TEXT2}; background: transparent; border: none;"
        )
        al.addWidget(self._alert_lbl, 1)

        self._alert_btn = QPushButton("Ver archivos")
        self._alert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._alert_btn.setFixedHeight(26)
        self._alert_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_rgba(C.AMBER, 0.14)}; color: {C.AMBER};
                border: none; border-radius: 7px;
                font-size: 11.5px; font-weight: 600; padding: 0 12px;
            }}
            QPushButton:hover {{ background: {_rgba(C.AMBER, 0.26)}; }}
        """)
        self._alert_btn.clicked.connect(lambda: self.stat_clicked.emit("untagged"))
        al.addWidget(self._alert_btn)
        root.addWidget(self._alert)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        show = self.width() >= self._COMPACT_BELOW
        for it in self._items:
            it.show_icon(show)

    def update_stats(self, tags_data: list[dict], total_files: int):
        n_tags  = len(tags_data)
        in_use  = sum(1 for t in tags_data if t["count"] > 0)
        top_tag = max(tags_data, key=lambda t: t["count"]) if tags_data else None

        try:
            untagged = len(db.get_untagged_files()) if hasattr(db, "get_untagged_files") else 0
        except Exception:
            untagged = 0
        untagged = min(untagged, total_files) if total_files else untagged
        tagged_files = max(0, total_files - untagged)
        pct = round(tagged_files / total_files * 100, 1) if total_files else None

        try:
            recent_list = db.get_recent_files(1) if hasattr(db, "get_recent_files") else []
            rname = recent_list[0].get("name", "—") if recent_list else "—"
        except Exception:
            rname = "—"

        self._s_total.set_data(
            C.PURPLE3, str(n_tags),
            f"{in_use} en uso" if n_tags else "Sin etiquetas aún",
        )

        if pct is None:
            self._s_coverage.set_data(C.PURPLE3, "—", "Sin archivos")
        else:
            cov_color = C.GREEN if pct >= 90 else (C.AMBER if pct >= 60 else C.RED)
            self._s_coverage.set_data(
                cov_color, f"{pct:g}%", f"{tagged_files} de {total_files} etiquetados", cov_color
            )

        if top_tag and top_tag["count"] > 0:
            n = top_tag["count"]
            self._s_top.set_data(
                C.PURPLE3, top_tag["name"], f"{n} archivo{'s' if n != 1 else ''}"
            )
        else:
            self._s_top.set_data(C.PURPLE3, "—", "")

        if untagged > 0:
            self._s_untagged.set_data(C.AMBER, str(untagged), "Requieren etiqueta", C.AMBER)
        else:
            self._s_untagged.set_data(C.GREEN, "0", "Todo etiquetado", C.GREEN)

        self._s_recent.set_data(C.PURPLE3, rname, "Archivo más reciente" if rname != "—" else "")

        self._alert.setVisible(untagged > 0)
        if untagged > 0:
            s = "s" if untagged != 1 else ""
            self._alert_lbl.set_full_text(
                f"{untagged} archivo{s} sin etiquetar. Etiquetarlos mejora tus búsquedas."
            )


# ══════════════════════════════════════════════════════════════════════
# RANKING ROW — con medallas top-3
# ══════════════════════════════════════════════════════════════════════

class RankingRow(QWidget):
    _MEDAL = {1: "#F0C060", 2: "#B0B8C8", 3: "#C08060"}

    def __init__(self, rank: int, name: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        svg, color = _tag_svg(name)
        pct        = max(4, int(count / max_count * 100)) if max_count else 4
        num_color  = self._MEDAL.get(rank, color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 4)
        layout.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(8)

        rank_lbl = QLabel(f"#{rank}")
        rank_lbl.setFixedWidth(26)
        rank_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 800; color: {num_color}; "
            f"background: transparent; letter-spacing: 0.5px;"
        )
        top.addWidget(rank_lbl)

        ic = QLabel()
        ic.setFixedSize(14, 14)
        ic.setPixmap(_svg_pixmap(svg, 14, color))
        ic.setStyleSheet("background: transparent;")
        top.addWidget(ic)

        nm = QLabel(name)
        nm.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {C.TEXT}; background: transparent;"
        )
        top.addWidget(nm, 1)

        cnt = QLabel(str(count))
        cnt.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {color}; background: transparent;"
        )
        top.addWidget(cnt)
        layout.addLayout(top)

        bar_bg = QFrame()
        bar_bg.setFixedHeight(3)
        bar_bg.setStyleSheet(f"background: {C.BG4}; border-radius: 2px; border: none;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setFixedHeight(3)
        bar_inner.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {color}, stop:1 {color}44);
            border-radius: 2px;
        """)
        bar_inner.setFixedWidth(int(250 * pct / 100))
        layout.addWidget(bar_bg)


# ══════════════════════════════════════════════════════════════════════
# RANKING MODAL
# ══════════════════════════════════════════════════════════════════════

class RankingModal(QDialog):

    def __init__(self, tags_data: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ranking de Etiquetas")
        self.setFixedWidth(340)
        self.setMinimumHeight(400)
        self.setMaximumHeight(600)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build(tags_data)

    def _build(self, tags_data: list[dict]):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {C.BG2};
                border: 1px solid {C.BORDER2};
                border-radius: 16px;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 20, 20, 20)
        cl.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(18, 18)
        icon_lbl.setPixmap(_svg_pixmap(_SVG_RANKING, 18, C.PURPLE3))
        icon_lbl.setStyleSheet("background: transparent;")
        hdr.addWidget(icon_lbl)
        hdr.addSpacing(8)
        title = QLabel("Ranking completo")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        hdr.addWidget(title, 1)
        close_btn = QPushButton()
        close_btn.setFixedSize(28, 28)
        close_btn.setIcon(QIcon(_svg_pixmap(_SVG_CLOSE, 14, C.TEXT3)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.BG3}; border: 1px solid {C.BORDER}; border-radius: 14px;
            }}
            QPushButton:hover {{ background: {C.BG4}; }}
        """)
        close_btn.clicked.connect(self.close)
        hdr.addWidget(close_btn)
        cl.addLayout(hdr)
        cl.addSpacing(8)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C.PURPLE}, stop:1 transparent);
            border: none;
        """)
        cl.addWidget(sep)
        cl.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 3px; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER2}; border-radius: 2px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)

        max_count = max((t["count"] for t in tags_data), default=1)
        for idx, tag in enumerate(tags_data):
            row = RankingRow(idx + 1, tag["name"], tag["count"], max_count)
            vl.addWidget(row)
        vl.addStretch()

        scroll.setWidget(container)
        cl.addWidget(scroll, 1)

        # Footer
        cl.addSpacing(8)
        footer = QLabel(f"{len(tags_data)} etiquetas activas · ordenado por uso")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            f"font-size: 10px; color: {C.TEXT3}; background: transparent;"
        )
        cl.addWidget(footer)
        outer.addWidget(card)


# ══════════════════════════════════════════════════════════════════════
# EMPTY STATE — cuando no hay resultados
# ══════════════════════════════════════════════════════════════════════

class EmptyState(QWidget):
    create_requested = pyqtSignal(str)

    def __init__(self, query: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(40, 40, 40, 40)

        ic = QLabel()
        ic.setFixedSize(40, 40)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setPixmap(_svg_pixmap(_SVG_TAGOFF, 36, C.BORDER2))
        ic.setStyleSheet("background: transparent;")
        layout.addWidget(ic, alignment=Qt.AlignmentFlag.AlignCenter)

        if query:
            title = QLabel(f'No hay etiquetas con "{query}"')
            sub   = QLabel("Intenta otro término o crea esta etiqueta nueva")
        else:
            title = QLabel("Aún no tienes etiquetas")
            sub   = QLabel("Crea tu primera etiqueta para organizar tus archivos")

        for w, sz, col in [(title, 14, C.TEXT2), (sub, 12, C.TEXT3)]:
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setStyleSheet(
                f"font-size: {sz}px; font-weight: {'600' if sz==14 else '400'}; "
                f"color: {col}; background: transparent;"
            )
            layout.addWidget(w)

        if query:
            btn = QPushButton(f'  Crear "{query}"')
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.BG3}; color: {C.PURPLE3};
                    border: 1px solid {C.PURPLE}; border-radius: 8px;
                    font-size: 12px; padding: 6px 16px; margin-top: 4px;
                }}
                QPushButton:hover {{ background: {C.BG4}; }}
            """)
            btn.clicked.connect(lambda: self.create_requested.emit(query))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ══════════════════════════════════════════════════════════════════════
# ETIQUETAS PAGE
# ══════════════════════════════════════════════════════════════════════

class EtiquetasPage(QWidget):
    navigate_to_tag = pyqtSignal(str)  # emitida al hacer clic en una etiqueta

    _GAP         = 12
    _CARD_MIN_W  = 220
    _MAX_COLS    = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags_data:   list[dict] = []
        self._total_files: int        = 0
        self._sort_mode               = "count"
        self._search_query            = ""
        self._cards:       list[QWidget] = []
        self._empty:       QWidget | None = None
        self._cols                    = 0
        self._build()

    # ── Construcción ───────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 20)
        root.setSpacing(0)

        # Fila 1: título + acción principal
        head = QHBoxLayout()
        head.setSpacing(12)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Etiquetas")
        title.setObjectName("page_title")
        titles.addWidget(title)
        sub = QLabel("Navega, filtra y ordena tus archivos por etiqueta")
        sub.setStyleSheet(f"font-size: 12.5px; color: {C.TEXT3}; background: transparent;")
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch()

        self._btn_new = QPushButton("  Nueva etiqueta")
        self._btn_new.setObjectName("btn_primary")
        self._btn_new.setFixedHeight(38)
        self._btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_new.setIcon(QIcon(_svg_pixmap(_SVG_PLUS, 14, "#FFFFFF")))
        self._btn_new.setIconSize(QSize(14, 14))
        self._btn_new.clicked.connect(self._prompt_new_tag)
        head.addWidget(self._btn_new, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)
        root.addSpacing(18)

        # Fila 2: búsqueda (flexible) + orden + ranking
        bar = QHBoxLayout()
        bar.setSpacing(10)

        self._search_frame = QFrame()
        self._search_frame.setObjectName("tag_search")
        self._search_frame.setFixedHeight(38)
        self._search_frame.setMinimumWidth(180)
        self._search_frame.setMaximumWidth(420)
        self._search_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._set_search_focus(False)
        sfl = QHBoxLayout(self._search_frame)
        sfl.setContentsMargins(12, 0, 8, 0)
        sfl.setSpacing(8)

        # Solo la lupa, sin recuadro
        self._lupa_lbl = QLabel()
        self._lupa_lbl.setFixedSize(16, 16)
        self._lupa_lbl.setPixmap(_svg_pixmap(_SVG_SEARCH, 16, C.TEXT3))
        self._lupa_lbl.setStyleSheet("background: transparent; border: none; padding: 0;")
        sfl.addWidget(self._lupa_lbl)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar etiquetas…")
        self._search_input.setStyleSheet(f"""
            QLineEdit, QLineEdit:focus {{
                background: transparent; border: none; padding: 0;
                font-size: 13px; color: {C.TEXT};
            }}
        """)
        self._search_input.textChanged.connect(self._on_search)
        self._search_input.installEventFilter(self)
        sfl.addWidget(self._search_input, 1)

        self._clear_btn = QPushButton()
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setToolTip("Limpiar búsqueda")
        self._clear_btn.setIcon(QIcon(_svg_pixmap(_SVG_CLOSE, 11, C.TEXT3)))
        self._clear_btn.setIconSize(QSize(11, 11))
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 10px; padding: 0; }}
            QPushButton:hover {{ background: {C.BG4}; }}
        """)
        self._clear_btn.clicked.connect(lambda: self._search_input.clear())
        self._clear_btn.setVisible(False)
        sfl.addWidget(self._clear_btn)
        bar.addWidget(self._search_frame, 1)
        bar.addStretch(1)

        # Control segmentado de orden
        seg = QFrame()
        seg.setObjectName("seg_group")
        seg.setFixedHeight(38)
        seg.setStyleSheet(f"""
            QFrame#seg_group {{
                background: {C.BG2}; border: 1px solid {C.BORDER}; border-radius: 10px;
            }}
            QPushButton {{
                background: transparent; color: {C.TEXT2}; border: none;
                border-radius: 7px; padding: 0 14px; font-size: 12.5px; font-weight: 600;
            }}
            QPushButton:hover {{ color: {C.TEXT}; }}
            QPushButton:checked {{ background: {C.PURPLE_DIM2}; color: {C.PURPLE3}; }}
        """)
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(2)
        self._btn_mas = QPushButton("Más usados")
        self._btn_az  = QPushButton("A–Z")
        for b, mode in ((self._btn_mas, "count"), (self._btn_az, "alpha")):
            b.setCheckable(True)
            b.setMinimumWidth(92)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, m=mode: self._set_sort(m))
            sl.addWidget(b)
        self._btn_mas.setChecked(True)
        bar.addWidget(seg)

        self._btn_ranking = QPushButton("  Ranking")
        self._btn_ranking.setObjectName("btn_ghost")
        self._btn_ranking.setFixedHeight(38)
        self._btn_ranking.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_ranking.setIcon(QIcon(_svg_pixmap(_SVG_RANKING, 14, C.TEXT2)))
        self._btn_ranking.setIconSize(QSize(14, 14))
        self._btn_ranking.clicked.connect(self._open_ranking)
        bar.addWidget(self._btn_ranking)

        root.addLayout(bar)
        root.addSpacing(16)

        # Panel de métricas
        self._stats_bar = StatsBar()
        self._stats_bar.stat_clicked.connect(self._on_stat_clicked)
        root.addWidget(self._stats_bar)
        root.addSpacing(18)

        # Subtítulo dinámico
        self._lbl_count = QLabel("")
        self._lbl_count.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {C.TEXT3}; "
            f"background: transparent; padding-bottom: 10px;"
        )
        root.addWidget(self._lbl_count)

        # Cuadrícula con columnas adaptables
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER2}; border-radius: 3px; min-height: 32px; }}
            QScrollBar::handle:vertical:hover {{ background: {C.PURPLE}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 8, 0)
        self._grid.setSpacing(self._GAP)
        self._scroll.setWidget(self._grid_container)
        root.addWidget(self._scroll, 1)

    # ── Foco del buscador ──────────────────────────────────────────────

    def _set_search_focus(self, focused: bool):
        border = C.PURPLE if focused else C.BORDER
        self._search_frame.setStyleSheet(f"""
            QFrame#tag_search {{
                background: {C.BG2}; border: 1px solid {border}; border-radius: 10px;
            }}
        """)
        if hasattr(self, "_lupa_lbl"):
            self._lupa_lbl.setPixmap(
                _svg_pixmap(_SVG_SEARCH, 16, C.PURPLE3 if focused else C.TEXT3)
            )

    def eventFilter(self, obj, ev):
        if obj is getattr(self, "_search_input", None):
            if ev.type() == QEvent.Type.FocusIn:
                self._set_search_focus(True)
            elif ev.type() == QEvent.Type.FocusOut:
                self._set_search_focus(False)
        return super().eventFilter(obj, ev)

    # ── Modal ranking ──────────────────────────────────────────────────

    def _open_ranking(self):
        if not self._tags_data:
            return
        modal = RankingModal(self._tags_data, self)
        modal.adjustSize()
        x = self.mapToGlobal(self.rect().topLeft()).x() + (self.width()  - modal.width())  // 2
        y = self.mapToGlobal(self.rect().topLeft()).y() + (self.height() - modal.height()) // 2
        modal.move(x, y)
        modal.exec()

    # ── Clics en métricas ──────────────────────────────────────────────

    def _on_stat_clicked(self, key: str):
        if key == "untagged":
            self.navigate_to_tag.emit("__untagged__")
        elif key == "top" and self._tags_data:
            top = max(self._tags_data, key=lambda t: t["count"])
            self._search_input.setText(top["name"])
        elif key in ("coverage", "total"):
            self._open_ranking()
        elif key == "recent":
            self.navigate_to_tag.emit("__recent__")

    # ── Lógica principal ───────────────────────────────────────────────

    def refresh(self):
        try:
            self._tags_data = db.get_tag_counts()
            try:
                self._total_files = db.get_stats().get("total_files", 0)
            except Exception:
                self._total_files = 0

            self._apply_sort()
            self._stats_bar.update_stats(self._tags_data, self._total_files)
            self._render()
        except Exception as e:
            logger.exception(f"Error cargando etiquetas: {e}")

    def _apply_sort(self):
        if self._sort_mode == "count":
            self._tags_data.sort(key=lambda t: (-t["count"], t["name"].lower()))
        else:
            self._tags_data.sort(key=lambda t: t["name"].lower())

    def _filtered_tags(self):
        q = self._search_query.strip().lower()
        return [t for t in self._tags_data if q in t["name"].lower()] if q else self._tags_data

    def _columns(self) -> int:
        w = self._scroll.viewport().width() - self._grid.contentsMargins().right()
        cols = (w + self._GAP) // (self._CARD_MIN_W + self._GAP)
        return max(1, min(self._MAX_COLS, cols))

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards = []
        self._empty = None

    def _render(self):
        filtered  = self._filtered_tags()
        max_count = max((t["count"] for t in filtered), default=1)

        total = len(self._tags_data)
        shown = len(filtered)
        if self._search_query.strip():
            self._lbl_count.setText(
                f"{shown} resultado{'s' if shown != 1 else ''} de {total} "
                f"etiqueta{'s' if total != 1 else ''}"
            )
        else:
            order = "por uso" if self._sort_mode == "count" else "alfabéticamente"
            self._lbl_count.setText(
                f"{total} etiqueta{'s' if total != 1 else ''} · ordenadas {order}"
                if total else "Sin etiquetas todavía"
            )

        self._clear_grid()

        if not filtered:
            self._empty = EmptyState(self._search_query.strip())
            self._empty.create_requested.connect(self._on_create_tag)
        else:
            for tag in filtered:
                card = TagCard(tag["name"], tag["count"], max_count)
                card.clicked.connect(self.navigate_to_tag)
                card.request_delete.connect(self._on_delete_tag)
                self._cards.append(card)
        self._place()

    def _place(self):
        """Coloca los widgets actuales en la cuadrícula según el ancho disponible."""
        cols = self._columns()
        self._cols = cols
        while self._grid.count():
            self._grid.takeAt(0)          # no destruye los widgets
        for c in range(self._MAX_COLS + 1):
            self._grid.setColumnStretch(c, 1 if c < cols else 0)
        for r in range(len(self._cards) + 2):
            self._grid.setRowStretch(r, 0)

        if self._empty is not None:
            self._grid.addWidget(self._empty, 0, 0, 1, cols)
            self._grid.setRowStretch(1, 1)
            return
        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // cols, i % cols)
        self._grid.setRowStretch((len(self._cards) - 1) // cols + 1, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if (self._cards or self._empty is not None) and self._columns() != self._cols:
            self._place()

    def showEvent(self, e):
        super().showEvent(e)
        if (self._cards or self._empty is not None) and self._columns() != self._cols:
            self._place()

    def _on_search(self, text: str):
        self._search_query = text
        self._clear_btn.setVisible(bool(text))
        self._render()

    def _set_sort(self, mode: str):
        self._sort_mode = mode
        self._btn_mas.setChecked(mode == "count")
        self._btn_az.setChecked(mode == "alpha")
        self._apply_sort()
        self._render()

    def _on_delete_tag(self, name: str):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Eliminar etiqueta")
        msg.setText(f'¿Eliminar la etiqueta <b>"{name}"</b>?')
        msg.setInformativeText(
            "Esta acción no se puede deshacer. Los archivos no serán eliminados."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                db.delete_tag(name)
                self.refresh()
            except Exception as e:
                logger.exception(f"Error eliminando etiqueta: {e}")

    def _prompt_new_tag(self):
        name, ok = QInputDialog.getText(self, "Nueva etiqueta", "Nombre de la etiqueta:")
        if ok and name.strip():
            self._on_create_tag(name.strip())

    def _on_create_tag(self, name: str):
        try:
            db.create_tag(name)
            self._search_input.clear()
            self.refresh()
        except ValueError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Nombre no válido",
                                "Usa letras, números o guiones en el nombre de la etiqueta.")
        except Exception as e:
            logger.exception(f"Error creando etiqueta: {e}")

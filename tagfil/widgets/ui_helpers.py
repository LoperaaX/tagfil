"""
ui_helpers.py — Funciones de UI reutilizables y GlowCard base.
"""
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QRectF
from PyQt6.QtGui import (
    QColor, QLinearGradient, QPainter, QPen, QBrush, QPixmap
)
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QWidget

from theme import C


# ── Separador horizontal ──────────────────────────────────────────────

def sep(horizontal: bool = True, parent=None) -> QFrame:
    f = QFrame(parent)
    f.setFrameShape(QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine)
    f.setStyleSheet(f"background: {C.BORDER}; max-height: 1px; border: none; margin: 0;")
    f.setFixedHeight(1)
    return f


# ── Sombra rápida ─────────────────────────────────────────────────────

def shadow(radius: int = 20, color: str = "#00000070") -> QGraphicsDropShadowEffect:
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(radius)
    eff.setOffset(0, 2)
    eff.setColor(QColor(color))
    return eff


# ── Emoji/icono de extensión ──────────────────────────────────────────

def ext_icon_str(path: str) -> str:
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


def tag_icon(tag_name: str) -> str:
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


# ── SVG → QPixmap ─────────────────────────────────────────────────────

_IC = "#9D5EF0"

def svg_pixmap(svg_str: str, size: int = 22, color: str = _IC) -> QPixmap:
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
    _RADIUS   = 20.0
    _BG_TOP   = QColor("#1C1A30")
    _BG_BOT   = QColor("#0F0E1C")
    _GLOW_COL = QColor("#7C3AED")
    _ACC_COL  = QColor("#A78BFA")

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

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, self._BG_TOP)
        grad.setColorAt(1.0, self._BG_BOT)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, rad, rad)

        p.setBrush(Qt.BrushStyle.NoBrush)
        layers = [(45, 1.5), (28, 3), (16, 5.5), (9, 8), (4, 12)] if self._hovered \
            else [(28, 1.2), (14, 3.5), (6, 6)]
        for alpha, width in layers:
            gc = QColor(self._GLOW_COL)
            gc.setAlpha(alpha)
            p.setPen(QPen(gc, width))
            exp = int(width * 0.5)
            p.drawRoundedRect(r.adjusted(-exp, -exp, exp, exp), rad + exp, rad + exp)

        bc = QColor(self._GLOW_COL)
        bc.setAlpha(200 if self._hovered else 80)
        p.setPen(QPen(bc, 1.0))
        p.drawRoundedRect(r, rad, rad)

        acc = QColor(self._ACC_COL)
        acc.setAlpha(255 if self._hovered else 180)
        pen_acc = QPen(acc, 2.2)
        pen_acc.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_acc)
        cx = w // 2
        half = min(80, w // 3) if self._hovered else min(55, w // 4)
        p.drawLine(cx - half, r.top() + 1, cx + half, r.top() + 1)

        if self._hovered:
            dot_c = QColor(self._ACC_COL)
            dot_c.setAlpha(255)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(dot_c))
            p.drawEllipse(cx - 3, r.top() - 2, 6, 6)

        p.end()

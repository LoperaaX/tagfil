"""
neon_icon.py — NeonSvgIcon widget y constantes SVG de línea para TagFil.
"""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QBrush
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget

class NeonSvgIcon(QWidget):
    """
    Widget que renderiza un SVG de línea con efecto glow neón morado
    usando QPainter. Acepta un path SVG como string.
    """
    def __init__(self, svg_path: str, size: int = 28,
                 color: str = "#A78BFA", glow: bool = True, parent=None):
        super().__init__(parent)
        self._svg_path = svg_path
        self._size     = size
        self._color    = QColor(color)
        self._glow     = glow
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._renderer = QSvgRenderer(svg_path.encode() if svg_path.startswith("<") else svg_path.encode())
        # Si recibimos SVG literal como string, usar QSvgRenderer con bytes
        self._svg_data = svg_path if svg_path.startswith("<") else None

    @classmethod
    def from_data(cls, svg_data: str, size: int = 28,
                  color: str = "#A78BFA", glow: bool = True, parent=None):
        obj = cls.__new__(cls)
        QWidget.__init__(obj, parent)
        obj._svg_data = svg_data
        obj._size     = size
        obj._color    = QColor(color)
        obj._glow     = glow
        obj.setFixedSize(size, size)
        obj.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        obj._renderer = QSvgRenderer(svg_data.encode("utf-8"))
        return obj

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Dibujamos en un pixmap temporal para aplicar glow
        pm = QPixmap(self._size, self._size)
        pm.fill(Qt.GlobalColor.transparent)
        pp = QPainter(pm)
        pp.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._renderer.render(pp, QRectF(0, 0, self._size, self._size))
        pp.end()

        # Tintamos el pixmap al color deseado
        tinted = QPixmap(self._size, self._size)
        tinted.fill(Qt.GlobalColor.transparent)
        tp = QPainter(tinted)
        tp.setRenderHint(QPainter.RenderHint.Antialiasing)
        tp.drawPixmap(0, 0, pm)
        tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        tp.fillRect(0, 0, self._size, self._size, self._color)
        tp.end()

        # Glow: dibujamos el tinted desenfocado varias veces
        if self._glow:
            glow_color = QColor(self._color)
            for radius, alpha in ((6, 60), (4, 90), (2, 120)):
                glow_pm = QPixmap(self._size, self._size)
                glow_pm.fill(Qt.GlobalColor.transparent)
                gp = QPainter(glow_pm)
                glow_color.setAlpha(alpha)
                effect_pen = QPen(glow_color, radius * 2)
                effect_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                gp.setPen(effect_pen)
                gp.drawPixmap(0, 0, tinted)
                gp.end()
                p.setOpacity(0.35)
                p.drawPixmap(0, 0, glow_pm)

        p.setOpacity(1.0)
        p.drawPixmap(0, 0, tinted)
        p.end()


# SVGs inline estilo línea (stroke only, sin fill)
_SVG_MOON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
</svg>"""

_SVG_SUN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="5"/>
  <line x1="12" y1="1"  x2="12" y2="3"/>
  <line x1="12" y1="21" x2="12" y2="23"/>
  <line x1="4.22" y1="4.22"  x2="5.64" y2="5.64"/>
  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
  <line x1="1" y1="12" x2="3" y2="12"/>
  <line x1="21" y1="12" x2="23" y2="12"/>
  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
</svg>"""

_SVG_SYSTEM = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
  <path d="M15.54 8.46a5 5 0 0 1 0 7.07M8.46 8.46a5 5 0 0 0 0 7.07"/>
</svg>"""

_SVG_LIGHTNING = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
</svg>"""

_SVG_SHIELD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
</svg>"""

_SVG_PALETTE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="13.5" cy="6.5" r="1"/><circle cx="17.5" cy="10.5" r="1"/>
  <circle cx="8.5"  cy="7.5" r="1"/><circle cx="6.5"  cy="12.5" r="1"/>
  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10c1.1 0 2-.9 2-2v-.5c0-.55.45-1 1-1h1c3.31 0 6-2.69 6-6 0-5.52-4.48-10-10-10z"/>
</svg>"""

_SVG_DB = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <ellipse cx="12" cy="5" rx="9" ry="3"/>
  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
</svg>"""

_SVG_SAVE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
  <polyline points="17 21 17 13 7 13 7 21"/>
  <polyline points="7 3 7 8 15 8"/>
</svg>"""



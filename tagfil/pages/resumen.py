"""
pages/resumen.py — Página de Resumen rediseñada (mockup B final).

Layout:
  Header (título + alerta papelera)
  ── 3 stat cards (Archivos · Etiquetas · Sin etiqueta)
  ── 2 cards grandes:
       izq: Espacio usado (donut + barras + distribución por tipo)
       der: Archivos recientes (lista con ícono color + tamaño)
"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QByteArray
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QConicalGradient, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

import database as db
from config import get_logger
from theme import C
from widgets.ui_helpers import GlowCard

logger = get_logger(__name__)

# ── SVG helper ────────────────────────────────────────────────────────
def _svg_px(svg: str, color: str, size: int = 18) -> QPixmap:
    svg = svg.replace("CLR", color)
    try:
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtCore import QByteArray
        r = QSvgRenderer(QByteArray(svg.encode()))
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r.render(p)
        p.end()
        return px
    except Exception:
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        return px

_SVG = {
    "files": "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z' stroke='CLR' stroke-width='1.7'/><polyline points='15 2 15 8 21 8' stroke='CLR' stroke-width='1.7'/><line x1='9' y1='13' x2='15' y2='13' stroke='CLR' stroke-width='1.5'/><line x1='9' y1='17' x2='13' y2='17' stroke='CLR' stroke-width='1.5'/></svg>",
    "tags":  "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z' stroke='CLR' stroke-width='1.7'/><circle cx='7' cy='7' r='1.3' fill='CLR'/></svg>",
    "untagged": "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><circle cx='12' cy='12' r='9' stroke='CLR' stroke-width='1.7'/><line x1='12' y1='8' x2='12' y2='12' stroke='CLR' stroke-width='1.7' stroke-linecap='round'/><circle cx='12' cy='16' r='0.8' fill='CLR'/></svg>",
    "db":    "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><ellipse cx='12' cy='5' rx='9' ry='3' stroke='CLR' stroke-width='1.7'/><path d='M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5' stroke='CLR' stroke-width='1.7'/><path d='M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3' stroke='CLR' stroke-width='1.7'/></svg>",
    "clock": "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><circle cx='12' cy='12' r='9' stroke='CLR' stroke-width='1.7'/><polyline points='12 6.5 12 12 16 14.5' stroke='CLR' stroke-width='1.7' stroke-linecap='round'/></svg>",
    # file type icons
    "pdf":   "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' stroke='CLR' stroke-width='1.8' fill='none'/><polyline points='14 2 14 8 20 8' stroke='CLR' stroke-width='1.8'/><line x1='8' y1='13' x2='16' y2='13' stroke='CLR' stroke-width='1.5'/><line x1='8' y1='17' x2='16' y2='17' stroke='CLR' stroke-width='1.5'/></svg>",
    "docx":  "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' stroke='CLR' stroke-width='1.8' fill='none'/><polyline points='14 2 14 8 20 8' stroke='CLR' stroke-width='1.8'/><line x1='8' y1='12' x2='16' y2='12' stroke='CLR' stroke-width='1.4'/><line x1='8' y1='15' x2='16' y2='15' stroke='CLR' stroke-width='1.4'/><line x1='8' y1='18' x2='13' y2='18' stroke='CLR' stroke-width='1.4'/></svg>",
    "xlsx":  "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><rect x='3' y='3' width='18' height='18' rx='2' stroke='CLR' stroke-width='1.8' fill='none'/><line x1='3' y1='9' x2='21' y2='9' stroke='CLR' stroke-width='1.4'/><line x1='3' y1='15' x2='21' y2='15' stroke='CLR' stroke-width='1.4'/><line x1='9' y1='3' x2='9' y2='21' stroke='CLR' stroke-width='1.4'/></svg>",
    "py":    "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><polyline points='16 18 22 12 16 6' stroke='CLR' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/><polyline points='8 6 2 12 8 18' stroke='CLR' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "png":   "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><rect x='3' y='3' width='18' height='18' rx='2' stroke='CLR' stroke-width='1.8' fill='none'/><circle cx='8.5' cy='8.5' r='1.5' stroke='CLR' stroke-width='1.4' fill='none'/><polyline points='21 15 16 10 5 21' stroke='CLR' stroke-width='1.5'/></svg>",
    "mp4":   "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><rect x='2' y='4' width='15' height='16' rx='2' stroke='CLR' stroke-width='1.8' fill='none'/><polyline points='17 8 22 5 22 19 17 16' stroke='CLR' stroke-width='1.8'/></svg>",
    "file":  "<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' stroke='CLR' stroke-width='1.8' fill='none'/><polyline points='14 2 14 8 20 8' stroke='CLR' stroke-width='1.8'/></svg>",
}

_EXT_COLOR = {
    "pdf": "#F87171", "docx": "#60A5FA", "doc": "#60A5FA",
    "xlsx": "#34D399", "xls": "#34D399", "csv": "#34D399",
    "py": "#FBBF24", "js": "#FBBF24", "ts": "#38BDF8",
    "png": "#A78BFA", "jpg": "#A78BFA", "jpeg": "#A78BFA",
    "mp4": "#F472B6", "mp3": "#F472B6",
    "pptx": "#FB923C", "txt": "#CBD5E1",
}

def _ext_color(path: str) -> str:
    return _EXT_COLOR.get(Path(path).suffix.lower().lstrip("."), "#A78BFA")

def _ext_svg_key(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return ext if ext in _SVG else "file"

def _fmt_size(b: int) -> str:
    if b == 0: return "0 B"
    if b < 1024: return f"{b} B"
    if b < 1_048_576: return f"{b/1024:.1f} KB"
    if b < 1_073_741_824: return f"{b/1_048_576:.1f} MB"
    return f"{b/1_073_741_824:.2f} GB"

_TOTAL_BYTES = 1_099_511_627_776  # 1 TB


# ── Donut widget (conservado del original) ────────────────────────────
class _DonutWidget(QWidget):
    def __init__(self, accent: str = "#9D5EF0", parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._track  = QColor("#2D1F52")
        self._pct    = 0.0
        self._target = 0.0
        self.setFixedSize(80, 80)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._step)

    def set_pct(self, pct: float, animate: bool = True):
        self._target = max(0.0, min(pct, 100.0))
        if animate: self._timer.start()
        else:
            self._pct = self._target
            self.update()

    def _step(self):
        diff = self._target - self._pct
        if abs(diff) < 0.3:
            self._pct = self._target
            self._timer.stop()
        else:
            self._pct += diff * 0.12
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        m = 8
        rf = self.rect().adjusted(m, m, -m, -m)
        sw = 10
        pen_t = QPen(self._track, sw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_t)
        p.drawArc(rf, 0, 360 * 16)
        if self._pct > 0:
            w, h = self.width(), self.height()
            g = QConicalGradient(w/2, h/2, 90)
            g.setColorAt(0.0, QColor("#B07EF5"))
            g.setColorAt(1.0, QColor("#6D5CE8"))
            pen_f = QPen(QBrush(g), sw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen_f)
            p.drawArc(rf, 90*16, -int(self._pct/100*360*16))
        p.end()


# ── Helpers de construcción de widgets ───────────────────────────────
def _glass_card(purple: bool = False) -> tuple[QWidget, QVBoxLayout]:
    """Crea una card glass con línea superior y retorna (widget, layout)."""
    card = QWidget()
    card.setObjectName("glass_card")
    if purple:
        card.setStyleSheet("""
            QWidget#glass_card {
                background: rgba(124,58,237,0.09);
                border: 0.5px solid rgba(124,58,237,0.25);
                border-radius: 14px;
            }
        """)
    else:
        card.setStyleSheet("""
            QWidget#glass_card {
                background: rgba(255,255,255,0.03);
                border: 0.5px solid rgba(255,255,255,0.09);
                border-radius: 14px;
            }
        """)
    vl = QVBoxLayout(card)
    vl.setContentsMargins(18, 16, 18, 16)
    vl.setSpacing(0)
    return card, vl


def _card_header(svg_key: str, label: str, color: str = "#A78BFA",
                 right_widget: QWidget = None) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    hl = QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    ic_bg = QWidget()
    ic_bg.setFixedSize(32, 32)
    ic_bg.setStyleSheet(f"""
        background: rgba(167,139,250,0.12);
        border: 0.5px solid rgba(167,139,250,0.22);
        border-radius: 9px;
    """)
    ic_lbl = QLabel(ic_bg)
    ic_lbl.setGeometry(7, 7, 18, 18)
    ic_lbl.setPixmap(_svg_px(_SVG[svg_key], color, 18))
    ic_lbl.setStyleSheet("background: transparent;")
    hl.addWidget(ic_bg)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {C.TEXT}; background: transparent;")
    hl.addWidget(lbl)
    hl.addStretch()
    if right_widget:
        hl.addWidget(right_widget)
    return w


def _top_line(purple: bool = False) -> QWidget:
    """Línea degradada superior de la card."""
    line = QFrame()
    line.setFixedHeight(2)
    if purple:
        line.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 transparent, stop:0.5 #A78BFA, stop:1 transparent);
            border: none; border-radius: 1px;
        """)
    else:
        line.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 transparent, stop:0.5 rgba(255,255,255,0.15), stop:1 transparent);
            border: none; border-radius: 1px;
        """)
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    hl = QHBoxLayout(w)
    hl.setContentsMargins(20, 0, 20, 0)
    hl.addWidget(line)
    return w


# ══════════════════════════════════════════════════════════════════════
# PÁGINA RESUMEN
# ══════════════════════════════════════════════════════════════════════

class ResumenPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        # Refs a labels que se actualizan en refresh()
        self._lbl_files:    QLabel | None = None
        self._lbl_tags:     QLabel | None = None
        self._lbl_untagged: QLabel | None = None
        self._donut:        _DonutWidget | None = None
        self._lbl_used:     QLabel | None = None
        self._lbl_pct:      QLabel | None = None
        self._lbl_free:     QLabel | None = None
        self._bars:         dict = {}   # ext -> (bar_fill, lbl_size)
        self._recent_vl:    QVBoxLayout | None = None
        self._build()

    # ── construcción ─────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(40, 32, 40, 40)
        bv.setSpacing(0)

        # ── Header ───────────────────────────────────────────────
        bv.addLayout(self._build_header())
        bv.addSpacing(20)

        # Separador glow
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 transparent, stop:0.15 #7C3AED,
                stop:0.85 #7C3AED, stop:1 transparent);
            border: none;
        """)
        bv.addWidget(sep)
        bv.addSpacing(20)

        # ── 3 stat cards ─────────────────────────────────────────
        bv.addLayout(self._build_stats_row())
        bv.addSpacing(14)

        # ── 2 cards grandes ──────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        bottom.addWidget(self._build_space_card(), 1)
        bottom.addWidget(self._build_recent_card(), 1)
        bv.addLayout(bottom)
        bv.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll)

    def _build_header(self) -> QHBoxLayout:
        hl = QHBoxLayout()
        hl.setSpacing(0)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title = QLabel("Resumen")
        title.setObjectName("page_title")
        title_col.addWidget(title)
        tagline = QLabel("Vista general de tu biblioteca de archivos")
        tagline.setStyleSheet(f"font-size: 13px; color: {C.TEXT3}; background: transparent;")
        title_col.addWidget(tagline)
        hl.addLayout(title_col)
        hl.addStretch()

        # Alerta papelera (badge rojo) + fecha
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight)

        date_lbl = QLabel(datetime.now().strftime("%A, %d %b %Y"))
        date_lbl.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(date_lbl)

        self._trash_badge = QPushButton("🗑  10 en papelera · vencen en 20d")
        self._trash_badge.setFixedHeight(30)
        self._trash_badge.setStyleSheet("""
            QPushButton {
                background: rgba(248,113,113,0.08);
                border: 0.5px solid rgba(248,113,113,0.22);
                border-radius: 8px;
                color: #F87171;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(248,113,113,0.14);
            }
        """)
        right_col.addWidget(self._trash_badge)
        hl.addLayout(right_col)
        return hl

    def _build_stats_row(self) -> QHBoxLayout:
        hl = QHBoxLayout()
        hl.setSpacing(14)

        cfg = [
            ("files",    "#A78BFA", "ARCHIVOS",          "—", "+3 esta semana",   "_lbl_files"),
            ("tags",     "#34D399", "ETIQUETAS",          "—", "8 tipos distintos", "_lbl_tags"),
            ("untagged", "#FBBF24", "SIN ETIQUETA",       "—", "Pendientes de organizar", "_lbl_untagged"),
        ]

        for svg_key, color, label, val, sub, attr in cfg:
            card, vl = _glass_card(purple=False)
            vl.addWidget(_top_line(purple=False))
            vl.addSpacing(12)

            # Label superior
            lbl_title = QLabel(label)
            lbl_title.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; letter-spacing: .8px; background: transparent;")
            vl.addWidget(lbl_title)
            vl.addSpacing(4)

            # Número
            lbl_val = QLabel(val)
            lbl_val.setStyleSheet(f"font-size: 28px; font-weight: 500; color: {C.TEXT}; background: transparent; line-height: 1;")
            vl.addWidget(lbl_val)
            vl.addSpacing(2)

            # Sub
            lbl_sub = QLabel(sub)
            lbl_sub.setStyleSheet(f"font-size: 10px; color: {color}; background: transparent;")
            vl.addWidget(lbl_sub)
            vl.addSpacing(12)

            setattr(self, attr, lbl_val)
            hl.addWidget(card, 1)

        return hl

    def _build_space_card(self) -> QWidget:
        card, vl = _glass_card(purple=True)
        vl.addWidget(_top_line(purple=True))
        vl.addSpacing(14)

        # Header
        pct_badge = QLabel("13.9% usado")
        pct_badge.setStyleSheet("""
            font-size: 10px; color: #A78BFA;
            background: rgba(124,58,237,0.2);
            border: 0.5px solid rgba(167,139,250,0.3);
            border-radius: 99px; padding: 2px 8px;
        """)
        self._lbl_pct_badge = pct_badge
        vl.addWidget(_card_header("db", "Espacio usado", "#A78BFA", pct_badge))
        vl.addSpacing(16)

        # Donut + datos
        center = QHBoxLayout()
        center.setSpacing(14)
        center.setContentsMargins(0, 0, 0, 0)

        self._donut = _DonutWidget(accent="#9D5EF0")
        center.addWidget(self._donut, 0, Qt.AlignmentFlag.AlignTop)

        data_col = QVBoxLayout()
        data_col.setSpacing(0)
        data_col.setContentsMargins(0, 2, 0, 0)

        for attr, label, val in [
            ("_lbl_used", "Ocupado", "— GB"),
            ("_lbl_free", "Libre",   "— GB"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(6)
            dot = QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"""
                background: {'#7C3AED' if attr == '_lbl_used' else 'rgba(255,255,255,0.15)'};
                border-radius: 3px;
            """)
            lbl_label = QLabel(label)
            lbl_label.setStyleSheet(f"font-size: 11px; color: {C.TEXT3}; background: transparent;")
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {C.TEXT}; background: transparent;")
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(lbl_label)
            row.addStretch()
            row.addWidget(lbl_v)
            data_col.addLayout(row)
            if attr == "_lbl_used":
                # barra ocupado
                bar_w = QWidget()
                bar_w.setFixedHeight(3)
                bar_w.setStyleSheet("background: rgba(255,255,255,0.06); border-radius: 2px;")
                bar_fill = QWidget(bar_w)
                bar_fill.setFixedHeight(3)
                bar_fill.setStyleSheet("background: #7C3AED; border-radius: 2px;")
                bar_fill.setFixedWidth(0)
                self._bar_used = bar_fill
                self._bar_used_track = bar_w
                data_col.addWidget(bar_w)
                data_col.addSpacing(8)
            else:
                data_col.addSpacing(4)
            setattr(self, attr, lbl_v)

        center.addLayout(data_col, 1)
        vl.addLayout(center)
        vl.addSpacing(14)

        # Separador
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(167,139,250,0.12); border: none;")
        vl.addWidget(sep)
        vl.addSpacing(12)

        # Distribución por tipo
        dist_lbl = QLabel("DISTRIBUCIÓN POR TIPO")
        dist_lbl.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; letter-spacing: .6px; background: transparent;")
        vl.addWidget(dist_lbl)
        vl.addSpacing(8)

        self._bars = {}
        for ext, color, pct_demo, size_demo in [
            ("PDF",  "#F87171", 38, "54 GB"),
            ("MP4",  "#F472B6", 28, "40 GB"),
            ("DOCX", "#60A5FA", 18, "26 GB"),
            ("Otros","#A78BFA", 10, "22 GB"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            ext_lbl = QLabel(ext)
            ext_lbl.setFixedWidth(32)
            ext_lbl.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; background: transparent;")
            bar_track = QWidget()
            bar_track.setFixedHeight(3)
            bar_track.setStyleSheet("background: rgba(255,255,255,0.06); border-radius: 2px;")
            bar_fill = QWidget(bar_track)
            bar_fill.setFixedHeight(3)
            bar_fill.setStyleSheet(f"background: {color}; border-radius: 2px;")
            bar_fill.setFixedWidth(0)
            size_lbl = QLabel(size_demo)
            size_lbl.setFixedWidth(36)
            size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            size_lbl.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; background: transparent;")
            row.addWidget(ext_lbl)
            row.addWidget(bar_track, 1)
            row.addWidget(size_lbl)
            vl.addLayout(row)
            vl.addSpacing(5)
            self._bars[ext] = (bar_fill, bar_track, pct_demo, color)

        # Nota al pie
        footer = QLabel("1 TB total · SSD principal")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; background: transparent;")
        vl.addSpacing(8)
        vl.addWidget(footer)
        vl.addSpacing(4)
        return card

    def _build_recent_card(self) -> QWidget:
        card, vl = _glass_card(purple=False)
        vl.addWidget(_top_line(purple=False))
        vl.addSpacing(14)

        # Header con "Ver todos →"
        see_all = QPushButton("Ver todos →")
        see_all.setFlat(True)
        see_all.setStyleSheet(f"font-size: 11px; color: {C.PURPLE3}; background: transparent; border: none;")
        vl.addWidget(_card_header("clock", "Archivos recientes", "#A78BFA", see_all))
        vl.addSpacing(12)

        # Lista de archivos (se popula en refresh)
        self._recent_vl = QVBoxLayout()
        self._recent_vl.setSpacing(0)
        self._recent_vl.setContentsMargins(0, 0, 0, 0)
        vl.addLayout(self._recent_vl)
        vl.addStretch()
        return card

    def _make_file_row(self, name: str, path: str, meta: str, size: str, last: bool) -> QWidget:
        color   = _ext_color(path)
        svg_key = _ext_svg_key(path)

        w = QWidget()
        w.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 7, 0, 7)
        hl.setSpacing(10)

        # Ícono con color de tipo
        ic_bg = QWidget()
        ic_bg.setFixedSize(32, 32)
        ic_bg.setStyleSheet(f"""
            background: {color}18;
            border: 0.5px solid {color}30;
            border-radius: 8px;
        """)
        ic_lbl = QLabel(ic_bg)
        ic_lbl.setGeometry(7, 7, 18, 18)
        ic_lbl.setPixmap(_svg_px(_SVG[svg_key], color, 18))
        ic_lbl.setStyleSheet("background: transparent;")
        hl.addWidget(ic_bg)

        # Nombre + meta
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        nm = QLabel(name if len(name) <= 26 else name[:24] + "…")
        nm.setToolTip(name)
        nm.setStyleSheet(f"font-size: 12px; color: {C.TEXT}; background: transparent;")
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; background: transparent;")
        text_col.addWidget(nm)
        text_col.addWidget(meta_lbl)
        hl.addLayout(text_col, 1)

        # Tamaño
        sz = QLabel(size)
        sz.setStyleSheet(f"font-size: 10px; color: {C.TEXT3}; background: transparent;")
        hl.addWidget(sz)

        # Borde inferior excepto en el último
        if not last:
            wrapper = QWidget()
            wrapper.setStyleSheet("background: transparent;")
            outer = QVBoxLayout(wrapper)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            outer.addWidget(w)
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: rgba(255,255,255,0.05); border: none;")
            outer.addWidget(sep)
            return wrapper
        return w

    # ── actualización de datos ────────────────────────────────────────

    def refresh(self):
        try:
            stats = db.get_stats()
            total   = stats.get("total_files", 0)
            tags    = stats.get("total_tags", 0)
            size_b  = stats.get("total_size_bytes", 0)
            untagged = stats.get("files_without_tags", 0)

            # Stats arriba
            if self._lbl_files:
                self._lbl_files.setText(f"{total:,}".replace(",", "."))
            if self._lbl_tags:
                self._lbl_tags.setText(f"{tags:,}".replace(",", "."))
            if self._lbl_untagged:
                self._lbl_untagged.setText(str(untagged))

            # Papelera badge
            try:
                trash = db.get_trash_stats()
                n = trash.get("total", 0)
                if n > 0:
                    self._trash_badge.setText(f"🗑  {n} en papelera")
                    self._trash_badge.show()
                else:
                    self._trash_badge.hide()
            except Exception:
                pass

            # Espacio usado
            pct = min(size_b / _TOTAL_BYTES * 100, 100.0)
            used_gb = size_b / 1_073_741_824
            free_gb = (_TOTAL_BYTES - size_b) / 1_073_741_824

            if self._donut:
                self._donut.set_pct(pct)
            if self._lbl_used:
                self._lbl_used.setText(f"{used_gb:.2f} GB")
            if self._lbl_free:
                self._lbl_free.setText(f"{free_gb:.1f} GB")
            if self._lbl_pct_badge:
                self._lbl_pct_badge.setText(f"{pct:.1f}% usado")

            # Actualizar barras de distribución con animación de ancho
            QTimer.singleShot(50, self._update_bars)

            # Archivos recientes
            try:
                recents = db.list_all_files()[:6]
                self._render_recent(recents)
            except Exception:
                pass

        except Exception as e:
            logger.exception(f"Error actualizando resumen: {e}")

    def _update_bars(self):
        # Barra ocupado
        if hasattr(self, "_bar_used_track") and self._bar_used_track:
            track_w = self._bar_used_track.width()
            try:
                stats = db.get_stats()
                size_b = stats.get("total_size_bytes", 0)
                pct = min(size_b / _TOTAL_BYTES, 1.0)
                self._bar_used.setFixedWidth(max(0, int(track_w * pct)))
            except Exception:
                pass

        # Barras de distribución (estáticas por ahora, porcentajes demo)
        for ext, (fill, track, pct_demo, _) in self._bars.items():
            w = max(0, int(track.width() * pct_demo / 100))
            fill.setFixedWidth(w)

    def _render_recent(self, files: list):
        if not self._recent_vl:
            return
        for i in reversed(range(self._recent_vl.count())):
            item = self._recent_vl.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for idx, f in enumerate(files):
            name = f.get("name", "")
            path = f.get("path", "")
            size_b = f.get("size", 0) or 0
            ext = Path(path).suffix.upper().lstrip(".")
            updated = f.get("updated_at", "")
            # Formatear fecha relativa simple
            try:
                from datetime import timezone
                dt = datetime.fromisoformat(str(updated))
                diff = (datetime.now(timezone.utc) - dt).days
                if diff == 0: ago = "hoy"
                elif diff == 1: ago = "ayer"
                else: ago = f"hace {diff}d"
            except Exception:
                ago = ""
            meta = f"{ext} · {ago}" if ext else ago
            size_str = _fmt_size(size_b)
            row = self._make_file_row(name, path, meta, size_str, idx == len(files) - 1)
            self._recent_vl.addWidget(row)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(10, self._update_bars)
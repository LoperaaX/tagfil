"""
pages/papelera.py — Página de Papelera con grid de tarjetas y estadísticas.
"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QByteArray, QRectF
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)

import database as db
from config import get_logger
from theme import C

logger = get_logger(__name__)

# ── SVG data por tipo de archivo ──────────────────────────────────────
_SVG_FILE_GENERIC = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
        stroke="COLOR" stroke-width="1.8" fill="none"/>
  <polyline points="14 2 14 8 20 8" stroke="COLOR" stroke-width="1.8" fill="none"/>
</svg>"""

_SVG_PDF = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
        stroke="COLOR" stroke-width="1.8" fill="none"/>
  <polyline points="14 2 14 8 20 8" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <line x1="8" y1="13" x2="16" y2="13" stroke="COLOR" stroke-width="1.5"/>
  <line x1="8" y1="17" x2="16" y2="17" stroke="COLOR" stroke-width="1.5"/>
  <line x1="8" y1="9"  x2="11" y2="9"  stroke="COLOR" stroke-width="1.5"/>
</svg>"""

_SVG_DOC = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
        stroke="COLOR" stroke-width="1.8" fill="none"/>
  <polyline points="14 2 14 8 20 8" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <line x1="8" y1="12" x2="16" y2="12" stroke="COLOR" stroke-width="1.4"/>
  <line x1="8" y1="15" x2="16" y2="15" stroke="COLOR" stroke-width="1.4"/>
  <line x1="8" y1="18" x2="13" y2="18" stroke="COLOR" stroke-width="1.4"/>
</svg>"""

_SVG_SHEET = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="3" width="18" height="18" rx="2" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <line x1="3" y1="9"  x2="21" y2="9"  stroke="COLOR" stroke-width="1.4"/>
  <line x1="3" y1="15" x2="21" y2="15" stroke="COLOR" stroke-width="1.4"/>
  <line x1="9" y1="3"  x2="9"  y2="21" stroke="COLOR" stroke-width="1.4"/>
</svg>"""

_SVG_SLIDE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="4" width="20" height="14" rx="2" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <line x1="12" y1="18" x2="12" y2="22" stroke="COLOR" stroke-width="1.8"/>
  <line x1="8"  y1="22" x2="16" y2="22" stroke="COLOR" stroke-width="1.8"/>
  <rect x="6" y="8" width="5" height="4" rx="1" stroke="COLOR" stroke-width="1.3" fill="none"/>
  <line x1="13" y1="9"  x2="18" y2="9"  stroke="COLOR" stroke-width="1.3"/>
  <line x1="13" y1="12" x2="17" y2="12" stroke="COLOR" stroke-width="1.3"/>
</svg>"""

_SVG_IMAGE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="3" width="18" height="18" rx="2" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <circle cx="8.5" cy="8.5" r="1.5" stroke="COLOR" stroke-width="1.4" fill="none"/>
  <polyline points="21 15 16 10 5 21" stroke="COLOR" stroke-width="1.5" fill="none"/>
</svg>"""

_SVG_CODE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <polyline points="16 18 22 12 16 6" stroke="COLOR" stroke-width="1.8" fill="none"
            stroke-linecap="round" stroke-linejoin="round"/>
  <polyline points="8 6 2 12 8 18"   stroke="COLOR" stroke-width="1.8" fill="none"
            stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_SVG_ARCHIVE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <polyline points="21 8 21 21 3 21 3 8" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <rect x="1" y="3" width="22" height="5" rx="1" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <line x1="10" y1="12" x2="14" y2="12" stroke="COLOR" stroke-width="1.8"/>
</svg>"""

_SVG_VIDEO = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="4" width="15" height="16" rx="2" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <polyline points="17 8 22 5 22 19 17 16" stroke="COLOR" stroke-width="1.8" fill="none"/>
</svg>"""

_SVG_AUDIO = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M9 18V5l12-2v13" stroke="COLOR" stroke-width="1.8" fill="none"
        stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="6"  cy="18" r="3" stroke="COLOR" stroke-width="1.6" fill="none"/>
  <circle cx="18" cy="16" r="3" stroke="COLOR" stroke-width="1.6" fill="none"/>
</svg>"""

_SVG_EXE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="3" width="18" height="18" rx="2" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <path d="M9 9l6 6M15 9l-6 6" stroke="COLOR" stroke-width="1.8"
        stroke-linecap="round"/>
</svg>"""

_SVG_FOLDER = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
        stroke="COLOR" stroke-width="1.8" fill="none"/>
</svg>"""

_SVG_TXT = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
        stroke="COLOR" stroke-width="1.8" fill="none"/>
  <polyline points="14 2 14 8 20 8" stroke="COLOR" stroke-width="1.8" fill="none"/>
  <line x1="8" y1="13" x2="16" y2="13" stroke="COLOR" stroke-width="1.4"/>
  <line x1="8" y1="17" x2="12" y2="17" stroke="COLOR" stroke-width="1.4"/>
</svg>"""


def _svg_pixmap(svg_template: str, color: str, size: int = 40) -> QPixmap:
    """Renderiza un SVG string (con placeholder COLOR) a QPixmap."""
    svg_data = svg_template.replace("COLOR", color)
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap



class PapeleraPage(QWidget):
    """
    Página de Papelera: barra de alerta roja, grid de tarjetas con
    miniaturas de tipo de archivo, y panel de estadísticas lateral.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ── construcción del layout ────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Cuerpo: grid + panel de estadísticas
        body = QHBoxLayout()
        body.setContentsMargins(20, 20, 20, 20)
        body.setSpacing(18)

        # ─ Área izquierda: alerta + scroll con grid ───────────────
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(14)

        # Banner de alerta dentro del área del grid
        left_col.addWidget(self._make_alert_bar())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
            QScrollBar:vertical {{
                background: {C.BG3};
                width: 5px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER2};
                border-radius: 3px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C.PURPLE};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; background: none; }}
        """)

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(4, 4, 4, 4)
        self._grid.setSpacing(14)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)
        self._grid.setColumnStretch(2, 1)

        scroll.setWidget(self._grid_container)
        left_col.addWidget(scroll, 1)
        body.addLayout(left_col, 1)

        # ─ Panel de estadísticas (derecha) ────────────────────────
        body.addWidget(self._make_stats_panel())

        root.addLayout(body, 1)

    def _make_alert_bar(self, days_used: int = 20, days_total: int = 30) -> QWidget:
        """
        Banner estilo opción A+D:
        borde izquierdo rojo · ícono · título/subtexto con días · botón · barra de tiempo
        """
        days_left = days_total - days_used
        ratio     = days_used / days_total  # 0.0 → 1.0

        # Color de la barra: verde → ámbar → rojo según avance
        if ratio < 0.5:
            bar_color = "#22C55E"
        elif ratio < 0.75:
            bar_color = "#F97316"
        else:
            bar_color = "#E24B4A"

        # Contenedor externo con borde izquierdo rojo
        outer = QWidget()
        outer.setStyleSheet(f"""
            QWidget#alert_bar {{
                background: {C.BG2};
                border: 1px solid {C.BORDER};
                border-left: 3px solid #E24B4A;
                border-radius: 0px;
            }}
        """)
        outer.setObjectName("alert_bar")

        vl_outer = QVBoxLayout(outer)
        vl_outer.setContentsMargins(0, 0, 0, 0)
        vl_outer.setSpacing(0)

        # ── Fila superior: ícono + texto + botón ──────────────────
        top_row = QWidget()
        top_row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(top_row)
        hl.setContentsMargins(20, 14, 20, 8)
        hl.setSpacing(14)

        # Ícono SVG de basura
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(28, 28)
        ic_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic_lbl.setStyleSheet("background: transparent; border: none;")
        _SVG_TRASH = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <polyline points="3 6 5 6 21 6" stroke="COLOR" stroke-width="2" stroke-linecap="round"/>
          <path d="M19 6l-1 14H6L5 6" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M10 11v6M14 11v6" stroke="COLOR" stroke-width="2" stroke-linecap="round"/>
          <path d="M9 6V4h6v2" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""
        ic_lbl.setPixmap(_svg_pixmap(_SVG_TRASH, "#E24B4A", size=24))
        hl.addWidget(ic_lbl)

        # Texto
        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        txt_col.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel("Papelera · archivos en espera")
        title_lbl.setStyleSheet(f"""
            font-size: 13px; font-weight: 700;
            color: {C.TEXT}; background: transparent;
        """)
        txt_col.addWidget(title_lbl)

        body_lbl = QLabel(
            f"Se eliminarán permanentemente en <b style='color:#E24B4A;'>{days_left} días</b>"
            f" · Verifica antes de vaciar"
        )
        body_lbl.setTextFormat(Qt.TextFormat.RichText)
        body_lbl.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        txt_col.addWidget(body_lbl)
        hl.addLayout(txt_col, 1)

        # Botón vaciar
        self._btn_vaciar = QPushButton("  Vaciar ahora")
        self._btn_vaciar.setFixedHeight(36)
        self._btn_vaciar.setMinimumWidth(140)
        self._btn_vaciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_vaciar.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #E24B4A;
                font-size: 12px;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #E24B4A;
                padding: 0 16px;
                letter-spacing: 0.2px;
            }
            QPushButton:hover {
                background: rgba(226,75,74,0.12);
                border-color: #F09595;
                color: #F09595;
            }
            QPushButton:pressed {
                background: rgba(226,75,74,0.22);
            }
        """)
        self._btn_vaciar.clicked.connect(self._on_vaciar)
        hl.addWidget(self._btn_vaciar)

        vl_outer.addWidget(top_row)

        # ── Fila inferior: barra de progreso de tiempo ────────────
        bar_row = QWidget()
        bar_row.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bar_row)
        bl.setContentsMargins(62, 0, 20, 12)   # alineado bajo el texto
        bl.setSpacing(10)

        # Track de la barra
        track = QWidget()
        track.setFixedHeight(4)
        track.setStyleSheet(f"""
            background: {C.BG4};
            border-radius: 2px;
            border: 1px solid {C.BORDER};
        """)
        # Relleno interior
        fill = QWidget(track)
        fill.setFixedHeight(4)
        fill.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #22C55E, stop:0.5 #F97316, stop:1 #E24B4A);
            border-radius: 2px;
        """)
        # El ancho del fill se ajusta en showEvent
        self._progress_track = track
        self._progress_fill  = fill
        self._progress_ratio = ratio

        bl.addWidget(track, 1)

        day_lbl = QLabel(f"día {days_used} / {days_total}")
        day_lbl.setStyleSheet(f"font-size: 11px; color: {C.TEXT3}; background: transparent;")
        bl.addWidget(day_lbl)

        vl_outer.addWidget(bar_row)

        # Ajustar fill al mostrarse por primera vez
        def _update_fill():
            w = max(4, int(track.width() * ratio))
            fill.setFixedWidth(w)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, _update_fill)
        # También al redimensionar
        original_resize = outer.resizeEvent
        def _on_resize(e, t=track, f=fill, r=ratio, orig=original_resize):
            orig(e)
            f.setFixedWidth(max(4, int(t.width() * r)))
        outer.resizeEvent = _on_resize

        return outer

    def _make_stats_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(245)
        panel.setStyleSheet(f"""
            QWidget#stats_panel {{
                background: {C.BG2};
                border-radius: 16px;
                border: 1px solid {C.BORDER};
            }}
        """)
        panel.setObjectName("stats_panel")

        vl = QVBoxLayout(panel)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(0)

        # ── Título del panel ──────────────────────────────────────
        title = QLabel("Estadísticas de la Papelera")
        title.setStyleSheet(f"""
            font-size: 14px; font-weight: 800;
            color: {C.TEXT}; background: transparent;
        """)
        vl.addWidget(title)
        vl.addSpacing(4)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C.BORDER}; border: none;")
        vl.addWidget(sep)
        vl.addSpacing(10)

        sub = QLabel("Papelera en Cifras")
        sub.setStyleSheet(f"""
            font-size: 10px; font-weight: 700;
            color: {C.TEXT3}; letter-spacing: 1.2px;
            background: transparent;
            text-transform: uppercase;
        """)
        vl.addWidget(sub)

        # ── Sub-contador dinámico ─────────────────────────────────
        self._stats_count_lbl = QLabel("Sin registros")
        self._stats_count_lbl.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        vl.addWidget(self._stats_count_lbl)
        vl.addSpacing(12)

        # ── Filas de estadísticas ─────────────────────────────────
        self._stat_rows: dict[str, tuple[QWidget, QLabel]] = {}
        stats_defs = [
            ("total",     "Registros Totales",   C.PURPLE),
            ("archivos",  "Archivos",             C.PURPLE),
            ("carpetas",  "Carpetas",             "#F97316"),
            ("espacio",   "Espacio Recuperable",  C.RED),
            ("fecha",     "Fecha más antigua",    C.TEXT3),
        ]
        for key, label, bar_color in stats_defs:
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            rl = QVBoxLayout(row_w)
            rl.setContentsMargins(0, 8, 0, 8)
            rl.setSpacing(6)

            # Etiqueta + valor en la misma fila
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"font-size: 12px; color: {C.TEXT2}; background: transparent;"
            )
            top_row.addWidget(lbl, 1)

            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 800; color: {C.TEXT}; background: transparent;"
            )
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top_row.addWidget(val_lbl)
            rl.addLayout(top_row)

            # Barra de progreso
            prog_bg = QWidget()
            prog_bg.setFixedHeight(4)
            prog_bg.setStyleSheet(f"background: {C.BG4}; border-radius: 2px;")
            prog_inner = QWidget(prog_bg)
            prog_inner.setFixedHeight(4)
            prog_inner.setStyleSheet(
                f"background: {bar_color}; border-radius: 2px;"
            )
            prog_inner.setFixedWidth(4)
            rl.addWidget(prog_bg)

            self._stat_rows[key] = (prog_bg, val_lbl)
            vl.addWidget(row_w)

            if key != "fecha":
                row_sep = QFrame()
                row_sep.setFrameShape(QFrame.Shape.HLine)
                row_sep.setFixedHeight(1)
                row_sep.setStyleSheet(f"background: {C.BORDER}; border: none;")
                vl.addWidget(row_sep)

        vl.addStretch()
        return panel

    # ── helpers de tarjeta ─────────────────────────────────────────────

    def _ext_color(self, path: str, is_folder: bool = False) -> tuple[str, str, str]:
        """Devuelve (bg_color, text_color, accent_color) según tipo."""
        if is_folder:
            return "#1C1207", "#F97316", "#F9731644"
        ext = Path(path).suffix.lower() if path else ""
        if ext == ".pdf":
            return "#2D0000", "#EF4444", "#EF444444"
        if ext in (".docx", ".doc"):
            return "#0D1B3E", "#3B82F6", "#3B82F644"
        if ext in (".xlsx", ".xls", ".csv"):
            return "#032211", "#22C55E", "#22C55E44"
        if ext in (".pptx",):
            return "#2C0E00", "#F97316", "#F9731644"
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            return "#1A0A3B", "#A855F7", "#A855F744"
        if ext in (".zip", ".rar", ".7z"):
            return "#161310", "#78716C", "#78716C44"
        if ext in (".py", ".js", ".ts", ".html", ".css"):
            return "#0A1A10", "#34D399", "#34D39944"
        return C.PURPLE_DIM, C.PURPLE3, C.PURPLE_GLOW

    def _ext_badge(self, path: str, is_folder: bool = False) -> tuple[str, str]:
        """Devuelve (texto_badge, svg_template) según tipo."""
        if is_folder:
            return "DIR", _SVG_FOLDER
        ext = Path(path).suffix.lower() if path else ""
        mapping = {
            ".pdf":  ("PDF",  _SVG_PDF),
            ".docx": ("DOCX", _SVG_DOC),
            ".doc":  ("DOC",  _SVG_DOC),
            ".xlsx": ("XLSX", _SVG_SHEET),
            ".xls":  ("XLS",  _SVG_SHEET),
            ".csv":  ("CSV",  _SVG_SHEET),
            ".pptx": ("PPTX", _SVG_SLIDE),
            ".txt":  ("TXT",  _SVG_TXT),
            ".py":   ("PY",   _SVG_CODE),
            ".js":   ("JS",   _SVG_CODE),
            ".ts":   ("TS",   _SVG_CODE),
            ".html": ("HTML", _SVG_CODE),
            ".css":  ("CSS",  _SVG_CODE),
            ".jpg":  ("JPG",  _SVG_IMAGE),
            ".jpeg": ("JPG",  _SVG_IMAGE),
            ".png":  ("PNG",  _SVG_IMAGE),
            ".gif":  ("GIF",  _SVG_IMAGE),
            ".webp": ("WEBP", _SVG_IMAGE),
            ".zip":  ("ZIP",  _SVG_ARCHIVE),
            ".rar":  ("RAR",  _SVG_ARCHIVE),
            ".7z":   ("7Z",   _SVG_ARCHIVE),
            ".mp4":  ("MP4",  _SVG_VIDEO),
            ".mov":  ("MOV",  _SVG_VIDEO),
            ".mp3":  ("MP3",  _SVG_AUDIO),
            ".exe":  ("EXE",  _SVG_EXE),
        }
        badge, svg = mapping.get(ext, (ext.lstrip(".").upper()[:4] or "?", _SVG_FILE_GENERIC))
        return badge, svg

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes >= 1_073_741_824:
            return f"{size_bytes / 1_073_741_824:.1f} GB"
        if size_bytes >= 1_048_576:
            return f"{size_bytes / 1_048_576:.1f} MB"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"

    def _make_trash_card(self, record: dict) -> QWidget:
        """Crea una tarjeta premium de elemento eliminado."""
        is_folder = record.get("is_folder", False)
        path      = record.get("path", "")
        bg_col, fg_col, accent = self._ext_color(path, is_folder)
        badge, svg_tmpl         = self._ext_badge(path, is_folder)

        # ── Fecha de eliminación (calcular antes) ─────────────────
        deleted_at = record.get("deleted_at", "")
        if deleted_at:
            try:
                dt = datetime.fromisoformat(str(deleted_at))
                fecha_str = f"Eliminado el {dt.strftime('%d/%m/%Y')}"
            except Exception:
                fecha_str = f"Eliminado el {str(deleted_at)[:10]}"
        else:
            fecha_str = "Fecha desconocida"

        name = record.get("name", "Archivo desconocido")

        # ── Card container ────────────────────────────────────────
        card = QWidget()
        card.setObjectName("trash_card")
        card.setFixedHeight(210)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QWidget#trash_card {{
                background: {C.BG3};
                border: 1px solid {C.BORDER};
                border-radius: 14px;
            }}
            QWidget#trash_card:hover {{
                border-color: {fg_col}66;
                background: {C.BG4};
            }}
        """)

        vl = QVBoxLayout(card)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        # ── Miniatura: ícono+badge izquierda | nombre derecha ────
        thumb = QWidget()
        thumb.setFixedHeight(80)
        thumb.setStyleSheet(f"""
            background: {C.BG3};
            border-radius: 9px;
            border: 1.5px solid {fg_col}55;
        """)
        thumb_hl = QHBoxLayout(thumb)
        thumb_hl.setContentsMargins(12, 0, 14, 0)
        thumb_hl.setSpacing(12)

        # Columna izquierda: SVG + badge
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(3)
        left_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        svg_lbl = QLabel()
        svg_lbl.setFixedSize(36, 36)
        svg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        svg_lbl.setStyleSheet("background: transparent; border: none;")
        pixmap = _svg_pixmap(svg_tmpl, fg_col, size=32)
        svg_lbl.setPixmap(pixmap)
        left_col.addWidget(svg_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        badge_lbl = QLabel(badge)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_lbl.setStyleSheet(f"""
            background: transparent; border: none;
            font-size: 9px; font-weight: 900;
            color: {fg_col}; letter-spacing: 1.5px;
        """)
        left_col.addWidget(badge_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        thumb_hl.addLayout(left_col)

        # Nombre del archivo (derecha, sin separador)
        nm_lbl = QLabel(name if len(name) <= 28 else name[:26] + "…")
        nm_lbl.setToolTip(name)
        nm_lbl.setWordWrap(True)
        nm_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        nm_lbl.setStyleSheet(f"""
            background: transparent; border: none;
            font-size: 12px; font-weight: 700; color: {C.TEXT};
        """)
        thumb_hl.addWidget(nm_lbl, 1)

        vl.addWidget(thumb)

        # ── Fecha ─────────────────────────────────────────────────
        date_lbl = QLabel(fecha_str)
        date_lbl.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        vl.addWidget(date_lbl)

        # ── Botón Restaurar ───────────────────────────────────────
        btn_restaurar = QPushButton("Restaurar")
        btn_restaurar.setFixedHeight(32)
        btn_restaurar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restaurar.setStyleSheet(f"""
            QPushButton {{
                background: {C.PURPLE};
                color: white;
                font-size: 12px;
                font-weight: 700;
                border-radius: 8px;
                border: none;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{ background: {C.PURPLE2}; }}
            QPushButton:pressed {{ background: {C.PURPLE_DIM2}; }}
        """)
        btn_restaurar.clicked.connect(lambda _, r=record: self._on_restore(r))
        vl.addWidget(btn_restaurar)

        # ── Botón Eliminar Permanentemente ────────────────────────
        btn_eliminar = QPushButton("Eliminar Permanentemente")
        btn_eliminar.setFixedHeight(32)
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C.RED};
                font-size: 11px;
                font-weight: 700;
                border-radius: 8px;
                border: 1.5px solid #7F1D1D;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: rgba(239,68,68,0.14);
                border-color: {C.RED};
            }}
            QPushButton:pressed {{ background: rgba(239,68,68,0.22); }}
        """)
        btn_eliminar.clicked.connect(lambda _, r=record: self._on_delete_permanent(r))
        vl.addWidget(btn_eliminar)

        return card

    # ── render del grid ────────────────────────────────────────────────

    def _render_grid(self, items: list[dict]):
        # Limpiar grid
        for i in reversed(range(self._grid.count())):
            w = self._grid.itemAt(i)
            if w and w.widget():
                w.widget().deleteLater()

        if not items:
            empty_w = QWidget()
            empty_w.setStyleSheet("background: transparent;")
            ev = QVBoxLayout(empty_w)
            ev.setAlignment(Qt.AlignmentFlag.AlignCenter)

            ic = QLabel("🗑")
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet("font-size: 48px; background: transparent;")
            ev.addWidget(ic)
            ev.addSpacing(12)

            msg = QLabel("La papelera está vacía")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet(
                f"color: {C.TEXT3}; font-size: 18px; font-weight: 600; background: transparent;"
            )
            ev.addWidget(msg)

            sub = QLabel("Los elementos eliminados aparecerán aquí")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setStyleSheet(
                f"color: {C.TEXT4}; font-size: 13px; background: transparent;"
            )
            ev.addWidget(sub)
            self._grid.addWidget(empty_w, 0, 0, 1, 3)
            return

        COLS = 3
        for i, record in enumerate(items):
            card = self._make_trash_card(record)
            self._grid.addWidget(card, i // COLS, i % COLS)

        # Filler para alinear al tope si la última fila es incompleta
        remainder = len(items) % COLS
        if remainder:
            filler = QWidget()
            filler.setStyleSheet("background: transparent;")
            last_row = len(items) // COLS
            self._grid.addWidget(filler, last_row, remainder, 1, COLS - remainder)

    def _update_stats(self, items: list[dict]):
        total    = len(items)
        archivos = sum(1 for r in items if not r.get("is_folder", False))
        carpetas = total - archivos
        total_bytes = sum(r.get("size", 0) or 0 for r in items)
        espacio_str = self._format_size(total_bytes)

        # Fecha más antigua
        dates = []
        for r in items:
            da = r.get("deleted_at") or r.get("added_at") or ""
            if da:
                try:
                    dates.append(datetime.fromisoformat(str(da)))
                except Exception:
                    pass
        fecha_str = min(dates).strftime("%d/%m/%Y") if dates else "—"

        values = {
            "total":    (str(total),    min(total / max(total, 1), 1.0) if total else 0),
            "archivos": (str(archivos), archivos / max(total, 1) if total else 0),
            "carpetas": (str(carpetas), carpetas / max(total, 1) if total else 0),
            "espacio":  (espacio_str,   min(total_bytes / max(total_bytes, 1_073_741_824), 1.0)),
            "fecha":    (fecha_str,     0.0),
        }

        for key, (val_str, ratio) in values.items():
            prog_bg, val_lbl = self._stat_rows[key]
            val_lbl.setText(val_str)

            # Actualizar barra de progreso interior
            inner = prog_bg.findChild(QWidget)
            if inner:
                w = max(4, int(prog_bg.width() * ratio)) if ratio else 4
                inner.setFixedWidth(w)

        # Sub-contador
        label = f"{total} de {total} registros" if total else "Sin registros"
        if hasattr(self, "_stats_count_lbl"):
            self._stats_count_lbl.setText(label)

    # ── refresh ────────────────────────────────────────────────────────

    def refresh(self):
        try:
            items = db.list_trash()
        except AttributeError:
            items = []
        except Exception as exc:
            logger.exception(f"Error cargando papelera: {exc}")
            items = []
        self._render_grid(items)
        self._update_stats(items)

    # ── acciones ───────────────────────────────────────────────────────

    def _on_vaciar(self):
        try:
            db.empty_trash()
        except AttributeError:
            pass
        except Exception as exc:
            logger.exception(f"Error vaciando papelera: {exc}")
        self.refresh()

    def _on_restore(self, record: dict):
        try:
            db.restore_from_trash(record.get("path"))
        except AttributeError:
            pass
        except Exception as exc:
            logger.exception(f"Error restaurando: {exc}")
        self.refresh()

    def _on_delete_permanent(self, record: dict):
        try:
            db.purge_file(record.get("path"))
        except AttributeError:
            pass
        except Exception as exc:
            logger.exception(f"Error eliminando permanentemente: {exc}")
        self.refresh()
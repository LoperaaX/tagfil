"""
pages/archivos.py — Página "Todos los archivos" con grid y filtros.
"""
from collections import Counter
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import database as db
from config import get_logger, SEARCH_DEBOUNCE_MS
from theme import C
from widgets.ui_helpers import GlowCard
from widgets.import_worker import FolderImportWorker, FolderScanWorker
from widgets.search_worker import SearchWorker

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# SVG ICONS — uno por tipo de archivo (stroke, sin fill)
# ══════════════════════════════════════════════════════════════════════

_SVG_PDF = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <line x1="9" y1="13" x2="15" y2="13"/>
  <line x1="9" y1="17" x2="15" y2="17"/>
  <line x1="9" y1="9"  x2="11" y2="9"/>
</svg>"""

_SVG_WORD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <polyline points="8 13 10 18 12 13 14 18 16 13"/>
</svg>"""

_SVG_EXCEL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <line x1="8" y1="13" x2="16" y2="19"/>
  <line x1="16" y1="13" x2="8"  y2="19"/>
</svg>"""

_SVG_PPT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <rect x="8" y="12" width="4" height="5" rx="1"/>
  <line x1="14" y1="13" x2="17" y2="13"/>
  <line x1="14" y1="16" x2="16" y2="16"/>
</svg>"""

_SVG_IMAGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2"/>
  <circle cx="8.5" cy="8.5" r="1.5"/>
  <polyline points="21 15 16 10 5 21"/>
</svg>"""

_SVG_VIDEO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="4" width="15" height="16" rx="2"/>
  <polygon points="22 8 17 12 22 16 22 8"/>
</svg>"""

_SVG_MUSIC = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9 18V5l12-2v13"/>
  <circle cx="6"  cy="18" r="3"/>
  <circle cx="18" cy="16" r="3"/>
</svg>"""

_SVG_ZIP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <line x1="12" y1="11" x2="12" y2="11"/><line x1="12" y1="14" x2="12" y2="14"/>
  <line x1="12" y1="17" x2="12" y2="17"/>
</svg>"""

_SVG_CODE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="16 18 22 12 16 6"/>
  <polyline points="8 6 2 12 8 18"/>
</svg>"""

_SVG_TXT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
  <line x1="8" y1="13" x2="16" y2="13"/>
  <line x1="8" y1="17" x2="16" y2="17"/>
</svg>"""

_SVG_FILE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
  <polyline points="14 2 14 8 20 8"/>
</svg>"""

_SVG_SEARCH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="11" cy="11" r="8"/>
  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
</svg>"""

_SVG_PANEL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2"/>
  <line x1="15" y1="3" x2="15" y2="21"/>
</svg>"""

# Mapa ext → (svg, color_acento)
_EXT_SVG: dict[str, tuple[str, str]] = {
    ".pdf":  (_SVG_PDF,   "#EF4444"),
    ".docx": (_SVG_WORD,  "#3B82F6"),
    ".doc":  (_SVG_WORD,  "#3B82F6"),
    ".xlsx": (_SVG_EXCEL, "#22C55E"),
    ".xls":  (_SVG_EXCEL, "#22C55E"),
    ".csv":  (_SVG_EXCEL, "#22C55E"),
    ".pptx": (_SVG_PPT,   "#F59E0B"),
    ".ppt":  (_SVG_PPT,   "#F59E0B"),
    ".png":  (_SVG_IMAGE, "#06B6D4"),
    ".jpg":  (_SVG_IMAGE, "#06B6D4"),
    ".jpeg": (_SVG_IMAGE, "#06B6D4"),
    ".gif":  (_SVG_IMAGE, "#06B6D4"),
    ".webp": (_SVG_IMAGE, "#06B6D4"),
    ".mp4":  (_SVG_VIDEO, "#A855F7"),
    ".mov":  (_SVG_VIDEO, "#A855F7"),
    ".mp3":  (_SVG_MUSIC, "#EC4899"),
    ".zip":  (_SVG_ZIP,   "#F97316"),
    ".rar":  (_SVG_ZIP,   "#F97316"),
    ".7z":   (_SVG_ZIP,   "#F97316"),
    ".py":   (_SVG_CODE,  "#84CC16"),
    ".js":   (_SVG_CODE,  "#EAB308"),
    ".ts":   (_SVG_CODE,  "#3B82F6"),
    ".html": (_SVG_CODE,  "#F97316"),
    ".css":  (_SVG_CODE,  "#A78BFA"),
    ".txt":  (_SVG_TXT,   "#94A3B8"),
}


def _svg_to_pixmap(svg_data: str, size: int, color: str):
    """Convierte SVG a QPixmap tintado con el color dado."""
    from PyQt6.QtGui import QPainter, QPixmap
    from PyQt6.QtCore import QByteArray, QRectF
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


class NeonFilterBtn(QPushButton):
    """Botón de filtro con ícono SVG neón + badge de texto."""

    def __init__(self, label: str, ext: str | None, parent=None):
        super().__init__(parent)
        self._label = label
        self._ext   = ext
        self._active = False
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 0, 14, 0)
        hl.setSpacing(7)

        # Ícono SVG
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(16, 16)
        self._icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._icon_lbl.setStyleSheet("background: transparent;")
        hl.addWidget(self._icon_lbl)

        # Texto
        self._text_lbl = QLabel(label)
        self._text_lbl.setStyleSheet(
            f"background: transparent; font-size: 12px; font-weight: 600; color: {C.TEXT2};"
        )
        hl.addWidget(self._text_lbl)

        self._set_active(False)

    def _color(self) -> str:
        if self._ext is None:
            return C.PURPLE3
        return _EXT_SVG.get(self._ext, (_SVG_FILE, C.PURPLE3))[1]

    def _svg(self) -> str:
        if self._ext is None:
            return _SVG_FILE
        return _EXT_SVG.get(self._ext, (_SVG_FILE, C.PURPLE3))[0]

    def _set_active(self, active: bool):
        self._active = active
        col = self._color() if active else C.TEXT3
        pm = _svg_to_pixmap(self._svg(), 16, col)
        self._icon_lbl.setPixmap(pm)

        if active:
            glow = self._color()
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1.5px solid {glow};
                    border-radius: 17px;
                }}
            """)
            self._text_lbl.setStyleSheet(
                f"background: transparent; font-size: 12px; font-weight: 700; color: {self._color()};"
            )
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {C.BORDER};
                    border-radius: 17px;
                }}
                QPushButton:hover {{
                    border-color: {C.BORDER2};
                    background: {C.BG4};
                }}
            """)
            self._text_lbl.setStyleSheet(
                f"background: transparent; font-size: 12px; font-weight: 600; color: {C.TEXT2};"
            )


# ══════════════════════════════════════════════════════════════════════
# FILE CARD
# ══════════════════════════════════════════════════════════════════════

class FileCard(GlowCard):
    edit_requested = pyqtSignal(dict)
    _EXT_COLORS = {
        ".pdf":  ("#EF4444","#3B0E0E"), ".docx": ("#3B82F6","#0F2040"),
        ".doc":  ("#3B82F6","#0F2040"), ".xlsx": ("#22C55E","#0A2E18"),
        ".xls":  ("#22C55E","#0A2E18"), ".pptx": ("#F59E0B","#3A1F05"),
        ".zip":  ("#F59E0B","#3A1F05"), ".rar":  ("#F59E0B","#3A1F05"),
        ".mp4":  ("#A855F7","#2A0A40"), ".mp3":  ("#EC4899","#350520"),
        ".png":  ("#06B6D4","#052A35"), ".jpg":  ("#06B6D4","#052A35"),
        ".jpeg": ("#06B6D4","#052A35"), ".gif":  ("#06B6D4","#052A35"),
        ".py":   ("#84CC16","#1A2E05"), ".js":   ("#EAB308","#2E1D02"),
        ".ts":   ("#3B82F6","#0F2040"), ".html": ("#F97316","#2E0E02"),
        ".css":  ("#A78BFA","#1E1240"), ".txt":  ("#94A3B8","#1E2433"),
    }
    _DEFAULT_COLORS = ("#9D5EF0","#1E1240")

    def __init__(self, record: dict, parent=None):
        super().__init__(parent)
        self._record = record
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        ext = Path(record["path"]).suffix.lower()
        self._fg, self._bg_icon = self._EXT_COLORS.get(ext, self._DEFAULT_COLORS)
        self._build(record)

    @property
    def _GLOW_COL(self): return QColor(self._fg)
    @property
    def _ACC_COL(self):  return QColor(self._fg)

    def _build(self, r: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(12)
        ext = Path(r["path"]).suffix.lower()
        ext_str = ext.upper().lstrip(".") or "FILE"

        # Ícono SVG neón en el badge
        svg_data, svg_color = _EXT_SVG.get(ext, (_SVG_FILE, self._fg))
        icon_box = QLabel()
        icon_box.setFixedSize(42, 42)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(f"""
            background: {self._bg_icon};
            border-radius: 11px;
            border: 1px solid {self._fg}55;
        """)
        pm = _svg_to_pixmap(svg_data, 22, svg_color)
        icon_box.setPixmap(pm)
        top.addWidget(icon_box)

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        name = r["name"]
        name_lbl = QLabel(name if len(name) <= 26 else name[:24] + "…")
        name_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        name_col.addWidget(name_lbl)
        desc_s = r.get("description", "").strip()
        sub = (f"{ext_str} · {desc_s[:32]}…" if len(desc_s) > 32
               else f"{ext_str} · {desc_s}" if desc_s else ext_str)
        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        name_col.addWidget(sub_lbl)
        top.addLayout(name_col, 1)

        exists = r.get("file_exists")
        if exists is not None:
            st = QLabel("●")
            st.setStyleSheet(
                f"font-size: 9px; color: {C.GREEN if exists else C.RED}; background: transparent;"
            )
            top.addWidget(st)
        layout.addLayout(top)
        layout.addSpacing(8)

        desc = r.get("description", "").strip()
        dl = QLabel((desc[:68] + "…") if len(desc) > 68 else (desc or "Sin descripción"))
        dl.setStyleSheet(f"font-size: 12px; color: {C.TEXT2}; background: transparent;")
        dl.setWordWrap(True)
        layout.addWidget(dl)
        layout.addStretch()

        tr = QHBoxLayout()
        tr.setSpacing(5)
        for tag in r.get("tags", [])[:3]:
            chip = QLabel(tag)
            chip.setStyleSheet(f"""
                background: {C.PURPLE_DIM}; color: {C.PURPLE3};
                border-radius: 5px; padding: 2px 9px;
                font-size: 10px; font-weight: 600;
            """)
            tr.addWidget(chip)
        tr.addStretch()

        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.BG5}; border: 1px solid {C.BORDER};
                border-radius: 8px; font-size: 11px; color: {C.TEXT3};
            }}
            QPushButton:hover {{
                background: {C.PURPLE_DIM2}; color: {C.PURPLE3};
                border-color: {C.PURPLE_DIM2};
            }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._record))
        tr.addWidget(edit_btn)
        layout.addLayout(tr)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.edit_requested.emit(self._record)


# ══════════════════════════════════════════════════════════════════════
# EXT TYPE ROW (panel derecho)
# ══════════════════════════════════════════════════════════════════════

class ExtTypeRow(QWidget):
    def __init__(self, ext: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 4)
        layout.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(8)

        # Ícono SVG pequeño
        dot_ext = f".{ext.lower()}"
        svg_data, svg_color = _EXT_SVG.get(dot_ext, (_SVG_FILE, C.PURPLE3))
        ic = QLabel()
        ic.setFixedSize(14, 14)
        ic.setPixmap(_svg_to_pixmap(svg_data, 14, svg_color))
        ic.setStyleSheet("background: transparent;")
        top.addWidget(ic)

        lbl = QLabel(ext.upper())
        lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        top.addWidget(lbl)
        top.addStretch()

        cnt = QLabel(str(count))
        cnt.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {svg_color}; background: transparent;"
        )
        top.addWidget(cnt)
        layout.addLayout(top)

        bar_bg = QFrame()
        bar_bg.setFixedHeight(3)
        bar_bg.setStyleSheet(f"background: {C.BG4}; border-radius: 2px; border: none;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setFixedHeight(3)
        bar_inner.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {svg_color},stop:1 {C.PURPLE3}); border-radius: 2px;"
        )
        pct = max(4, int(count / max_count * 100)) if max_count else 4
        bar_inner.setFixedWidth(int(160 * pct / 100))
        layout.addWidget(bar_bg)


# ══════════════════════════════════════════════════════════════════════
# ARCHIVOS PAGE
# ══════════════════════════════════════════════════════════════════════

class ArchivosPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_files: list[dict]       = []
        self._worker: SearchWorker | None = None
        self._scan_worker: FolderScanWorker | None = None
        self._import_worker: FolderImportWorker | None = None
        self._search_id   = 0
        self._active_ext: str | None      = None
        self._filter_widgets: dict[str, NeonFilterBtn] = {}
        self._panel_visible = True
        self._build()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)

    # ── layout ────────────────────────────────────────────────────────

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel principal ───────────────────────────────────────────
        main_panel = QWidget()
        main_panel.setStyleSheet("background: transparent;")
        ml = QVBoxLayout(main_panel)
        ml.setContentsMargins(32, 28, 20, 20)
        ml.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel("Todos los archivos")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        # Buscador con lupa SVG neón
        sf = QFrame()
        sf.setStyleSheet(f"""
            QFrame {{
                background: {C.BG3};
                border: 1px solid {C.BORDER2};
                border-radius: 12px;
            }}
            QFrame:focus-within {{
                border-color: {C.PURPLE};
            }}
        """)
        sf.setFixedWidth(300)
        sf.setFixedHeight(42)
        sfl = QHBoxLayout(sf)
        sfl.setContentsMargins(12, 0, 12, 0)
        sfl.setSpacing(8)

        # Lupa SVG
        lupa = QLabel()
        lupa.setFixedSize(16, 16)
        lupa.setPixmap(_svg_to_pixmap(_SVG_SEARCH, 16, C.PURPLE3))
        lupa.setStyleSheet("background: transparent;")
        sfl.addWidget(lupa)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar archivos y etiquetas...")
        self._search_input.setStyleSheet(
            f"background: transparent; border: none; font-size: 13px; color: {C.TEXT}; padding: 0;"
        )
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

        # Botones sort
        self._btn_import = QPushButton("Importar carpeta")
        self._btn_import.setObjectName("btn_primary")
        self._btn_import.setFixedHeight(42)
        self._btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_import.clicked.connect(self._on_import_folder)
        header.addWidget(self._btn_import)

        self._btn_mas = QPushButton("Más usados")
        self._btn_mas.setObjectName("btn_sort_active")
        self._btn_mas.setFixedHeight(42)
        self._btn_mas.clicked.connect(lambda: self._set_sort("usage"))
        header.addWidget(self._btn_mas)

        self._btn_az = QPushButton("⇅  A-Z")
        self._btn_az.setObjectName("btn_ghost")
        self._btn_az.setFixedHeight(42)
        self._btn_az.clicked.connect(lambda: self._set_sort("alpha"))
        header.addWidget(self._btn_az)

        # Botón toggle panel derecho (ícono SVG)
        self._btn_toggle_panel = QPushButton()
        self._btn_toggle_panel.setFixedSize(42, 42)
        self._btn_toggle_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle_panel.setToolTip("Mostrar/ocultar panel lateral")
        self._btn_toggle_panel.clicked.connect(self._toggle_panel)
        self._update_toggle_btn_icon(True)
        header.addWidget(self._btn_toggle_panel)

        self._sort_mode = "usage"
        ml.addLayout(header)
        ml.addSpacing(16)

        # Separador
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 transparent, stop:0.1 {C.BORDER2},
                stop:0.9 {C.BORDER2}, stop:1 transparent);
            border: none;
        """)
        ml.addWidget(sep)
        ml.addSpacing(14)

        # Barra de filtros (chips con NeonFilterBtn)
        self._filter_inner = QWidget()
        self._filter_inner.setStyleSheet("background: transparent;")
        self._filter_bar = QHBoxLayout(self._filter_inner)
        self._filter_bar.setContentsMargins(0, 2, 0, 2)
        self._filter_bar.setSpacing(6)

        filter_scroll = QScrollArea()
        filter_scroll.setWidgetResizable(True)
        filter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        filter_scroll.setFixedHeight(42)
        filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        filter_scroll.setStyleSheet("background: transparent;")
        filter_scroll.setWidget(self._filter_inner)
        ml.addWidget(filter_scroll)
        ml.addSpacing(10)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent; margin-bottom: 4px;"
        )
        ml.addWidget(self._count_lbl)
        ml.addSpacing(6)

        # Grid de tarjetas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 8, 0)
        self._grid.setSpacing(14)
        scroll.setWidget(self._grid_container)
        ml.addWidget(scroll, 1)
        root.addWidget(main_panel, 1)

        # ── Panel lateral derecho ─────────────────────────────────────
        self._right_panel = QFrame()
        self._right_panel.setFixedWidth(210)
        self._right_panel.setStyleSheet(f"""
            QFrame {{ background: {C.BG2}; border-left: 1px solid {C.BORDER}; }}
        """)
        rl = QVBoxLayout(self._right_panel)
        rl.setContentsMargins(18, 28, 18, 24)
        rl.setSpacing(0)

        panel_title = QLabel("TIPOS DE ARCHIVOS MÁS USADOS")
        panel_title.setObjectName("section_title")
        panel_title.setWordWrap(True)
        rl.addWidget(panel_title)
        rl.addSpacing(16)

        self._types_layout = QVBoxLayout()
        self._types_layout.setSpacing(6)
        rl.addLayout(self._types_layout)
        rl.addStretch()
        root.addWidget(self._right_panel)

    # ── toggle panel ──────────────────────────────────────────────────

    def _update_toggle_btn_icon(self, visible: bool):
        col = C.PURPLE3 if visible else C.TEXT3
        pm = _svg_to_pixmap(_SVG_PANEL, 18, col)
        self._btn_toggle_panel.setIcon(
            __import__('PyQt6.QtGui', fromlist=['QIcon']).QIcon(pm)
        )
        self._btn_toggle_panel.setIconSize(
            __import__('PyQt6.QtCore', fromlist=['QSize']).QSize(18, 18)
        )
        self._btn_toggle_panel.setStyleSheet(f"""
            QPushButton {{
                background: {'%s' % C.PURPLE_DIM2 if visible else C.BG4};
                border: 1px solid {'%s' % C.PURPLE_DIM2 if visible else C.BORDER};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: {C.PURPLE_DIM2};
                border-color: {C.PURPLE};
            }}
        """)

    def _toggle_panel(self):
        self._panel_visible = not self._panel_visible
        self._update_toggle_btn_icon(self._panel_visible)

        # Animación de ancho: 210 → 0 o 0 → 210
        start_w = self._right_panel.width()
        end_w   = 210 if self._panel_visible else 0

        if self._panel_visible:
            self._right_panel.setVisible(True)

        self._anim = QPropertyAnimation(self._right_panel, b"maximumWidth")
        self._anim.setDuration(220)
        self._anim.setStartValue(start_w)
        self._anim.setEndValue(end_w)
        self._anim.setEasingCurve(
            QEasingCurve.Type.OutCubic if self._panel_visible
            else QEasingCurve.Type.InCubic
        )
        if not self._panel_visible:
            self._anim.finished.connect(lambda: self._right_panel.setVisible(False))
        self._anim.start()

    # ── lógica ────────────────────────────────────────────────────────

    def refresh(self):
        self._run_search()

    def _set_sort(self, mode: str):
        self._sort_mode = mode
        self._btn_mas.setObjectName("btn_sort_active" if mode == "usage" else "btn_ghost")
        self._btn_az.setObjectName("btn_sort_active" if mode == "alpha" else "btn_ghost")
        self._btn_mas.setStyle(self._btn_mas.style())
        self._btn_az.setStyle(self._btn_az.style())
        self._render_grid(self._apply_ext_filter(self._all_files))

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
        exts = Counter(
            Path(f["path"]).suffix.lower()
            for f in files if Path(f["path"]).suffix
        )
        top = [e for e, _ in exts.most_common(8)]

        for i in reversed(range(self._filter_bar.count())):
            item = self._filter_bar.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._filter_widgets.clear()

        entries = [("Todos", None)] + [(e.lstrip(".").upper(), e) for e in top]
        for label, ext in entries:
            btn = NeonFilterBtn(label, ext)
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
            is_active = (
                (key == "__all__" and self._active_ext is None) or
                (key == self._active_ext)
            )
            btn._set_active(is_active)

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

        exts = Counter(
            Path(f["path"]).suffix.lower()
            for f in files if Path(f["path"]).suffix
        )
        top = exts.most_common(10)
        max_count = top[0][1] if top else 1
        for ext, count in top:
            row = ExtTypeRow(ext.lstrip("."), count, max_count)
            self._types_layout.addWidget(row)

    def _on_search_changed(self, text):
        self._clear_btn.setVisible(bool(text))
        self._debounce.start(SEARCH_DEBOUNCE_MS)

    def _on_import_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Importar carpeta",
            str(Path.home()),
        )
        if not folder:
            return

        self._btn_import.setEnabled(False)
        self._btn_import.setText("Escaneando...")
        self._scan_worker = FolderScanWorker(folder)
        self._scan_worker.progress.connect(self._on_import_progress)
        self._scan_worker.scan_ready.connect(self._on_scan_ready)
        self._scan_worker.error.connect(self._on_import_error)
        self._scan_worker.finished.connect(self._cleanup_scan_worker)
        self._scan_worker.start()

    def _on_import_progress(self, label: str, current: int, total: int):
        total_text = f"/{total}" if total else ""
        self._count_lbl.setText(f"{label}: {current}{total_text}")

    def _on_scan_ready(self, result: dict):
        self._pending_scan = result
        new_count = result.get("new", 0)
        if new_count <= 0:
            QMessageBox.information(
                self,
                "Importar carpeta",
                "No se encontraron archivos nuevos para importar.",
            )
            self._reset_import_button()
            self._run_search()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Importar carpeta")
        msg.setText(f"Se encontraron {new_count} archivos nuevos.")
        msg.setInformativeText(
            "Escaneados: {scanned}\n"
            "Ya registrados: {existing}\n"
            "Omitidos por tipo: {unsupported}\n"
            "Omitidos por tamaño: {large}\n\n"
            "¿Quieres importarlos ahora?".format(
                scanned=result.get("scanned", 0),
                existing=result.get("skipped_existing", 0),
                unsupported=result.get("skipped_unsupported", 0),
                large=result.get("skipped_large", 0),
            )
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            self._reset_import_button()
            return

        self._btn_import.setText("Importando...")
        self._import_worker = FolderImportWorker(result)
        self._import_worker.progress.connect(self._on_import_progress)
        self._import_worker.completed.connect(self._on_import_finished)
        self._import_worker.error.connect(self._on_import_error)
        self._import_worker.finished.connect(self._cleanup_import_worker)
        self._import_worker.start()

    def _on_import_finished(self, result: dict):
        QMessageBox.information(
            self,
            "Importar carpeta",
            "Importados: {imported}\nErrores: {failed}".format(
                imported=result.get("imported", 0),
                failed=result.get("failed", 0),
            ),
        )
        self._reset_import_button()
        self._run_search()

    def _on_import_error(self, message: str):
        QMessageBox.warning(self, "Importar carpeta", message)
        self._reset_import_button()
        self._run_search()

    def _cleanup_scan_worker(self):
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None

    def _cleanup_import_worker(self):
        if self._import_worker:
            self._import_worker.deleteLater()
            self._import_worker = None

    def _reset_import_button(self):
        self._btn_import.setEnabled(True)
        self._btn_import.setText("Importar carpeta")

    def _on_edit(self, record):
        try:
            from dialogs import MetadataDialog
            dlg = MetadataDialog(record["path"], parent=self)
            dlg.exec()
            self._run_search()
        except Exception as e:
            logger.exception(f"Error abriendo diálogo: {e}")

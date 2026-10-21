"""
pages/buscar.py — Página de búsqueda · Opción A redesign.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  [🔍 Buscar archivos, etiquetas...          ⌘K ]   │  ← barra prominente
  │  [Todos] [PDF] [PY] [DOCX] ...   Fecha Etiq Ordenar│  ← chips + acciones
  ├─────────────────────────────────────────────────────┤
  │  27 resultados                                       │
  │  ┌──────┐ ┌──────┐ ┌──────┐                        │
  │  │ card │ │ card │ │ card │   ...                   │  ← grid tarjetas
  └─────────────────────────────────────────────────────┘
"""
from pathlib import Path
from collections import Counter

from PyQt6.QtCore import Qt, QTimer, QByteArray, QRectF
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)

import database as db
from config import get_logger, SEARCH_DEBOUNCE_MS, SEARCH_MAX_RESULTS
from theme import C
from widgets.search_worker import SearchWorker
from widgets.ui_helpers import ext_icon_str

logger = get_logger(__name__)

# ── SVG helpers ───────────────────────────────────────────────────────

def _svg_px(svg: str, color: str, size: int = 16) -> QPixmap:
    data = svg.replace("CLR", color)
    r = QSvgRenderer(QByteArray(data.encode()))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, size, size))
    p.end()
    return px

_SVG_SEARCH = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="11" cy="11" r="7" stroke="CLR" stroke-width="2"/>
  <path d="M16.5 16.5L21 21" stroke="CLR" stroke-width="2" stroke-linecap="round"/>
</svg>"""

_SVG_CALENDAR = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="4" width="18" height="17" rx="2" stroke="CLR" stroke-width="1.8" fill="none"/>
  <line x1="3" y1="9" x2="21" y2="9" stroke="CLR" stroke-width="1.8"/>
  <line x1="8" y1="2" x2="8" y2="6" stroke="CLR" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="16" y1="2" x2="16" y2="6" stroke="CLR" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""

_SVG_TAG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M20.6 11.5L12.5 3.4A2 2 0 0 0 11.1 3H4a1 1 0 0 0-1 1v7.1c0 .5.2 1 .6 1.4l8.1 8.1a2 2 0 0 0 2.8 0l6.1-6.1a2 2 0 0 0 0-2.8z"
        stroke="CLR" stroke-width="1.8" fill="none"/>
  <circle cx="7.5" cy="7.5" r="1" fill="CLR"/>
</svg>"""

_SVG_SORT = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <line x1="4" y1="6" x2="20" y2="6" stroke="CLR" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="4" y1="12" x2="14" y2="12" stroke="CLR" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="4" y1="18" x2="9" y2="18" stroke="CLR" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""

# SVGs por tipo de archivo
_EXT_SVG = {
    "pdf":  """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="CLR" stroke-width="1.8" fill="none"/><polyline points="14 2 14 8 20 8" stroke="CLR" stroke-width="1.8" fill="none"/><line x1="8" y1="13" x2="16" y2="13" stroke="CLR" stroke-width="1.5"/><line x1="8" y1="17" x2="16" y2="17" stroke="CLR" stroke-width="1.5"/></svg>""",
    "docx": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="CLR" stroke-width="1.8" fill="none"/><polyline points="14 2 14 8 20 8" stroke="CLR" stroke-width="1.8" fill="none"/><line x1="8" y1="12" x2="16" y2="12" stroke="CLR" stroke-width="1.4"/><line x1="8" y1="15" x2="16" y2="15" stroke="CLR" stroke-width="1.4"/><line x1="8" y1="18" x2="13" y2="18" stroke="CLR" stroke-width="1.4"/></svg>""",
    "xlsx": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" rx="2" stroke="CLR" stroke-width="1.8" fill="none"/><line x1="3" y1="9" x2="21" y2="9" stroke="CLR" stroke-width="1.4"/><line x1="3" y1="15" x2="21" y2="15" stroke="CLR" stroke-width="1.4"/><line x1="9" y1="3" x2="9" y2="21" stroke="CLR" stroke-width="1.4"/></svg>""",
    "py":   """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><polyline points="16 18 22 12 16 6" stroke="CLR" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><polyline points="8 6 2 12 8 18" stroke="CLR" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>""",
    "png":  """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" rx="2" stroke="CLR" stroke-width="1.8" fill="none"/><circle cx="8.5" cy="8.5" r="1.5" stroke="CLR" stroke-width="1.4" fill="none"/><polyline points="21 15 16 10 5 21" stroke="CLR" stroke-width="1.5" fill="none"/></svg>""",
    "mp4":  """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="4" width="15" height="16" rx="2" stroke="CLR" stroke-width="1.8" fill="none"/><polyline points="17 8 22 5 22 19 17 16" stroke="CLR" stroke-width="1.8" fill="none"/></svg>""",
    "zip":  """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><polyline points="21 8 21 21 3 21 3 8" stroke="CLR" stroke-width="1.8" fill="none"/><rect x="1" y="3" width="22" height="5" rx="1" stroke="CLR" stroke-width="1.8" fill="none"/><line x1="10" y1="12" x2="14" y2="12" stroke="CLR" stroke-width="1.8"/></svg>""",
    "txt":  """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="CLR" stroke-width="1.8" fill="none"/><polyline points="14 2 14 8 20 8" stroke="CLR" stroke-width="1.8" fill="none"/><line x1="8" y1="13" x2="16" y2="13" stroke="CLR" stroke-width="1.4"/><line x1="8" y1="17" x2="12" y2="17" stroke="CLR" stroke-width="1.4"/></svg>""",
    "_":    """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="CLR" stroke-width="1.8" fill="none"/><polyline points="14 2 14 8 20 8" stroke="CLR" stroke-width="1.8" fill="none"/></svg>""",
}

# Color accent por extensión
_EXT_COLOR = {
    "pdf":  "#F87171",  # rojo suave
    "docx": "#60A5FA",  # azul
    "doc":  "#60A5FA",
    "xlsx": "#34D399",  # verde
    "xls":  "#34D399",
    "csv":  "#34D399",
    "py":   "#FBBF24",  # ámbar
    "js":   "#FBBF24",
    "ts":   "#38BDF8",
    "png":  "#A78BFA",  # violeta
    "jpg":  "#A78BFA",
    "jpeg": "#A78BFA",
    "mp4":  "#F472B6",  # rosa
    "mp3":  "#F472B6",
    "zip":  "#94A3B8",  # gris
    "rar":  "#94A3B8",
    "txt":  "#CBD5E1",
    "pptx": "#FB923C",  # naranja
}

def _ext_color(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return _EXT_COLOR.get(ext, "#A78BFA")

def _ext_svg(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return _EXT_SVG.get(ext, _EXT_SVG["_"])


class BusquedaPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_files: list[dict] = []
        self._worker: SearchWorker | None = None
        self._retired_workers: list[SearchWorker] = []   # hilos cancelados que aún terminan
        self._search_id = 0
        self._active_ext: str | None = None
        self._sort_mode: str = "relevancia"   # relevancia | az | mas_usado
        self._filter_widgets: dict[str, QPushButton] = {}
        self._build()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)

    # ── construcción ──────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Bloque superior (barra + chips) ───────────────────────
        top = QWidget()
        top.setStyleSheet(f"background: transparent; border-bottom: 1px solid {C.BORDER};")
        top_vl = QVBoxLayout(top)
        top_vl.setContentsMargins(32, 20, 32, 14)
        top_vl.setSpacing(12)

        # Barra de búsqueda prominente
        search_bar = QWidget()
        search_bar.setFixedHeight(46)
        search_bar.setStyleSheet(f"""
            background: {C.BG3};
            border: 1.5px solid {C.BORDER};
            border-radius: 14px;
        """)
        sbl = QHBoxLayout(search_bar)
        sbl.setContentsMargins(16, 0, 16, 0)
        sbl.setSpacing(10)

        ic = QLabel()
        ic.setFixedSize(18, 18)
        ic.setPixmap(_svg_px(_SVG_SEARCH, C.TEXT3, 18))
        ic.setStyleSheet("background: transparent;")
        sbl.addWidget(ic)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar archivos, etiquetas, descripciones...")
        self._search_input.setStyleSheet(f"""
            background: transparent; border: none;
            font-size: 14px; color: {C.TEXT}; padding: 0;
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        sbl.addWidget(self._search_input, 1)

        kbd = QLabel("⌘K")
        kbd.setStyleSheet(f"""
            font-size: 11px; color: {C.TEXT4};
            background: {C.BG4};
            border: 1px solid {C.BORDER};
            border-radius: 5px;
            padding: 1px 6px;
        """)
        sbl.addWidget(kbd)
        top_vl.addWidget(search_bar)

        # Chips de extensión + acciones inline — misma fila
        chips_row = QWidget()
        chips_row.setStyleSheet("background: transparent;")
        chips_full = QHBoxLayout(chips_row)
        chips_full.setContentsMargins(0, 0, 0, 0)
        chips_full.setSpacing(0)

        # Lado izquierdo: chips de tipo
        chips_left = QWidget()
        chips_left.setStyleSheet("background: transparent;")
        self._chips_hl = QHBoxLayout(chips_left)
        self._chips_hl.setContentsMargins(0, 0, 0, 0)
        self._chips_hl.setSpacing(6)
        chips_full.addWidget(chips_left)
        chips_full.addStretch()

        # Lado derecho: acciones Fecha · Etiquetas · Ordenar
        actions_row = QWidget()
        actions_row.setStyleSheet("background: transparent;")
        actions_hl = QHBoxLayout(actions_row)
        actions_hl.setContentsMargins(0, 0, 0, 0)
        actions_hl.setSpacing(2)

        for svg, label, slot in [
            (_SVG_CALENDAR, "Fecha",     self._on_filter_date),
            (_SVG_TAG,      "Etiquetas", self._on_filter_tags),
            (_SVG_SORT,     "Ordenar",   self._on_sort),
        ]:
            btn = self._action_btn(svg, label, slot)
            actions_hl.addWidget(btn)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFixedWidth(1)
            sep.setFixedHeight(14)
            sep.setStyleSheet(f"background: {C.BORDER}; border: none;")
            actions_hl.addWidget(sep)
        # quitar último separador
        last = actions_hl.itemAt(actions_hl.count() - 1)
        if last and last.widget():
            last.widget().deleteLater()

        chips_full.addWidget(actions_row)
        top_vl.addWidget(chips_row)

        root.addWidget(top)

        # ── Cuerpo: contador + grid ────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_vl = QVBoxLayout(body)
        body_vl.setContentsMargins(32, 16, 32, 24)
        body_vl.setSpacing(12)

        # Fila contador
        meta_row = QWidget()
        meta_row.setStyleSheet("background: transparent;")
        meta_hl = QHBoxLayout(meta_row)
        meta_hl.setContentsMargins(0, 0, 0, 0)
        meta_hl.setSpacing(0)

        self._count_lbl = QLabel("Cargando...")
        self._count_lbl.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        meta_hl.addWidget(self._count_lbl)
        meta_hl.addStretch()

        body_vl.addWidget(meta_row)

        # Grid de resultados
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
            QScrollBar:vertical {{
                background: {C.BG3}; width: 5px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER2}; border-radius: 3px; min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {C.PURPLE}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0; background: none;
            }}
        """)
        self._res_container = QWidget()
        self._res_container.setStyleSheet("background: transparent;")
        self._res_grid = QGridLayout(self._res_container)
        self._res_grid.setContentsMargins(0, 0, 0, 0)
        self._res_grid.setSpacing(12)
        self._res_grid.setColumnStretch(0, 1)
        self._res_grid.setColumnStretch(1, 1)
        self._res_grid.setColumnStretch(2, 1)
        scroll.setWidget(self._res_container)
        body_vl.addWidget(scroll, 1)

        root.addWidget(body, 1)

    def _action_btn(self, svg: str, label: str, slot) -> QWidget:
        """Botón de acción inline (ícono SVG + texto)."""
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {C.TEXT3};
                font-size: 12px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                color: {C.TEXT};
            }}
        """)

        hl = QHBoxLayout(btn)
        hl.setContentsMargins(8, 0, 8, 0)
        hl.setSpacing(5)

        ic = QLabel()
        ic.setFixedSize(14, 14)
        ic.setPixmap(_svg_px(svg, C.TEXT3, 14))
        ic.setStyleSheet("background: transparent;")
        hl.addWidget(ic)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        hl.addWidget(lbl)

        btn.clicked.connect(slot)
        return btn

    # ── lógica ────────────────────────────────────────────────────────

    def refresh(self):
        self._run_search()

    def _run_search(self):
        query = self._search_input.text().strip()
        if self._worker is not None:
            # No se espera al hilo anterior (bloquearía la UI mientras se escribe):
            # se cancela y sus resultados se descartan por search_id.
            self._worker.stop()
            self._retired_workers.append(self._worker)
        self._search_id += 1
        current_id = self._search_id
        worker = SearchWorker(query)
        worker.results_ready.connect(
            lambda r, sid=current_id: self._on_results(r, sid)
        )
        worker.error.connect(
            lambda msg, sid=current_id: self._on_search_error(msg, sid)
        )
        worker.finished.connect(lambda w=worker: self._on_worker_finished(w))
        self._worker = worker
        worker.start()

    def shutdown_workers(self, timeout_ms: int = 3000) -> None:
        """Cancela y espera las búsquedas en curso antes de cerrar la app."""
        for worker in [self._worker, *self._retired_workers]:
            if worker is not None and worker.isRunning():
                worker.stop()
                worker.wait(timeout_ms)

    def _on_worker_finished(self, worker):
        if worker in self._retired_workers:
            self._retired_workers.remove(worker)
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    def _on_search_error(self, message, search_id):
        if search_id != self._search_id:
            return
        self._count_lbl.setText("No se pudo completar la búsqueda")

    def _on_results(self, results, search_id):
        if search_id != self._search_id:
            return
        self._all_files = results
        self._build_ext_chips(results)
        filtered = self._apply_filters(results)
        self._render_results(filtered)
        n = len(filtered)
        self._count_lbl.setText(f"{n} resultado{'s' if n != 1 else ''}")

    def _apply_filters(self, files):
        if self._active_ext:
            files = [f for f in files if Path(f["path"]).suffix.lower() == self._active_ext]
        if self._sort_mode == "az":
            files = sorted(files, key=lambda f: f["name"].lower())
        elif self._sort_mode == "mas_usado":
            files = sorted(files, key=lambda f: len(f.get("tags", [])), reverse=True)
        return files

    def _build_ext_chips(self, files):
        exts = Counter(Path(f["path"]).suffix.lower() for f in files if Path(f["path"]).suffix)
        top = [e for e, _ in exts.most_common(7)]

        for i in reversed(range(self._chips_hl.count())):
            item = self._chips_hl.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._filter_widgets.clear()

        for label, ext in [("Todos", None)] + [(e.lstrip(".").upper(), e) for e in top]:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, e=ext: self._set_ext_filter(e))
            key = "__all__" if ext is None else ext
            self._filter_widgets[key] = btn
            self._chips_hl.addWidget(btn)

        self._chips_hl.addStretch()
        self._refresh_chip_styles()

    def _set_ext_filter(self, ext):
        self._active_ext = ext
        self._refresh_chip_styles()
        filtered = self._apply_filters(self._all_files)
        self._render_results(filtered)
        n = len(filtered)
        self._count_lbl.setText(f"{n} resultado{'s' if n != 1 else ''}")

    def _refresh_chip_styles(self):
        for key, btn in self._filter_widgets.items():
            active = (key == "__all__" and self._active_ext is None) or (key == self._active_ext)
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PURPLE};
                        color: white;
                        border: none;
                        border-radius: 15px;
                        padding: 0 16px;
                        font-size: 12px;
                        font-weight: 700;
                    }}
                    QPushButton:hover {{
                        background: {C.PURPLE2};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.TEXT3};
                        border: 1px solid {C.BORDER};
                        border-radius: 15px;
                        padding: 0 14px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        border-color: {C.BORDER2};
                        color: {C.TEXT};
                    }}
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
                f"color: {C.TEXT3}; font-size: 14px; background: transparent; padding: 60px;"
            )
            self._res_grid.addWidget(empty, 0, 0, 1, 3)
            return

        COLS = 3
        for i, record in enumerate(files):
            card = self._make_card(record)
            self._res_grid.addWidget(card, i // COLS, i % COLS)

    def _make_card(self, r: dict) -> QWidget:
        color = _ext_color(r["path"])
        ext   = Path(r["path"]).suffix.upper().lstrip(".")
        name  = r["name"]
        desc  = r.get("description", "").strip()
        tags  = r.get("tags", [])[:3]

        card = QWidget()
        card.setObjectName("res_card")
        card.setFixedHeight(136)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QWidget#res_card {{
                background: {C.BG2};
                border: 1px solid {C.BORDER};
                border-radius: 14px;
            }}
            QWidget#res_card:hover {{
                border-color: {C.BORDER2};
                background: {C.BG3};
            }}
        """)

        vl = QVBoxLayout(card)
        vl.setContentsMargins(14, 13, 14, 13)
        vl.setSpacing(8)

        # ── Fila superior: ícono + nombre/descripción ─────────────
        top_hl = QHBoxLayout()
        top_hl.setSpacing(10)

        # Ícono — fondo neutro, sin color de tipo
        ic_bg = QWidget()
        ic_bg.setFixedSize(38, 38)
        ic_bg.setStyleSheet(f"""
            background: {C.PURPLE_DIM};
            border-radius: 10px;
            border: 1px solid {C.PURPLE_DIM2};
        """)
        ic_lbl = QLabel(ic_bg)
        ic_lbl.setGeometry(7, 7, 24, 24)
        ic_lbl.setPixmap(_svg_px(_ext_svg(r["path"]), "#A78BFA", 24))
        ic_lbl.setStyleSheet("background: transparent;")
        top_hl.addWidget(ic_bg)

        # Nombre + descripción
        name_vl = QVBoxLayout()
        name_vl.setSpacing(2)
        name_vl.setContentsMargins(0, 0, 0, 0)

        nm = QLabel(name if len(name) <= 24 else name[:22] + "…")
        nm.setToolTip(name)
        nm.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {C.TEXT}; background: transparent;")
        name_vl.addWidget(nm)

        sub_text = f"{ext} · {desc[:32]}…" if len(desc) > 32 else f"{ext} · {desc}" if desc else ext
        sl = QLabel(sub_text)
        sl.setStyleSheet(f"font-size: 11px; color: {C.TEXT3}; background: transparent;")
        name_vl.addWidget(sl)

        top_hl.addLayout(name_vl, 1)
        vl.addLayout(top_hl)
        vl.addStretch()

        # ── Fila inferior: tags ───────────────────────────────────
        tag_hl = QHBoxLayout()
        tag_hl.setSpacing(5)
        tag_hl.setContentsMargins(0, 0, 0, 0)

        for tag in tags:
            chip = QLabel(tag)
            chip.setStyleSheet(f"""
                background: {C.PURPLE_DIM};
                color: {C.PURPLE3};
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
            """)
            tag_hl.addWidget(chip)
        tag_hl.addStretch()

        vl.addLayout(tag_hl)
        return card

    # ── slots de acciones ─────────────────────────────────────────────

    def _on_filter_date(self):
        pass  # TODO: abrir popover de fecha

    def _on_filter_tags(self):
        pass  # TODO: abrir popover de etiquetas

    def _on_sort(self):
        modes = ["relevancia", "az", "mas_usado"]
        idx = modes.index(self._sort_mode)
        self._sort_mode = modes[(idx + 1) % len(modes)]
        self._render_results(self._apply_filters(self._all_files))

    def _on_search_changed(self, text):
        self._debounce.start(SEARCH_DEBOUNCE_MS)
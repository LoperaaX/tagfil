"""
main_window.py — Ventana principal de InfoFile

Muestra todos los archivos registrados como tarjetas en un grid,
con búsqueda en tiempo real y panel lateral de detalle/edición.

Uso desde main.py:
    from PyQt6.QtWidgets import QApplication
    from main_window import MainWindow
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec()
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore    import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui     import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QStatusBar, QVBoxLayout,
    QWidget,
)

import database as db
from config  import (
    get_logger, APP_NAME, ICON_PATH,
    WINDOW_TITLE, WINDOW_MIN_W, WINDOW_MIN_H,
    SEARCH_DEBOUNCE_MS, SEARCH_MAX_RESULTS,
)
from dialogs import DescriptionDialog

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Estilos
# ──────────────────────────────────────────────

_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── Barra superior ── */
QWidget#topbar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
}

QLabel#app_title {
    color: #7287fd;
    font-size: 17px;
    font-weight: 700;
}

QLineEdit#search_input {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 14px;
}
QLineEdit#search_input:focus { border-color: #7287fd; }
QLineEdit#search_input:hover { border-color: #45475a; }

/* ── Tarjeta ── */
QWidget#card {
    background-color: #181825;
    border: 1px solid #26263a;
    border-radius: 10px;
}
QWidget#card_selected {
    background-color: #212137;
    border: 1.5px solid #7287fd;
    border-radius: 10px;
}
QWidget#card:hover {
    border-color: #45475a;
}

QLabel#card_name {
    color: #cdd6f4;
    font-size: 13px;
    font-weight: 600;
}
QLabel#card_desc {
    color: #a6adc8;
    font-size: 12px;
}
QLabel#card_tag {
    background-color: #2a2a3e;
    color: #89b4fa;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 600;
}
QLabel#card_icon {
    color: #45475a;
    font-size: 20px;
}

/* ── Panel lateral ── */
QWidget#detail_panel {
    background-color: #181825;
    border-left: 1px solid #313244;
}
QLabel#detail_name {
    color: #cdd6f4;
    font-size: 15px;
    font-weight: 600;
}
QLabel#detail_path {
    color: #6c7086;
    font-size: 11px;
}
QLabel#detail_section {
    color: #a6adc8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel#detail_value {
    color: #cdd6f4;
    font-size: 13px;
}
QLabel#detail_empty_text {
    color: #45475a;
    font-size: 13px;
}
QLabel#tag_chip {
    background-color: #2a2a3e;
    color: #89b4fa;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* ── Botones ── */
QPushButton#btn_edit {
    background-color: #7287fd;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 0;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btn_edit:hover   { background-color: #89b4fa; }
QPushButton#btn_edit:pressed { background-color: #5b6fd8; }

QPushButton#btn_open {
    background-color: transparent;
    color: #6c7086;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px 0;
    font-size: 13px;
}
QPushButton#btn_open:hover {
    background-color: #313244;
    color: #cdd6f4;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #181825;
    width: 7px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #313244;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #45475a; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

/* ── Status bar ── */
QStatusBar {
    background-color: #181825;
    color: #6c7086;
    border-top: 1px solid #313244;
    font-size: 11px;
    padding: 2px 10px;
}
"""


# ──────────────────────────────────────────────
# Worker de búsqueda (hilo separado)
# ──────────────────────────────────────────────

class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error         = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        try:
            results = db.search(self.query)[:SEARCH_MAX_RESULTS]
            self.results_ready.emit(results)
        except Exception as e:
            logger.exception(f"Error en búsqueda: {e}")
            self.error.emit(str(e))


# ──────────────────────────────────────────────
# Tarjeta individual
# ──────────────────────────────────────────────

class FileCard(QWidget):
    """
    Tarjeta visual de un archivo.
    Emite clicked con sus datos al hacer clic.
    """
    clicked = pyqtSignal(dict)

    # Íconos por extensión (texto unicode — no requiere assets)
    _ICONS = {
        ".pdf":  "📄", ".docx": "📝", ".doc":  "📝",
        ".xlsx": "📊", ".xls":  "📊", ".pptx": "📋",
        ".txt":  "📃", ".py":   "🐍", ".js":   "📜",
        ".png":  "🖼", ".jpg":  "🖼", ".jpeg": "🖼",
        ".zip":  "🗜", ".rar":  "🗜", ".mp4":  "🎬",
    }
    _ICON_FOLDER = "📁"
    _ICON_DEFAULT = "📄"

    def __init__(self, file_data: dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.selected  = False
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(110)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Ícono
        ext  = Path(self.file_data["path"]).suffix.lower()
        icon = self._ICON_FOLDER if Path(self.file_data["path"]).is_dir() else \
               self._ICONS.get(ext, self._ICON_DEFAULT)
        lbl_icon = QLabel(icon)
        lbl_icon.setObjectName("card_icon")
        lbl_icon.setFixedWidth(28)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        lbl_icon.setStyleSheet("font-size: 22px;")

        # Contenido
        content = QVBoxLayout()
        content.setSpacing(4)
        content.setContentsMargins(0, 0, 0, 0)

        # Nombre
        lbl_name = QLabel(self.file_data["name"])
        lbl_name.setObjectName("card_name")
        lbl_name.setMaximumWidth(320)

        # Descripción
        desc = self.file_data.get("description", "").strip()
        lbl_desc = QLabel(desc if desc else "Sin descripción")
        lbl_desc.setObjectName("card_desc")
        lbl_desc.setMaximumWidth(320)
        if not desc:
            lbl_desc.setStyleSheet("color: #45475a;")

        # Tags
        tags_row = QHBoxLayout()
        tags_row.setSpacing(5)
        tags_row.setContentsMargins(0, 0, 0, 0)
        tags_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for tag in self.file_data.get("tags", [])[:4]:   # máx 4 chips
            chip = QLabel(tag)
            chip.setObjectName("card_tag")
            tags_row.addWidget(chip)

        if len(self.file_data.get("tags", [])) > 4:
            more = QLabel(f"+{len(self.file_data['tags']) - 4}")
            more.setObjectName("card_tag")
            more.setStyleSheet(
                "background-color: #26263a; color: #6c7086; "
                "border-radius: 4px; padding: 2px 7px; font-size: 10px;"
            )
            tags_row.addWidget(more)

        tags_row.addStretch()

        content.addWidget(lbl_name)
        content.addWidget(lbl_desc)
        content.addLayout(tags_row)

        layout.addWidget(lbl_icon)
        layout.addLayout(content, 1)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.setObjectName("card_selected" if selected else "card")
        # Forzar refresco de estilo
        from PyQt6.QtWidgets import QApplication
        QApplication.style().unpolish(self)
        QApplication.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_data)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_data)
        super().mouseDoubleClickEvent(event)


# ──────────────────────────────────────────────
# Grid de tarjetas
# ──────────────────────────────────────────────

class CardGrid(QScrollArea):
    """
    Área scrollable con tarjetas en grid de 2 columnas.
    Emite card_selected con los datos del archivo al hacer clic.
    """
    card_selected  = pyqtSignal(dict)
    card_activated = pyqtSignal(dict)   # doble clic → abrir diálogo

    _COLS = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(16, 16, 16, 16)
        self._grid.setSpacing(10)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._container)
        self._cards: list[FileCard] = []
        self._selected_card: FileCard | None = None

        # Etiqueta de estado vacío
        self._lbl_empty = QLabel("No se encontraron resultados")
        self._lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_empty.setStyleSheet("color: #45475a; font-size: 14px;")
        self._lbl_empty.setVisible(False)
        self._grid.addWidget(self._lbl_empty, 0, 0, 1, self._COLS)

    def populate(self, results: list[dict]) -> None:
        """Limpia y reconstruye el grid con los nuevos resultados."""
        # Limpiar tarjetas anteriores
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        self._selected_card = None

        self._lbl_empty.setVisible(len(results) == 0)

        for idx, file_data in enumerate(results):
            row = idx // self._COLS
            col = idx % self._COLS
            card = FileCard(file_data)
            card.clicked.connect(self._on_card_clicked)
            self._grid.addWidget(card, row + 1, col)   # +1 por la fila del lbl_empty
            self._cards.append(card)

    def _on_card_clicked(self, file_data: dict) -> None:
        # Deseleccionar anterior
        if self._selected_card:
            self._selected_card.set_selected(False)

        # Seleccionar la nueva
        sender = self.sender()
        if isinstance(sender, FileCard):
            sender.set_selected(True)
            self._selected_card = sender

        self.card_selected.emit(file_data)


# ──────────────────────────────────────────────
# Panel lateral de detalle
# ──────────────────────────────────────────────

class DetailPanel(QWidget):
    edit_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detail_panel")
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)
        self._current_path: str | None = None
        self._setup_ui()
        self.show_empty()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(0)

        self._lbl_name = QLabel()
        self._lbl_name.setObjectName("detail_name")
        self._lbl_name.setWordWrap(True)

        self._lbl_path = QLabel()
        self._lbl_path.setObjectName("detail_path")
        self._lbl_path.setWordWrap(True)

        layout.addWidget(self._lbl_name)
        layout.addSpacing(4)
        layout.addWidget(self._lbl_path)
        layout.addSpacing(16)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#313244; max-height:1px;")
        layout.addWidget(sep)
        layout.addSpacing(16)

        # Descripción
        self._sec_desc = self._make_section("DESCRIPCIÓN")
        layout.addWidget(self._sec_desc)
        layout.addSpacing(6)
        self._lbl_desc = QLabel()
        self._lbl_desc.setObjectName("detail_value")
        self._lbl_desc.setWordWrap(True)
        layout.addWidget(self._lbl_desc)
        layout.addSpacing(14)

        # Tags
        self._sec_tags = self._make_section("ETIQUETAS")
        layout.addWidget(self._sec_tags)
        layout.addSpacing(6)
        self._tags_w = QWidget()
        self._tags_l = QHBoxLayout(self._tags_w)
        self._tags_l.setContentsMargins(0, 0, 0, 0)
        self._tags_l.setSpacing(6)
        self._tags_l.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._tags_w)
        layout.addSpacing(14)

        # Fecha
        self._sec_date = self._make_section("MODIFICADO")
        layout.addWidget(self._sec_date)
        layout.addSpacing(6)
        self._lbl_date = QLabel()
        self._lbl_date.setObjectName("detail_value")
        layout.addWidget(self._lbl_date)

        layout.addStretch()

        # Botones
        self._btn_edit = QPushButton("Editar descripción")
        self._btn_edit.setObjectName("btn_edit")
        self._btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_edit.clicked.connect(lambda: self.edit_requested.emit(self._current_path))

        self._btn_open = QPushButton("Abrir ubicación")
        self._btn_open.setObjectName("btn_open")
        self._btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_open.clicked.connect(self._open_location)

        layout.addWidget(self._btn_edit)
        layout.addSpacing(8)
        layout.addWidget(self._btn_open)

    def _make_section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("detail_section")
        return lbl

    def show_empty(self) -> None:
        self._current_path = None
        self._lbl_name.setText("Selecciona un archivo")
        self._lbl_name.setObjectName("detail_empty_text")
        self._lbl_path.setText("")
        self._lbl_desc.setText("")
        self._lbl_date.setText("")
        self._clear_tags()
        for w in [self._btn_edit, self._btn_open,
                  self._sec_desc, self._sec_tags, self._sec_date,
                  self._lbl_desc, self._lbl_date, self._tags_w]:
            w.setVisible(False)

    def show_file(self, f: dict) -> None:
        self._current_path = f["path"]
        path = Path(f["path"])

        self._lbl_name.setText(f["name"])
        self._lbl_name.setObjectName("detail_name")

        short = str(path.parent)
        if len(short) > 38:
            short = "..." + short[-35:]
        self._lbl_path.setText(short)

        desc = f.get("description", "").strip()
        self._lbl_desc.setText(desc if desc else "Sin descripción")
        self._lbl_desc.setStyleSheet("" if desc else "color: #45475a;")

        self._clear_tags()
        tags = f.get("tags", [])
        if tags:
            for tag in tags:
                chip = QLabel(tag)
                chip.setObjectName("tag_chip")
                self._tags_l.addWidget(chip)
        else:
            no_tags = QLabel("Sin etiquetas")
            no_tags.setObjectName("detail_empty_text")
            self._tags_l.addWidget(no_tags)

        raw = f.get("updated_at", "")
        try:
            dt = datetime.fromisoformat(raw)
            self._lbl_date.setText(dt.strftime("%d/%m/%Y  %H:%M"))
        except Exception:
            self._lbl_date.setText(raw)

        for w in [self._btn_edit, self._btn_open,
                  self._sec_desc, self._sec_tags, self._sec_date,
                  self._lbl_desc, self._lbl_date, self._tags_w]:
            w.setVisible(True)

    def _clear_tags(self) -> None:
        for i in reversed(range(self._tags_l.count())):
            item = self._tags_l.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w:
                w.deleteLater()

    def _open_location(self) -> None:
        if self._current_path:
            try:
                subprocess.Popen(f'explorer /select,"{self._current_path}"')
            except Exception as e:
                logger.warning(f"No se pudo abrir ubicación: {e}")


# ──────────────────────────────────────────────
# Ventana principal
# ──────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._search_worker: SearchWorker | None = None
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)

        self._setup_window()
        self._setup_ui()
        self._setup_shortcuts()

        db.init_db()
        self._run_search()

    def _setup_window(self) -> None:
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.resize(960, 620)
        self.setStyleSheet(_STYLE)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._grid = CardGrid()
        self._grid.card_selected.connect(self._on_card_selected)

        self._detail = DetailPanel()
        self._detail.edit_requested.connect(self._open_dialog)

        splitter.addWidget(self._grid)
        splitter.addWidget(self._detail)
        splitter.setSizes([680, 280])

        root.addWidget(splitter, 1)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._set_status("Listo")

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setObjectName("app_title")

        self._search_input = QLineEdit()
        self._search_input.setObjectName("search_input")
        self._search_input.setPlaceholderText(
            "Buscar por nombre, descripción o etiqueta..."
        )
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(
            lambda: self._debounce.start(SEARCH_DEBOUNCE_MS)
        )
        self._search_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(self._search_input, 1)
        return bar

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)
        QShortcut(QKeySequence("F5"),     self, self._run_search)

    # ── Búsqueda ─────────────────────────────────

    def _run_search(self) -> None:
        query = self._search_input.text().strip()
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
        self._set_status("Buscando...")
        self._search_worker = SearchWorker(query)
        self._search_worker.results_ready.connect(self._on_results)
        self._search_worker.error.connect(
            lambda e: self._set_status(f"Error: {e}")
        )
        self._search_worker.start()

    def _on_results(self, results: list[dict]) -> None:
        self._grid.populate(results)
        query = self._search_input.text().strip()
        n = len(results)
        if query:
            self._set_status(f"{n} resultado(s) para '{query}'")
        else:
            self._set_status(f"{n} archivo(s) registrado(s)")

    # ── Interacción ──────────────────────────────

    def _on_card_selected(self, file_data: dict) -> None:
        self._detail.show_file(file_data)

    def _open_dialog(self, path: str) -> None:
        dialog = DescriptionDialog(path, parent=self)
        if dialog.exec():
            self._run_search()

    # ── Utilidades ────────────────────────────────

    def _focus_search(self) -> None:
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _on_escape(self) -> None:
        if self._search_input.text():
            self._search_input.clear()
        else:
            self.hide()   # ocultar al tray si no hay texto

    def _set_status(self, msg: str) -> None:
        self._status.showMessage(f"  {msg}")


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

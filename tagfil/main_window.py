"""
main_window.py — Ventana principal de TagFil.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget,
)

import database as db
from config import get_logger, APP_NAME, ICON_PATH
from theme import C, QSS
from sidebar import Sidebar
from pages.resumen       import ResumenPage
from pages.archivos      import ArchivosPage
from pages.etiquetas     import EtiquetasPage
from pages.buscar        import BusquedaPage
from pages.configuracion import ConfigPage
from pages.papelera      import PapeleraPage
from widgets.starfield   import StarfieldBackground

logger = get_logger(__name__)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._bg: StarfieldBackground | None = None
        self._setup_window()
        self._setup_ui()
        self._setup_shortcuts()
        db.init_db()
        QTimer.singleShot(100, self._pages[0].refresh)

    def shutdown_workers(self) -> None:
        """Pide a cada página que detenga sus hilos (importación, búsqueda) antes de salir."""
        for page in self._pages:
            stop = getattr(page, "shutdown_workers", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    pass

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

        # Contenedor del contenido con fondo animado
        self._content_wrap = QWidget()
        # Los fondos transparentes se limitan a estos contenedores (por objectName).
        # Sin selector, «background: transparent» se heredaba a todos los widgets
        # de todas las páginas y anulaba el fondo de los botones del tema (btn_primary).
        self._content_wrap.setObjectName("content_wrap")
        self._content_wrap.setStyleSheet("QWidget#content_wrap { background: transparent; }")
        cl = QVBoxLayout(self._content_wrap)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # Fondo animado — se coloca detrás
        self._bg = StarfieldBackground(mode="space", parent=self._content_wrap)
        self._bg.lower()

        self._stack = QStackedWidget()
        self._stack.setObjectName("page_stack")
        self._stack.setStyleSheet("QStackedWidget#page_stack { background: transparent; }")

        self._pages: list[QWidget] = [
            ResumenPage(),    # 0
            ArchivosPage(),   # 1
            EtiquetasPage(),  # 2
            BusquedaPage(),   # 3
            ConfigPage(),     # 4
            PapeleraPage(),   # 5
        ]
        for page in self._pages:
            self._stack.addWidget(page)

        cl.addWidget(self._stack, 1)
        root.addWidget(self._content_wrap, 1)

        # Conectar el selector de fondo en ConfigPage
        config_page = self._pages[4]
        if hasattr(config_page, "bg_changed"):
            config_page.bg_changed.connect(self._set_background)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._set_status("Listo")

    def _setup_shortcuts(self):
        for i in range(1, 7):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self,
                      lambda _, idx=i-1: self._navigate_to(idx))
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

    def _set_background(self, mode: str):
        """Cambia el fondo animado — llamado desde ConfigPage."""
        if self._bg:
            self._bg.set_mode(mode)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._bg:
            self._bg.setGeometry(self._content_wrap.rect())

    def showEvent(self, event):
        super().showEvent(event)
        if self._bg:
            self._bg.setGeometry(self._content_wrap.rect())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
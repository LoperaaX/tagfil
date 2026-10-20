"""
tray.py — Bandeja del sistema de TagFil

Mantiene TagFil corriendo en segundo plano con un ícono
en la bandeja del sistema (system tray de Windows).

Menú del tray:
  - Abrir TagFil
  - N archivos registrados  (solo lectura)
  - Instalar / Desinstalar menú contextual
  - Salir

Uso desde main.py:
    from PyQt6.QtWidgets import QApplication
    from tray import TrayApp
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = TrayApp()
    tray.show()
    tray.open_window()
    app.exec()
"""

import sys

from PyQt6.QtCore    import QTimer
from PyQt6.QtGui     import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon

import database as db
from config       import APP_NAME, ICON_PATH, get_logger
from context_menu import install, is_installed, uninstall
from startup import enable as startup_enable, disable as startup_disable, is_enabled as startup_is_enabled

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Ícono generado en código
# ──────────────────────────────────────────────

def _make_tray_icon() -> QIcon:
    """
    Usa assets/icon.ico si existe.
    Si no, genera un círculo morado con las iniciales 'TF'.
    """
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))

    size = 32
    px   = QPixmap(size, size)
    px.fill(QColor(0, 0, 0, 0))

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor("#7287fd"))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(1, 1, size - 2, size - 2)

    font = QFont("Segoe UI", 11, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#1e1e2e"))
    # Qt.AlignHCenter | Qt.AlignVCenter = 0x04 | 0x80 = 0x84
    painter.drawText(px.rect(), 0x84, "TF")

    painter.end()
    return QIcon(px)


# ──────────────────────────────────────────────
# Ventana principal con closeEvent correcto
# ──────────────────────────────────────────────

class _MainWindowWrapped:
    """
    Crea MainWindow con closeEvent sobreescrito correctamente.
    En PyQt6 no se puede asignar closeEvent directamente a una instancia;
    hay que crear una subclase o usar un wrapper.
    """

    @staticmethod
    def create(on_close_cb) -> QMainWindow:
        from tagfil.main_window import MainWindow

        class _W(MainWindow):
            def closeEvent(self, event):
                event.ignore()
                self.hide()
                on_close_cb()

        return _W()


# ──────────────────────────────────────────────
# Aplicación de bandeja
# ──────────────────────────────────────────────

class TrayApp:
    """
    Gestiona el ícono del tray y el ciclo de vida de la ventana principal.
    La app solo se cierra desde "Salir" en el menú del tray.
    """

    def __init__(self):
        self._win: QMainWindow | None = None
        self._setup_tray()

        # Actualizar stats cada 5 minutos
        self._stats_timer = QTimer()
        self._stats_timer.setInterval(5 * 60 * 1000)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start()

    # ── Construcción ────────────────────────────

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray no disponible en este sistema")

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_make_tray_icon())
        self._tray.setToolTip(f"{APP_NAME} — Descripciones inteligentes para tus archivos")
        self._tray.activated.connect(self._on_activated)
        self._tray.setContextMenu(self._build_menu())

    def _build_menu(self) -> QMenu:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected { background-color: #313244; }
            QMenu::item:disabled { color: #45475a; }
            QMenu::separator {
                height: 1px;
                background: #313244;
                margin: 4px 8px;
            }
        """)

        # Abrir ventana
        act_open = menu.addAction(f"Abrir {APP_NAME}")
        f = QFont("Segoe UI", 13)
        f.setBold(True)
        act_open.setFont(f)
        act_open.triggered.connect(self.open_window)

        menu.addSeparator()

        # Stats (deshabilitado — solo informativo)
        self._act_stats = menu.addAction("Cargando...")
        self._act_stats.setEnabled(False)
        self._refresh_stats()

        menu.addSeparator()

        # Toggle menú contextual
        self._act_ctx = menu.addAction("")
        self._act_ctx.triggered.connect(self._toggle_context_menu)
        self._update_ctx_label()

        # Toggle inicio con Windows
        self._act_startup = menu.addAction("")
        self._act_startup.triggered.connect(self._toggle_startup)
        self._update_startup_label()

        menu.addSeparator()

        act_quit = menu.addAction("Salir")
        act_quit.triggered.connect(self._quit)

        return menu

    # ── Stats ────────────────────────────────────

    def _refresh_stats(self) -> None:
        try:
            db.init_db()
            n = db.get_stats()["total_files"]
            plural = "s" if n != 1 else ""
            self._act_stats.setText(f"{n} archivo{plural} registrado{plural}")
        except Exception as e:
            logger.warning(f"Error stats tray: {e}")
            self._act_stats.setText("Sin datos")

    # ── Menú contextual ──────────────────────────

    def _update_ctx_label(self) -> None:
        self._act_ctx.setText(
            "Desinstalar menú contextual" if is_installed()
            else "Instalar menú contextual"
        )

    def _toggle_context_menu(self) -> None:
        if is_installed():
            ok  = uninstall()
            msg = "Menú contextual desinstalado" if ok else "Error al desinstalar"
        else:
            ok  = install()
            msg = "Menú contextual instalado" if ok else "Error al instalar"

        self._update_ctx_label()

        self._tray.showMessage(APP_NAME, msg, _make_tray_icon(), 3000)
        logger.info(msg)

    def _update_startup_label(self) -> None:
        self._act_startup.setText(
            "Deshabilitar inicio con Windows" if startup_is_enabled()
            else "Iniciar con Windows"
        )

    def _toggle_startup(self) -> None:
        if startup_is_enabled():
            ok  = startup_disable()
            msg = "Inicio automático deshabilitado" if ok else "Error al deshabilitar"
        else:
            ok  = startup_enable()
            msg = "TagFil se iniciará con Windows" if ok else "Error al habilitar"
        self._update_startup_label()
        self._tray.showMessage(APP_NAME, msg, _make_tray_icon(), 3000)
        logger.info(msg)


    # ── Ventana principal ────────────────────────

    def open_window(self) -> None:
        """Crea (si no existe) y muestra la ventana principal."""
        if self._win is None:
            self._win = _MainWindowWrapped.create(self._on_window_hidden)

        self._win.show()
        self._win.raise_()
        self._win.activateWindow()

    def _on_window_hidden(self) -> None:
        """Callback cuando el usuario cierra la ventana (se oculta al tray)."""
        self._tray.showMessage(
            APP_NAME,
            f"{APP_NAME} sigue corriendo en la bandeja del sistema.",
            _make_tray_icon(),
            2000,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_window()

    # ── Ciclo de vida ────────────────────────────

    def show(self) -> None:
        self._tray.show()
        logger.info("TagFil iniciado en la bandeja del sistema")

    def _quit(self) -> None:
        logger.info("Cerrando TagFil...")
        try:
            db.optimize_db()
        except Exception:
            pass
        self._tray.hide()
        QApplication.quit()


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    tray = TrayApp()
    tray.show()
    tray.open_window()

    sys.exit(app.exec())

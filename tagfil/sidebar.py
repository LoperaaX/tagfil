"""
sidebar.py — Sidebar de navegación de TagFil.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from theme import C
from widgets.ui_helpers import sep

class SidebarButton(QPushButton):
    """Botón de navegación del sidebar con estilo TagFil."""

    def __init__(self, icon_char: str, text: str, parent=None):
        super().__init__(parent)
        self._active = False
        self._icon_char = icon_char
        self._text_str  = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        self._lbl_icon = QLabel(icon_char)
        self._lbl_icon.setFixedSize(18, 18)
        self._lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_icon.setStyleSheet("background: transparent; font-size: 15px;")

        self._lbl_text = QLabel(text)
        self._lbl_text.setStyleSheet(
            f"background: transparent; font-size: 13.5px; font-weight: 500;"
        )

        layout.addWidget(self._lbl_icon)
        layout.addWidget(self._lbl_text)
        layout.addStretch()

        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._refresh()

    def _refresh(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PURPLE_DIM};
                    border: none;
                    border-radius: 10px;
                    border-left: 3px solid {C.PURPLE2};
                    padding-left: 13px;
                }}
            """)
            self._lbl_text.setStyleSheet(
                f"background: transparent; font-size: 13.5px; font-weight: 700; color: {C.TEXT};"
            )
            self._lbl_icon.setStyleSheet(
                f"background: transparent; font-size: 15px; color: {C.PURPLE3};"
            )
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background: {C.BG3};
                }}
            """)
            self._lbl_text.setStyleSheet(
                f"background: transparent; font-size: 13.5px; font-weight: 500; color: {C.TEXT2};"
            )
            self._lbl_icon.setStyleSheet(
                "background: transparent; font-size: 15px;"
            )


class Sidebar(QWidget):
    page_changed = pyqtSignal(int)

    _NAV_ITEMS = [
        ("🏠", "Resumen",              0),
        ("📁", "Todos los archivos",   1),
        ("🏷️", "Etiquetas",            2),
        ("🔍", "Buscar",               3),
    ]
    _BOTTOM_ITEMS = [
        ("🗑️", "Papelera",             5),
        ("⚙️", "Configuración",        4),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background: {C.BG2};
                border-right: 1px solid {C.BORDER};
            }}
        """)
        self._buttons: list[tuple[SidebarButton, int | None]] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 18)
        layout.setSpacing(2)

        # ── Logo ──
        logo_frame = QWidget()
        logo_frame.setFixedHeight(72)
        ll = QHBoxLayout(logo_frame)
        ll.setContentsMargins(10, 0, 0, 0)
        ll.setSpacing(10)

        # Icono "T" estilizado
        logo_icon = QLabel()
        logo_icon.setFixedSize(34, 34)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setText("T")
        logo_icon.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {C.PURPLE}, stop:1 #5B21B6);
            border-radius: 9px;
            font-size: 18px;
            font-weight: 800;
            color: white;
            letter-spacing: -1px;
        """)

        logo_text = QLabel("TagFil")
        logo_text.setStyleSheet(f"""
            font-size: 20px; font-weight: 800;
            color: {C.TEXT}; letter-spacing: -0.5px;
            background: transparent;
        """)
        ll.addWidget(logo_icon)
        ll.addWidget(logo_text)
        ll.addStretch()
        layout.addWidget(logo_frame)

        for icon, text, page_idx in self._NAV_ITEMS:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda _, i=page_idx: self._on_nav(i))
            self._buttons.append((btn, page_idx))
            layout.addWidget(btn)

        layout.addStretch()

        # ── Línea divisora ──
        layout.addWidget(sep())
        layout.addSpacing(8)

        for icon, text, page_idx in self._BOTTOM_ITEMS:
            btn = SidebarButton(icon, text)
            if page_idx is not None:
                btn.clicked.connect(lambda _, i=page_idx: self._on_nav(i))
            self._buttons.append((btn, page_idx))
            layout.addWidget(btn)

        self._set_active(0)

    def _on_nav(self, page_idx: int) -> None:
        self._set_active(page_idx)
        self.page_changed.emit(page_idx)

    def _set_active(self, page_idx: int) -> None:
        for btn, idx in self._buttons:
            btn.set_active(idx == page_idx)

    def navigate_to(self, page_idx: int) -> None:
        self._set_active(page_idx)


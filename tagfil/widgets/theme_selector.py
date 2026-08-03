"""
theme_selector.py — Selector de tema visual con íconos SVG neón.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtGui import QColor

from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from theme import C
from widgets.neon_icon import NeonSvgIcon, _SVG_MOON, _SVG_SUN, _SVG_SYSTEM

class ThemeSelector(QWidget):
    """Selector de tema visual: Oscuro · Claro · Sistema con íconos SVG neón."""

    # SVG data por índice
    _ICONS = [_SVG_MOON, _SVG_SUN, _SVG_SYSTEM]
    _LABELS = ["Oscuro", "Claro", "Sistema"]
    # Color activo (neón morado) vs inactivo (gris)
    _COLOR_ON  = "#A78BFA"
    _COLOR_OFF = "#6B7280"

    def __init__(self, selected: int = 0, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)

        self._btns:      list[QPushButton]   = []
        self._svg_icons: list[NeonSvgIcon]   = []
        self._txt_lbls:  list[QLabel]        = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, (svg_data, label) in enumerate(zip(self._ICONS, self._LABELS)):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(i == selected)
            btn.setFixedSize(100, 80)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            vl = QVBoxLayout(btn)
            vl.setContentsMargins(0, 12, 0, 12)
            vl.setSpacing(8)
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Ícono SVG neón
            icon_w = NeonSvgIcon.from_data(
                svg_data, size=26,
                color=self._COLOR_ON if i == selected else self._COLOR_OFF,
                glow=(i == selected)
            )
            icon_w.setObjectName(f"theme_icon_{i}")

            tx_lbl = QLabel(label)
            tx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tx_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 500; background: transparent; color: {C.TEXT2};"
            )

            # Centrar el ícono manualmente con un container
            ic_container = QWidget()
            ic_container.setFixedSize(26, 26)
            ic_container.setStyleSheet("background: transparent;")
            icon_w.setParent(ic_container)
            icon_w.move(0, 0)

            vl.addWidget(ic_container, 0, Qt.AlignmentFlag.AlignHCenter)
            vl.addWidget(tx_lbl)

            self._btns.append(btn)
            self._svg_icons.append(icon_w)
            self._txt_lbls.append(tx_lbl)
            self._group.addButton(btn, i)
            hl.addWidget(btn)

        self._group.idToggled.connect(self._refresh_styles)
        self._refresh_styles()

    def _refresh_styles(self, *_):
        for i, btn in enumerate(self._btns):
            active = btn.isChecked()
            icon_w = self._svg_icons[i]
            tx_lbl = self._txt_lbls[i]

            # Actualizar color y glow del ícono
            icon_w._color = QColor(self._COLOR_ON if active else self._COLOR_OFF)
            icon_w._glow  = active
            icon_w.update()

            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PURPLE_DIM2};
                        border: 1.5px solid {C.PURPLE};
                        border-radius: 12px;
                    }}
                """)
                tx_lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: 700; background: transparent; color: {C.PURPLE3};"
                )
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.BG4};
                        border: 1px solid {C.BORDER};
                        border-radius: 12px;
                    }}
                    QPushButton:hover {{
                        background: {C.BG5};
                        border-color: {C.BORDER2};
                    }}
                """)
                tx_lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: 500; background: transparent; color: {C.TEXT3};"
                )



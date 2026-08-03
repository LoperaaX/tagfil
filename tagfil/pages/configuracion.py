"""
pages/configuracion.py — Página de Configuración (tema, almacenamiento, backup, integraciones).
"""
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)

import database as db
from security import encrypted_backups_enabled, run_security_audit
from theme import C
from widgets.toggle_switch import ToggleSwitch
from widgets.neon_icon import (
    NeonSvgIcon,
    _SVG_PALETTE, _SVG_DB, _SVG_LIGHTNING, _SVG_SHIELD,
)
from widgets.theme_selector import ThemeSelector
from config import DB_PATH

# SVG para el ícono de integraciones (nube/enlace)
_SVG_CLOUD = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

# SVGs simples para cada servicio (colores propios por CSS override)
_SVG_ONEDRIVE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M10.5 18H6a4 4 0 0 1-.5-7.97 5.5 5.5 0 0 1 10.86-1.1A3.5 3.5 0 0 1 18 15.5a3 3 0 0 1-3 2.5H10.5z"
        stroke="#0078D4" stroke-width="1.6" fill="none"/>
</svg>"""

_SVG_GDRIVE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 3L2 19h6l4-7 4 7h6L12 3z" stroke="#34A853" stroke-width="1.6" fill="none"/>
  <path d="M6 19l4-7" stroke="#EA4335" stroke-width="1.6"/>
  <path d="M18 19l-4-7" stroke="#4285F4" stroke-width="1.6"/>
</svg>"""

_SVG_SHAREPOINT = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="9" cy="12" r="6" stroke="#038387" stroke-width="1.6" fill="none"/>
  <circle cx="15" cy="8" r="4" stroke="#0078D4" stroke-width="1.4" fill="none"/>
  <circle cx="16" cy="16" r="3" stroke="#038387" stroke-width="1.4" fill="none"/>
  <line x1="13" y1="10" x2="11" y2="11" stroke="#777" stroke-width="1.2"/>
  <line x1="13" y1="15" x2="11" y2="14" stroke="#777" stroke-width="1.2"/>
</svg>"""

_SVG_ACTIVITY = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 19V5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M8 17V9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M12 19V4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 15V8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M20 19v-6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>"""


class ConfigPage(QWidget):
    bg_changed = pyqtSignal(str)  # emite "space", "city" o "none"

    """
    Layout:
      Título
      ┌─────────────────────────┬──────────────────────────┐
      │  Interfaz de Usuario    │  Almacenamiento          │
      │  ThemeSelector          │  Ruta + botón            │
      ├─────────────────────────┼──────────────────────────┤
      │  Comportamiento         │  Copia de Seguridad      │
      │  3× toggle rows         │  estado + botón + toggle │
      ├─────────────────────────┴──────────────────────────┤
      │  Integraciones (ancho completo)                    │
      │  OneDrive / Google Drive / SharePoint + toggles   │
      │  [Guardar cambios]                                 │
      └────────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.refresh()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(40, 36, 40, 40)
        bv.setSpacing(0)

        title = QLabel("Configuración")
        title.setObjectName("page_title")
        bv.addWidget(title)
        bv.addSpacing(28)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._card_interfaz(),       0, 0)
        grid.addWidget(self._card_almacenamiento(), 0, 1)
        grid.addWidget(self._card_comportamiento(), 1, 0)
        grid.addWidget(self._card_copia(),          1, 1)

        bv.addLayout(grid)
        bv.addSpacing(16)

        # Integraciones — fila completa debajo del grid
        bv.addWidget(self._card_integraciones())
        bv.addSpacing(16)

        security_grid = QGridLayout()
        security_grid.setSpacing(16)
        security_grid.setColumnStretch(0, 1)
        security_grid.setColumnStretch(1, 1)
        security_grid.addWidget(self._card_seguridad(), 0, 0)
        security_grid.addWidget(self._card_actividad(), 0, 1)
        bv.addLayout(security_grid)

        bv.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_card(glow: bool = False) -> tuple[QWidget, QVBoxLayout]:
        card = QWidget()
        border_col = C.PURPLE_DIM if glow else C.BORDER
        card.setStyleSheet(f"""
            QWidget#config_card {{
                background: {C.BG2};
                border: 1px solid {border_col};
                border-radius: 16px;
            }}
        """)
        card.setObjectName("config_card")

        if glow:
            eff = QGraphicsDropShadowEffect()
            eff.setBlurRadius(28)
            eff.setOffset(0, 0)
            eff.setColor(QColor(C.PURPLE_GLOW))
            card.setGraphicsEffect(eff)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)
        return card, layout

    @staticmethod
    def _card_header(svg_data: str, text: str) -> QWidget:
        w  = QWidget()
        w.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)

        ic_bg = QWidget()
        ic_bg.setFixedSize(32, 32)
        ic_bg.setStyleSheet(f"""
            background: {C.PURPLE_DIM};
            border-radius: 9px;
            border: 1px solid {C.PURPLE_DIM2};
        """)
        ic_svg = NeonSvgIcon.from_data(svg_data, size=18, color="#A78BFA", glow=True)
        ic_svg.setParent(ic_bg)
        ic_svg.move(7, 7)

        hl.addWidget(ic_bg)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {C.TEXT}; background: transparent;"
        )
        hl.addWidget(lbl)
        hl.addStretch()
        return w

    @staticmethod
    def _divider() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setFixedHeight(1)
        f.setStyleSheet(f"background: {C.BORDER}; border: none;")
        return f

    def _toggle_row(self, label: str, subtitle: str,
                    checked: bool = False) -> tuple[QWidget, ToggleSwitch]:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 4, 0, 4)
        hl.setSpacing(12)

        txt = QWidget()
        txt.setStyleSheet("background: transparent;")
        vl  = QVBoxLayout(txt)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {C.TEXT}; background: transparent;"
        )
        sub = QLabel(subtitle)
        sub.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        vl.addWidget(lbl)
        vl.addWidget(sub)
        hl.addWidget(txt, 1)

        toggle = ToggleSwitch(checked)
        hl.addWidget(toggle)
        return row, toggle

    def _plain_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.BG4};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 9px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {C.BG5};
                border-color: {C.PURPLE_DIM2};
                color: {C.PURPLE3};
            }}
        """)
        return btn

    def _status_row(self, name: str) -> tuple[QWidget, QLabel, QLabel]:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 4, 0, 4)
        hl.setSpacing(10)

        lbl = QLabel(name)
        lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {C.TEXT2}; background: transparent;"
        )
        hl.addWidget(lbl, 1)

        badge = QLabel("INFO")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(52)
        badge.setStyleSheet(self._badge_style("info"))
        hl.addWidget(badge)

        detail = QLabel("")
        detail.setToolTip("")
        detail.setMinimumWidth(130)
        detail.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        hl.addWidget(detail, 1)
        return row, badge, detail

    @staticmethod
    def _badge_style(status: str) -> str:
        colors = {
            "ok": ("#14532D", "#22C55E"),
            "info": (C.BG4, C.TEXT3),
            "warn": ("#78350F", "#F59E0B"),
            "error": ("#7F1D1D", "#EF4444"),
        }
        bg, fg = colors.get(status, colors["info"])
        return f"""
            background: {bg};
            color: {fg};
            border: 1px solid {fg}66;
            border-radius: 8px;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 6px;
        """

    def _integration_row(self, svg_data: str, name: str,
                         subtitle: str, checked: bool = False) -> tuple[QWidget, ToggleSwitch]:
        """Fila de integración con ícono SVG propio del servicio."""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 6, 0, 6)
        hl.setSpacing(14)

        # Ícono del servicio con fondo suave
        ic_bg = QWidget()
        ic_bg.setFixedSize(36, 36)
        ic_bg.setStyleSheet(f"""
            background: {C.BG4};
            border-radius: 10px;
            border: 1px solid {C.BORDER};
        """)
        ic_svg = NeonSvgIcon.from_data(svg_data, size=20, color="#A78BFA", glow=False)
        ic_svg.setParent(ic_bg)
        ic_svg.move(8, 8)
        hl.addWidget(ic_bg)

        txt = QWidget()
        txt.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(txt)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)
        lbl = QLabel(name)
        lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {C.TEXT}; background: transparent;"
        )
        sub = QLabel(subtitle)
        sub.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        vl.addWidget(lbl)
        vl.addWidget(sub)
        hl.addWidget(txt, 1)

        toggle = ToggleSwitch(checked)
        hl.addWidget(toggle)
        return row, toggle

    # ── cards ────────────────────────────────────────────────────────

    def _card_interfaz(self) -> QWidget:
        card, cl = self._make_card(glow=True)
        cl.addWidget(self._card_header(_SVG_PALETTE, "Interfaz de Usuario"))
        cl.addWidget(self._divider())

        sub = QLabel("Tema de la aplicación")
        sub.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        cl.addWidget(sub)

        self._theme_sel = ThemeSelector(selected=0)
        cl.addWidget(self._theme_sel)

        cl.addSpacing(14)
        cl.addWidget(self._divider())
        cl.addSpacing(10)

        bg_lbl = QLabel("Fondo animado")
        bg_lbl.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        cl.addWidget(bg_lbl)
        cl.addSpacing(8)

        bg_row = QHBoxLayout()
        bg_row.setSpacing(8)
        bg_row.setContentsMargins(0, 0, 0, 0)

        self._bg_btns: dict[str, QPushButton] = {}
        self._active_bg = "space"

        for mode, label in [("space", "✦  Espacio"), ("city", "🏙  Ciudad"), ("none", "○  Ninguno")]:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self._set_bg(m))
            self._bg_btns[mode] = btn
            bg_row.addWidget(btn)

        cl.addLayout(bg_row)
        self._refresh_bg_btns()
        cl.addStretch()
        return card

    def _set_bg(self, mode: str):
        self._active_bg = mode
        self._refresh_bg_btns()
        self.bg_changed.emit(mode)

    def _refresh_bg_btns(self):
        for mode, btn in self._bg_btns.items():
            if mode == self._active_bg:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #8B5CF6, stop:0.5 #A855F7, stop:1 #C026D3);
                        color: white; border: none; border-radius: 9px;
                        font-size: 12px; font-weight: 700;
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #9333EA, stop:1 #C026D3);
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: 1px solid {C.BORDER};
                        border-radius: 9px;
                        font-size: 12px; color: {C.TEXT2};
                    }}
                    QPushButton:hover {{
                        background: {C.BG4};
                        border-color: {C.BORDER2};
                        color: {C.TEXT};
                    }}
                """)

    def _card_almacenamiento(self) -> QWidget:
        card, cl = self._make_card()
        cl.addWidget(self._card_header(_SVG_DB, "Almacenamiento"))
        cl.addWidget(self._divider())

        lbl = QLabel("Ubicación de la base de datos")
        lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {C.TEXT}; background: transparent;"
        )
        cl.addWidget(lbl)

        path = QLineEdit()
        path.setText(str(DB_PATH))
        path.setReadOnly(True)
        path.setFixedHeight(30)
        path.setStyleSheet(f"""
            QLineEdit {{
                background: {C.BG4};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 11px;
                color: {C.TEXT3};
            }}
        """)
        cl.addWidget(path)

        btn = QPushButton("Cambiar ubicación")
        btn.setFixedHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:0.5 #A855F7, stop:1 #C026D3);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.4px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333EA, stop:0.5 #C026D3, stop:1 #DB2777);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C3AED, stop:1 #A855F7);
            }}
        """)
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(32)
        btn_shadow.setOffset(0, 6)
        btn_shadow.setColor(QColor("#C026D3AA"))
        btn.setGraphicsEffect(btn_shadow)
        cl.addWidget(btn)

        # Degradado decorativo debajo del botón
        glow_line_alm = QWidget()
        glow_line_alm.setFixedHeight(8)
        glow_line_alm.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.3 rgba(168, 85, 247, 60),
                stop:0.5 rgba(192, 38, 211, 80),
                stop:0.7 rgba(168, 85, 247, 60),
                stop:1 transparent);
            border: none;
            border-radius: 4px;
        """)
        cl.addWidget(glow_line_alm)
        cl.addStretch()
        return card

    def _card_comportamiento(self) -> QWidget:
        card, cl = self._make_card(glow=True)
        cl.addWidget(self._card_header(_SVG_LIGHTNING, "Comportamiento"))
        cl.addWidget(self._divider())

        items = [
            ("Iniciar con Windows",
             "Lanzar TagFil automáticamente al iniciar el equipo", True),
            ("Mostrar descripciones en el Explorador",
             "Muestra el tooltip de metadatos al pasar el cursor", True),
            ("Minimizar al cerrar",
             "Ocultar en la bandeja en lugar de cerrar completamente", False),
        ]
        for i, (lbl, sub, chk) in enumerate(items):
            row, _ = self._toggle_row(lbl, sub, chk)
            cl.addWidget(row)
            if i < len(items) - 1:
                cl.addWidget(self._divider())

        cl.addStretch()
        return card

    def _card_copia(self) -> QWidget:
        card, cl = self._make_card()
        cl.addWidget(self._card_header(_SVG_SHIELD, "Copia de Seguridad"))
        cl.addWidget(self._divider())

        # ── Fila de estado con punto verde ──────────────────────────
        status_row = QWidget()
        status_row.setStyleSheet("background: transparent;")
        srl = QHBoxLayout(status_row)
        srl.setContentsMargins(0, 4, 0, 4)
        srl.setSpacing(10)

        dot_container = QWidget()
        dot_container.setFixedSize(10, 10)
        dot_container.setStyleSheet(f"""
            background: {C.GREEN};
            border-radius: 5px;
            border: 1px solid #16A34A;
        """)
        srl.addWidget(dot_container, 0, Qt.AlignmentFlag.AlignVCenter)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        txt_col.setContentsMargins(0, 0, 0, 0)
        lbl1 = QLabel("Última copia realizada")
        lbl1.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {C.TEXT}; background: transparent;"
        )
        lbl2 = QLabel("Sáb 28/03/2026, 13:32:00")
        lbl2.setStyleSheet(
            f"font-size: 11px; color: {C.GREEN}; background: transparent;"
        )
        txt_col.addWidget(lbl1)
        txt_col.addWidget(lbl2)
        srl.addLayout(txt_col, 1)
        cl.addWidget(status_row)

        cl.addSpacing(6)

        # ── Botón principal — más visible con gradiente brillante ──
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.setSpacing(8)

        btn_now = QPushButton("  Crear copia de seguridad ahora")
        self._btn_backup_now = btn_now
        btn_now.setFixedHeight(42)
        btn_now.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_now.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:0.5 #A855F7, stop:1 #C026D3);
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.4px;
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333EA, stop:0.5 #C026D3, stop:1 #DB2777);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C3AED, stop:1 #A855F7);
            }}
        """)

        # Glow shadow más pronunciado para que sea visible
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(32)
        btn_shadow.setOffset(0, 6)
        btn_shadow.setColor(QColor("#C026D3AA"))
        btn_now.setGraphicsEffect(btn_shadow)

        btn_now.setIconSize(QSize(16, 16))
        brl.addWidget(btn_now, 1)
        cl.addWidget(btn_row)

        # ── Degradado decorativo debajo del botón ─────────────────
        glow_line = QWidget()
        glow_line.setFixedHeight(8)
        glow_line.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.3 rgba(168, 85, 247, 60),
                stop:0.5 rgba(192, 38, 211, 80),
                stop:0.7 rgba(168, 85, 247, 60),
                stop:1 transparent);
            border: none;
            border-radius: 4px;
        """)
        cl.addWidget(glow_line)

        cl.addSpacing(4)

        # ── Línea separadora con label centrado ────────────────────
        sep_row = QWidget()
        sep_row.setStyleSheet("background: transparent;")
        sepl = QHBoxLayout(sep_row)
        sepl.setContentsMargins(0, 0, 0, 0)
        sepl.setSpacing(8)

        line_l = QFrame()
        line_l.setFrameShape(QFrame.Shape.HLine)
        line_l.setFixedHeight(1)
        line_l.setStyleSheet(f"background: {C.BORDER}; border: none;")

        sep_lbl = QLabel("automático")
        sep_lbl.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            color: {C.TEXT4};
            background: transparent;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            padding: 0 4px;
        """)
        sep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        line_r = QFrame()
        line_r.setFrameShape(QFrame.Shape.HLine)
        line_r.setFixedHeight(1)
        line_r.setStyleSheet(f"background: {C.BORDER}; border: none;")

        sepl.addWidget(line_l, 1)
        sepl.addWidget(sep_lbl)
        sepl.addWidget(line_r, 1)
        cl.addWidget(sep_row)

        cl.addSpacing(6)

        row, _ = self._toggle_row(
            "Copia automática al iniciar",
            "Genera una copia cada vez que abres TagFil", True
        )
        cl.addWidget(row)
        cl.addStretch()

        btn_now.clicked.connect(self._on_backup_now)
        return card

    def _card_integraciones(self) -> QWidget:
        """Tarjeta ancha (ocupa las 2 columnas) con toggles de servicios en la nube."""
        card, cl = self._make_card(glow=False)
        cl.addWidget(self._card_header(_SVG_CLOUD, "Integraciones"))
        cl.addWidget(self._divider())

        sub = QLabel("Conecta TagFil con servicios de almacenamiento en la nube")
        sub.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
        cl.addWidget(sub)

        integrations = [
            (_SVG_ONEDRIVE,   "OneDrive",     "Sincroniza con tu cuenta de Microsoft OneDrive",  True),
            (_SVG_GDRIVE,     "Google Drive", "Sincroniza con tu cuenta de Google Drive",         True),
            (_SVG_SHAREPOINT, "SharePoint",   "Sincroniza con tu sitio de SharePoint corporativo", False),
        ]

        self._integration_toggles: dict[str, ToggleSwitch] = {}

        for i, (svg, name, subtitle, checked) in enumerate(integrations):
            row, toggle = self._integration_row(svg, name, subtitle, checked)
            cl.addWidget(row)
            self._integration_toggles[name] = toggle
            if i < len(integrations) - 1:
                cl.addWidget(self._divider())

        cl.addSpacing(10)

        # ── Botón Guardar cambios alineado a la derecha ────────────
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.addStretch()

        btn_save = QPushButton("  Guardar cambios")
        btn_save.setFixedHeight(42)
        btn_save.setMinimumWidth(180)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:0.5 #A855F7, stop:1 #C026D3);
                color: white;
                border: none;
                border-radius: 11px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.4px;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333EA, stop:0.5 #C026D3, stop:1 #DB2777);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C3AED, stop:1 #A855F7);
            }}
        """)
        save_shadow = QGraphicsDropShadowEffect()
        save_shadow.setBlurRadius(32)
        save_shadow.setOffset(0, 6)
        save_shadow.setColor(QColor("#C026D3AA"))
        btn_save.setGraphicsEffect(save_shadow)
        btn_save.clicked.connect(self._on_save_integrations)

        brl.addWidget(btn_save)
        cl.addWidget(btn_row)

        # Degradado decorativo debajo del botón guardar
        glow_line = QWidget()
        glow_line.setFixedHeight(8)
        glow_line.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.3 rgba(168, 85, 247, 60),
                stop:0.5 rgba(192, 38, 211, 80),
                stop:0.7 rgba(168, 85, 247, 60),
                stop:1 transparent);
            border: none;
            border-radius: 4px;
        """)
        cl.addWidget(glow_line)

        return card

    def _card_seguridad(self) -> QWidget:
        card, cl = self._make_card(glow=True)
        cl.addWidget(self._card_header(_SVG_SHIELD, "Seguridad"))
        cl.addWidget(self._divider())

        self._security_rows: dict[str, tuple[QLabel, QLabel]] = {}
        labels = {
            "database": "Base de datos",
            "backup-hash": "Integridad backup",
            "encrypted-backup": "Backup cifrado",
            "app-dir": "Carpeta de app",
            "context-menu": "Menú contextual",
        }
        for i, (key, label) in enumerate(labels.items()):
            row, badge, detail = self._status_row(label)
            cl.addWidget(row)
            self._security_rows[key] = (badge, detail)
            if i < len(labels) - 1:
                cl.addWidget(self._divider())

        self._encrypted_hint = QLabel()
        self._encrypted_hint.setWordWrap(True)
        self._encrypted_hint.setStyleSheet(
            f"font-size: 11px; color: {C.TEXT3}; background: transparent;"
        )
        cl.addWidget(self._encrypted_hint)

        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.addStretch()
        self._btn_refresh_security = self._plain_button("Actualizar")
        self._btn_refresh_security.clicked.connect(self.refresh)
        brl.addWidget(self._btn_refresh_security)
        cl.addWidget(btn_row)
        return card

    def _card_actividad(self) -> QWidget:
        card, cl = self._make_card()
        cl.addWidget(self._card_header(_SVG_ACTIVITY, "Actividad reciente"))
        cl.addWidget(self._divider())

        self._activity_layout = QVBoxLayout()
        self._activity_layout.setContentsMargins(0, 0, 0, 0)
        self._activity_layout.setSpacing(8)
        cl.addLayout(self._activity_layout)
        cl.addStretch()
        return card

    # ── slots ─────────────────────────────────────────────────────────

    def refresh(self):
        self._refresh_security()
        self._refresh_activity()

    def _refresh_security(self):
        try:
            findings = {item["check"]: item for item in run_security_audit()}
            for key, (badge, detail) in self._security_rows.items():
                item = findings.get(key, {"status": "info", "detail": "Sin datos"})
                status = item["status"]
                badge.setText(status.upper())
                badge.setStyleSheet(self._badge_style(status))
                text = str(item["detail"])
                detail.setText(text if len(text) <= 34 else text[:31] + "...")
                detail.setToolTip(text)

            if encrypted_backups_enabled():
                self._encrypted_hint.setText("Backup cifrado activo para este usuario de Windows.")
            else:
                self._encrypted_hint.setText(
                    "Para activar cifrado DPAPI inicia TagFil con TAGFIL_ENCRYPT_BACKUP=1."
                )
        except Exception as e:
            for badge, detail in self._security_rows.values():
                badge.setText("ERR")
                badge.setStyleSheet(self._badge_style("error"))
                detail.setText("No se pudo auditar")
                detail.setToolTip(str(e))

    def _refresh_activity(self):
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            events = db.get_audit_events(limit=6)
        except Exception as e:
            events = []
            err = QLabel(f"No se pudo cargar actividad: {e}")
            err.setWordWrap(True)
            err.setStyleSheet(f"font-size: 11px; color: {C.RED}; background: transparent;")
            self._activity_layout.addWidget(err)

        if not events:
            empty = QLabel("Aún no hay eventos registrados.")
            empty.setStyleSheet(f"font-size: 12px; color: {C.TEXT3}; background: transparent;")
            self._activity_layout.addWidget(empty)
            return

        action_names = {
            "file.upsert": "Archivo guardado",
            "file.rename": "Archivo renombrado",
            "file.trash": "Archivo enviado a papelera",
            "file.restore": "Archivo restaurado",
            "file.purge": "Archivo eliminado",
            "trash.empty": "Papelera vaciada",
            "tag.create": "Etiqueta creada",
            "tag.delete": "Etiqueta eliminada",
            "bulk.import": "Carpeta importada",
        }
        for event in events:
            row = QWidget()
            row.setStyleSheet(f"background: {C.BG4}; border: 1px solid {C.BORDER}; border-radius: 8px;")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(10, 8, 10, 8)
            rl.setSpacing(2)

            title = action_names.get(event["action"], event["action"])
            if event.get("file_name"):
                title = f"{title}: {event['file_name']}"
            lbl = QLabel(title)
            lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 700; color: {C.TEXT}; background: transparent;"
            )
            rl.addWidget(lbl)

            sub = QLabel(str(event.get("created_at", "")))
            sub.setStyleSheet(f"font-size: 10.5px; color: {C.TEXT3}; background: transparent;")
            rl.addWidget(sub)
            self._activity_layout.addWidget(row)

    def _on_backup_now(self):
        ok = db.backup_db(force=True)
        if ok:
            self.refresh()

    def _on_save_integrations(self):
        """Guarda el estado de los toggles de integraciones."""
        state = {name: toggle.isChecked()
                 for name, toggle in self._integration_toggles.items()}
        # TODO: persistir `state` en la configuración de la app
        print("[Integraciones] Estado guardado:", state)
"""
dialogs.py — Diálogo de descripción de InfoFile

Se abre al hacer clic derecho en el Explorador de Windows.
Estilo: fondo blanco, tipografía oscura, botón morado.

Uso:
    from PyQt6.QtWidgets import QApplication
    from dialogs import DescriptionDialog
    app = QApplication(sys.argv)
    DescriptionDialog("C:/ruta/archivo.pdf").exec()
"""

import sys
from pathlib import Path

from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
)

import database as db
from config import APP_NAME, ICON_PATH, get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Estilos — fondo blanco como en la imagen
# ──────────────────────────────────────────────

_STYLE = """
QDialog {
    background-color: #ffffff;
    color: #1a1a1a;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* Barra de título personalizada */
QWidget#titlebar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e5e5;
}
QLabel#title_app {
    color: #1a1a1a;
    font-size: 13px;
    font-weight: 400;
}
QLabel#title_sep {
    color: #888888;
    font-size: 13px;
}
QLabel#title_action {
    color: #1a1a1a;
    font-size: 13px;
    font-weight: 400;
}

/* Cuerpo */
QWidget#body {
    background-color: #ffffff;
}

/* Etiquetas de sección */
QLabel#section_label {
    color: #1a1a1a;
    font-size: 13px;
    font-weight: 700;
}

/* Nombre del archivo */
QLabel#file_name {
    color: #1a1a1a;
    font-size: 13px;
    font-weight: 400;
}

/* Textarea de descripción */
QTextEdit#desc_input {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 10px;
    font-size: 13px;
    font-family: "Segoe UI", sans-serif;
}
QTextEdit#desc_input:focus {
    border: 1px solid #7c3aed;
    outline: none;
}

/* Zona de etiquetas */
QWidget#tags_box {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
}
QLineEdit#tag_input {
    background-color: transparent;
    border: none;
    color: #1a1a1a;
    font-size: 13px;
    font-family: "Segoe UI", sans-serif;
    padding: 4px 2px;
}
QLineEdit#tag_input:focus {
    outline: none;
}

QLineEdit#meta_input {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 7px 9px;
    font-size: 12px;
    font-family: "Segoe UI", sans-serif;
}
QLineEdit#meta_input:focus {
    border: 1px solid #7c3aed;
}
QLineEdit#suggested_name {
    background-color: #fafafa;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px 9px;
    font-size: 12px;
    font-family: "Consolas", "Segoe UI", monospace;
}
QPushButton#btn_secondary {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: "Segoe UI", sans-serif;
}
QPushButton#btn_secondary:hover {
    border-color: #7c3aed;
    color: #5b21b6;
}

/* Chip de etiqueta */
QWidget#chip {
    background-color: #ffffff;
    border: 1px solid #c0c0c0;
    border-radius: 14px;
}
QLabel#chip_label {
    color: #1a1a1a;
    font-size: 12px;
    padding: 0px;
    background: transparent;
}
QPushButton#chip_btn {
    background-color: transparent;
    color: #888888;
    border: none;
    font-size: 13px;
    padding: 0px;
    min-width: 14px;
    max-width: 14px;
    min-height: 14px;
    max-height: 14px;
}
QPushButton#chip_btn:hover {
    color: #333333;
}

/* Botones principales */
QPushButton#btn_guardar {
    background-color: #7c3aed;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 28px;
    font-size: 14px;
    font-weight: 600;
    font-family: "Segoe UI", sans-serif;
    min-width: 110px;
}
QPushButton#btn_guardar:hover {
    background-color: #6d28d9;
}
QPushButton#btn_guardar:pressed {
    background-color: #5b21b6;
}
QPushButton#btn_cancelar {
    background-color: transparent;
    color: #1a1a1a;
    border: none;
    padding: 10px 20px;
    font-size: 14px;
    font-family: "Segoe UI", sans-serif;
    min-width: 90px;
}
QPushButton#btn_cancelar:hover {
    color: #555555;
}

/* Separador */
QFrame#sep {
    background-color: #e5e5e5;
    max-height: 1px;
    border: none;
}
"""


# ──────────────────────────────────────────────
# Chip de etiqueta
# ──────────────────────────────────────────────

class TagChip(QWidget):
    """Etiqueta visual con borde redondeado y botón ×."""

    def __init__(self, tag: str, on_remove, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.setObjectName("chip")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(5)

        lbl = QLabel(tag)
        lbl.setObjectName("chip_label")

        btn = QPushButton("×")
        btn.setObjectName("chip_btn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: on_remove(tag))
        btn.setFixedSize(14, 14)

        layout.addWidget(lbl)
        layout.addWidget(btn)
        self.setFixedHeight(28)


# ──────────────────────────────────────────────
# Zona de etiquetas
# ──────────────────────────────────────────────

class TagsBox(QWidget):
    """
    Caja de etiquetas con chips y campo de texto integrado.
    Reproduce exactamente el estilo de la imagen de referencia.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: list[str] = []
        self.setObjectName("tags_box")

        # Layout principal vertical dentro de la caja
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # Fila de chips (scroll horizontal si hay muchos)
        self._chips_row = QWidget()
        self._chips_row.setStyleSheet("background: transparent;")
        self._chips_layout = QHBoxLayout(self._chips_row)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Input de texto
        self._input = QLineEdit()
        self._input.setObjectName("tag_input")
        self._input.setPlaceholderText("Agregar etiqueta...")
        self._input.returnPressed.connect(self._add_from_input)
        self._input.textChanged.connect(self._on_text_changed)

        outer.addWidget(self._chips_row)
        outer.addWidget(self._input)

    def _on_text_changed(self, text: str) -> None:
        if "," in text:
            parts = text.split(",")
            for p in parts[:-1]:
                self._add_tag(p.strip())
            self._input.setText(parts[-1].lstrip())

    def _add_from_input(self) -> None:
        tag = self._input.text().strip().rstrip(",")
        if tag:
            self._add_tag(tag)
        self._input.clear()

    def _add_tag(self, tag: str) -> None:
        tag = tag.lower().strip()
        if not tag or tag in self._tags:
            return
        self._tags.append(tag)
        chip = TagChip(tag, self._remove_tag, self._chips_row)
        self._chips_layout.addWidget(chip)

    def _remove_tag(self, tag: str) -> None:
        if tag in self._tags:
            self._tags.remove(tag)
        # Reconstruir chips
        for i in reversed(range(self._chips_layout.count())):
            item = self._chips_layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w:
                w.deleteLater()
        for t in self._tags:
            chip = TagChip(t, self._remove_tag, self._chips_row)
            self._chips_layout.addWidget(chip)

    def get_tags(self) -> list[str]:
        pending = self._input.text().strip()
        if pending:
            self._add_tag(pending)
            self._input.clear()
        return list(self._tags)

    def set_tags(self, tags: list[str]) -> None:
        self._tags = []
        for i in reversed(range(self._chips_layout.count())):
            item = self._chips_layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w:
                w.deleteLater()
        for t in tags:
            self._add_tag(t)


# ──────────────────────────────────────────────
# Diálogo principal
# ──────────────────────────────────────────────

class DescriptionDialog(QDialog):
    """
    Diálogo "InfoFile - Agregar descripción".
    Estilo blanco, fiel a la imagen de referencia.
    """

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = str(Path(file_path).resolve(strict=False))
        self._existing  = None
        self._setup_ui()
        self._load_existing()

    # ── UI ──────────────────────────────────────

    def _setup_ui(self) -> None:
        # Sin marco nativo — usamos barra personalizada
        self.setWindowTitle(f"{APP_NAME} - Agregar descripción")
        self.setMinimumWidth(520)
        self.setMaximumWidth(580)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(_STYLE)

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        QShortcut(QKeySequence("Escape"), self, self.reject)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_body())

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setObjectName("body")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)

        # ── Sección Archivo ──
        lbl_archivo = QLabel("Archivo:")
        lbl_archivo.setObjectName("section_label")
        layout.addWidget(lbl_archivo)
        layout.addSpacing(6)

        path      = Path(self.file_path)
        file_name = path.name
        self._file_label = QLabel(file_name)
        self._file_label.setObjectName("file_name")
        self._file_label.setWordWrap(True)
        self._file_label.setToolTip(self.file_path)
        layout.addWidget(self._file_label)
        layout.addSpacing(20)

        lbl_short = QLabel("Nombre corto:")
        lbl_short.setObjectName("section_label")
        layout.addWidget(lbl_short)
        layout.addSpacing(8)
        layout.addWidget(self._build_short_name_box())
        layout.addSpacing(20)

        # ── Sección Descripción ──
        lbl_desc = QLabel("Descripción:")
        lbl_desc.setObjectName("section_label")
        layout.addWidget(lbl_desc)
        layout.addSpacing(8)

        self._desc_edit = QTextEdit()
        self._desc_edit.setObjectName("desc_input")
        self._desc_edit.setPlaceholderText(
            "Escribe una descripción para este archivo..."
        )
        self._desc_edit.setFixedHeight(120)
        self._desc_edit.setAcceptRichText(False)
        layout.addWidget(self._desc_edit)
        layout.addSpacing(20)

        # ── Sección Etiquetas ──
        lbl_tags = QLabel("Etiquetas:")
        lbl_tags.setObjectName("section_label")
        layout.addWidget(lbl_tags)
        layout.addSpacing(8)

        self._tags_box = TagsBox()
        self._tags_box.setMinimumHeight(80)
        layout.addWidget(self._tags_box)
        layout.addSpacing(28)

        # ── Botones ──
        layout.addWidget(self._build_buttons())

        return body

    def _build_short_name_box(self) -> QWidget:
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self._type_input = self._meta_input("factura")
        self._entity_input = self._meta_input("ACME")
        self._date_input = self._meta_input("2026-06-15")
        self._seq_input = self._meta_input("14")
        self._qualifier_input = self._meta_input("opcional")

        grid.addWidget(QLabel("Tipo"), 0, 0)
        grid.addWidget(QLabel("Entidad"), 0, 1)
        grid.addWidget(QLabel("Fecha/año"), 0, 2)
        grid.addWidget(QLabel("Consec."), 0, 3)
        grid.addWidget(self._type_input, 1, 0)
        grid.addWidget(self._entity_input, 1, 1)
        grid.addWidget(self._date_input, 1, 2)
        grid.addWidget(self._seq_input, 1, 3)

        grid.addWidget(QLabel("Calificador"), 2, 0)
        grid.addWidget(self._qualifier_input, 3, 0, 1, 2)

        self._suggested_name = QLineEdit()
        self._suggested_name.setObjectName("suggested_name")
        self._suggested_name.setReadOnly(True)
        self._suggested_name.setPlaceholderText("Genera una sugerencia...")
        grid.addWidget(self._suggested_name, 3, 2, 1, 2)

        btn_suggest = QPushButton("Sugerir")
        btn_suggest.setObjectName("btn_secondary")
        btn_suggest.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_suggest.clicked.connect(self._on_suggest_name)

        btn_rename = QPushButton("Renombrar")
        btn_rename.setObjectName("btn_secondary")
        btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rename.clicked.connect(self._on_rename_file)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(btn_suggest)
        row.addWidget(btn_rename)
        row.addStretch()
        grid.addLayout(row, 4, 0, 1, 4)

        for label in box.findChildren(QLabel):
            label.setStyleSheet("color: #555555; font-size: 11px; background: transparent;")

        return box

    def _meta_input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setObjectName("meta_input")
        inp.setPlaceholderText(placeholder)
        return inp

    def _build_buttons(self) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.setObjectName("btn_guardar")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setDefault(True)
        btn_guardar.clicked.connect(self._on_save)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_cancelar")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)

        row.addWidget(btn_guardar)
        row.addWidget(btn_cancelar)
        row.addStretch()

        return w

    # ── Lógica ──────────────────────────────────

    def _load_existing(self) -> None:
        try:
            db.init_db()
            existing = db.get_file(self.file_path)
            if existing:
                self._existing = existing
                self._desc_edit.setPlainText(existing["description"])
                self._tags_box.set_tags(existing["tags"])
                self._type_input.setText(existing.get("document_type") or "")
                self._entity_input.setText(existing.get("entity") or "")
                self._date_input.setText(existing.get("document_date") or "")
                seq = existing.get("sequence_number")
                self._seq_input.setText("" if seq in (None, "") else str(seq))
                self._qualifier_input.setText(existing.get("qualifier") or "")
                self._suggested_name.setText(existing.get("short_name") or "")
                # Cambiar título si ya tiene descripción
                self.setWindowTitle(f"{APP_NAME} - Editar descripción")
        except Exception as e:
            logger.exception(f"Error cargando datos: {e}")

    def _on_save(self) -> None:
        desc = self._desc_edit.toPlainText().strip()
        tags = self._tags_box.get_tags()
        seq_text = self._seq_input.text().strip()

        if not desc and not tags:
            QMessageBox.warning(
                self,
                "Sin datos",
                "Agrega una descripción o al menos una etiqueta.",
            )
            return

        try:
            sequence_number = int(seq_text) if seq_text else None
            db.upsert_file(
                path=self.file_path,
                description=desc,
                tags=tags,
                short_name=self._suggested_name.text().strip(),
                document_type=self._type_input.text().strip(),
                entity=self._entity_input.text().strip(),
                document_date=self._date_input.text().strip(),
                sequence_number=sequence_number,
                qualifier=self._qualifier_input.text().strip(),
                provider="local",
            )
            logger.info(f"Guardado: {self.file_path}")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Datos inválidos", str(e))
        except Exception as e:
            logger.exception(f"Error guardando: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")

    def _on_suggest_name(self) -> str | None:
        from core.naming import suggest_short_path

        try:
            seq_text = self._seq_input.text().strip()
            if not seq_text:
                raise ValueError("Ingresa un consecutivo.")
            suggested = suggest_short_path(
                original_path=self.file_path,
                document_type=self._type_input.text().strip(),
                entity=self._entity_input.text().strip(),
                document_date=self._date_input.text().strip() or None,
                sequence=int(seq_text),
                qualifier=self._qualifier_input.text().strip(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Nombre corto", str(e))
            return None

        self._suggested_name.setText(suggested.name)
        return suggested.name

    def _on_rename_file(self) -> None:
        name = self._suggested_name.text().strip() or self._on_suggest_name()
        if not name:
            return

        current = Path(self.file_path)
        target = current.with_name(name)

        if current.name == target.name:
            QMessageBox.information(self, "Renombrar", "El archivo ya tiene ese nombre.")
            return
        if not current.exists():
            QMessageBox.warning(self, "Renombrar", "El archivo no existe en disco.")
            return
        if target.exists():
            QMessageBox.warning(self, "Renombrar", f"Ya existe un archivo con ese nombre:\n{target}")
            return

        answer = QMessageBox.question(
            self,
            "Renombrar archivo",
            f"Renombrar:\n{current.name}\n\na:\n{target.name}",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            current.rename(target)
            db.update_file_path(self.file_path, str(target))
            self.file_path = str(target.resolve(strict=False))
            self._file_label.setText(target.name)
            self._file_label.setToolTip(self.file_path)
            logger.info(f"Renombrado: {current} -> {target}")
        except Exception as e:
            logger.exception(f"Error renombrando archivo: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo renombrar:\n{e}")


MetadataDialog = DescriptionDialog


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else __file__
    app  = QApplication(sys.argv)
    result = DescriptionDialog(path).exec()
    print("Guardado" if result == QDialog.DialogCode.Accepted else "Cancelado")

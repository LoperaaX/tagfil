"""
import_worker.py — Workers para importación segura de carpetas.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

import database as db
from config import get_logger
from security import sanitize_tags

logger = get_logger(__name__)

MAX_FILES = 5000
MAX_FILE_SIZE = 500 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx",
    ".txt", ".md", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".zip", ".rar", ".7z",
}

IGNORED_DIRS = {
    "$recycle.bin", ".git", ".hg", ".svn", "__pycache__", "node_modules",
    ".venv", "venv", "env", "build", "dist", "obj", "bin", ".idea", ".vscode",
}

IGNORED_NAMES = {"desktop.ini", "thumbs.db"}

KEYWORD_TAGS = {
    "factura": "factura",
    "invoice": "factura",
    "contrato": "contrato",
    "contract": "contrato",
    "recibo": "recibo",
    "informe": "informe",
    "reporte": "reporte",
    "certificado": "certificado",
    "cotizacion": "cotizacion",
    "propuesta": "propuesta",
}


def _suggest_tags(path: Path, root: Path) -> list[str]:
    tags = []
    ext = path.suffix.lower().lstrip(".")
    if ext:
        tags.append(ext)

    try:
        rel_parent = path.parent.relative_to(root)
        if rel_parent.parts:
            tags.extend(rel_parent.parts[-2:])
    except ValueError:
        pass

    haystack = f"{path.stem} {' '.join(path.parts)}".lower()
    for needle, tag in KEYWORD_TAGS.items():
        if needle in haystack:
            tags.append(tag)

    return sanitize_tags(tags)


class FolderScanWorker(QThread):
    progress = pyqtSignal(str, int, int)
    scan_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, folder: str):
        super().__init__()
        self.folder = folder
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            root = Path(self.folder).resolve(strict=False)
            if not root.exists() or not root.is_dir():
                self.error.emit("La carpeta seleccionada no existe.")
                return

            existing = {f["path"].lower() for f in db.list_all_files(check_exists=False)}
            items = []
            skipped_existing = 0
            skipped_unsupported = 0
            skipped_large = 0
            scanned = 0

            for current_root, dirs, files in os.walk(root, onerror=lambda e: logger.warning(str(e))):
                if self._cancelled:
                    return

                dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRS]

                for filename in files:
                    if self._cancelled:
                        return

                    path = Path(current_root) / filename
                    scanned += 1
                    if scanned % 50 == 0:
                        self.progress.emit("Escaneando carpeta", scanned, MAX_FILES)

                    name_lower = path.name.lower()
                    if name_lower in IGNORED_NAMES or name_lower.startswith("~$"):
                        skipped_unsupported += 1
                        continue

                    ext = path.suffix.lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        skipped_unsupported += 1
                        continue

                    try:
                        size = path.stat().st_size
                    except OSError:
                        skipped_unsupported += 1
                        continue

                    if size > MAX_FILE_SIZE:
                        skipped_large += 1
                        continue

                    normalized = str(path.resolve(strict=False))
                    if normalized.lower() in existing:
                        skipped_existing += 1
                        continue

                    items.append({
                        "path": normalized,
                        "name": path.name,
                        "tags": _suggest_tags(path, root),
                        "size": size,
                    })

                    if len(items) >= MAX_FILES:
                        break

                if len(items) >= MAX_FILES:
                    break

            self.scan_ready.emit({
                "folder": str(root),
                "items": items,
                "scanned": scanned,
                "new": len(items),
                "skipped_existing": skipped_existing,
                "skipped_unsupported": skipped_unsupported,
                "skipped_large": skipped_large,
                "limited": len(items) >= MAX_FILES,
            })

        except Exception as e:
            logger.exception(f"Error escaneando carpeta: {e}")
            self.error.emit(str(e))


class FolderImportWorker(QThread):
    progress = pyqtSignal(str, int, int)
    completed = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, scan_result: dict):
        super().__init__()
        self.scan_result = scan_result
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        imported = 0
        failed = 0
        items = self.scan_result.get("items", [])
        total = len(items)
        try:
            for index, item in enumerate(items, start=1):
                if self._cancelled:
                    break
                try:
                    db.upsert_file(
                        path=item["path"],
                        description="",
                        tags=item.get("tags", []),
                    )
                    imported += 1
                except Exception:
                    failed += 1
                    logger.exception(f"No se pudo importar: {item.get('path')}")

                self.progress.emit("Importando archivos", index, total)

            db.log_audit_event(
                "bulk.import",
                details={
                    "folder_hash": db.hash_path(self.scan_result.get("folder", "")),
                    "imported": imported,
                    "failed": failed,
                    "scanned": self.scan_result.get("scanned", 0),
                    "skipped_existing": self.scan_result.get("skipped_existing", 0),
                },
            )
            self.completed.emit({"imported": imported, "failed": failed, "total": total})

        except Exception as e:
            logger.exception(f"Error importando carpeta: {e}")
            self.error.emit(str(e))

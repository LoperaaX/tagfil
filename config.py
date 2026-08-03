"""
config.py — Configuración central de TagFil

Todos los módulos importan desde aquí.
Nunca hardcodees rutas, versiones o constantes en otros archivos.

Uso:
    from config import APP_DIR, DB_PATH, get_logger
"""

import logging
import os
import sys
from pathlib import Path


# ──────────────────────────────────────────────
# Versión
# ──────────────────────────────────────────────

APP_NAME      = "TagFil"
APP_VERSION   = "0.1.0"
APP_AUTHOR    = "Tu nombre"


# ──────────────────────────────────────────────
# Directorios
# ──────────────────────────────────────────────

# Raíz de datos: %APPDATA%\InfoFile en Windows, ~/.InfoFile en otros sistemas
if sys.platform == "win32":
    _base = Path(os.getenv("APPDATA", Path.home()))
else:
    _base = Path.home()

APP_DIR        = _base / APP_NAME          # %APPDATA%\TagFil
DB_PATH        = APP_DIR / "tagfil.db"
LEGACY_DB_PATH = APP_DIR / "infofile.db"
LOG_DIR    = APP_DIR / "logs"
ASSETS_DIR = Path(__file__).parent / "assets"   # relativo al proyecto

# Crear directorios al importar (idempotente)
APP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

if LEGACY_DB_PATH.exists() and not DB_PATH.exists():
    import shutil
    shutil.copy2(LEGACY_DB_PATH, DB_PATH)


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

# Nivel según variable de entorno (útil para desarrollo)
# Ejemplo: set INFOFILE_LOG=DEBUG  →  activa logs de depuración
_LOG_LEVEL = os.getenv("TAGFIL_LOG", os.getenv("INFOFILE_LOG", "INFO")).upper()
_LOG_FILE  = LOG_DIR / "tagfil.log"

# Formato: timestamp [NIVEL] módulo: mensaje
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _setup_logging() -> None:
    """
    Configura logging una sola vez para toda la app.
    - Archivo rotativo: máx 1 MB, guarda 3 backups.
    - Consola: solo en desarrollo (cuando INFOFILE_LOG está definido).

    Llamar solo desde main.py o al importar config por primera vez.
    """
    from logging.handlers import RotatingFileHandler

    root = logging.getLogger()

    # Evitar duplicar handlers si se llama más de una vez
    if root.handlers:
        return

    root.setLevel(_LOG_LEVEL)

    # Handler de archivo (rotativo)
    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=1_000_000,   # 1 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    # Handler de consola (solo si se pide explícitamente o en desarrollo)
    if os.getenv("TAGFIL_LOG") or os.getenv("INFOFILE_LOG"):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
        root.addHandler(console_handler)


# Inicializar al importar
_setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger con el nombre dado.

    Uso en cualquier módulo:
        from config import get_logger
        logger = get_logger(__name__)
        logger.info("Iniciando...")
    """
    return logging.getLogger(name)


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────

WINDOW_TITLE    = f"{APP_NAME} {APP_VERSION}"
WINDOW_MIN_W    = 700
WINDOW_MIN_H    = 500
TRAY_TOOLTIP    = f"{APP_NAME} — Descripciones inteligentes para tus archivos"

# Icono principal (puede no existir en desarrollo)
ICON_PATH = ASSETS_DIR / "icon.ico"


# ──────────────────────────────────────────────
# Búsqueda
# ──────────────────────────────────────────────

SEARCH_DEBOUNCE_MS = 300    # milisegundos antes de lanzar búsqueda al escribir
SEARCH_MAX_RESULTS = 200    # límite de resultados mostrados en la UI


# ──────────────────────────────────────────────
# Registro de Windows (menú contextual)
# ──────────────────────────────────────────────

# Clave raíz del menú contextual en el registro
REGISTRY_KEY = r"*\shell\TagFil"
REGISTRY_LABEL = "TagFil"


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info(f"{APP_NAME} v{APP_VERSION} iniciado")
    logger.debug(f"APP_DIR : {APP_DIR}")
    logger.debug(f"DB_PATH : {DB_PATH}")
    logger.debug(f"LOG_DIR : {LOG_DIR}")
    logger.debug(f"Log level: {_LOG_LEVEL}")

    print(f"\n{'─' * 40}")
    print(f"  {APP_NAME} {APP_VERSION}")
    print(f"{'─' * 40}")
    print(f"  APP_DIR  : {APP_DIR}")
    print(f"  DB_PATH  : {DB_PATH}")
    print(f"  LOG_DIR  : {LOG_DIR}")
    print(f"  LOG_FILE : {_LOG_FILE}")
    print(f"  Log level: {_LOG_LEVEL}")
    print(f"{'─' * 40}\n")

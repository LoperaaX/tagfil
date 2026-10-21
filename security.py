"""
security.py — Seguridad de TagFil

Implementa tres capas de seguridad:

  1. Instancia única (Mutex) — evita múltiples instancias simultáneas
     que podrían corromper la DB con escrituras concurrentes.

  2. Validación e integridad — valida rutas, sanitiza descripciones,
     verifica hashes de backup.

  3. Protección de logs — asegura que los logs no expongan
     contenido sensible de las descripciones.

Uso:
    from security import ensure_single_instance, validate_path,
                         sanitize_description, verify_backup_hash
"""

import ctypes
import hashlib
import os
import re
import sys
from pathlib import Path, PureWindowsPath

from config import APP_NAME, DB_PATH, APP_DIR, get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Capa 2 — Instancia única (Mutex de Windows)
# ──────────────────────────────────────────────

_mutex_handle = None

def ensure_single_instance() -> bool:
    """
    Garantiza que solo corra una instancia de TagFil a la vez (por sesión de usuario).

    Crea un Mutex de sistema con nombre único. Si ya existe,
    significa que hay otra instancia corriendo — retorna False.

    Retorna True si esta es la única instancia (ok para continuar).
    Retorna False si ya hay otra instancia corriendo.

    El Mutex se libera automáticamente cuando el proceso termina.

    Uso en main.py:
        from security import ensure_single_instance
        if not ensure_single_instance():
            # Enfocar ventana existente y salir
            _focus_existing_window()
            sys.exit(0)
    """
    global _mutex_handle

    # «Local\\»: una instancia por sesión. Con «Global\\» un segundo usuario de la
    # misma PC (cambio rápido de usuario / RDP) no podría abrir TagFil.
    mutex_name = f"Local\\{APP_NAME}_SingleInstance_Mutex"

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateMutexW(
            None,   # sin atributos de seguridad
            True,   # este proceso es el dueño inicial
            mutex_name,
        )

        if handle == 0:
            logger.error("No se pudo crear el mutex de instancia única")
            return True   # permitir continuar si falla la creación

        last_error = ctypes.get_last_error()

        if last_error == 183:   # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            logger.info("Ya existe otra instancia de TagFil corriendo")
            return False

        # Esta es la instancia principal — guardar handle para no liberar
        _mutex_handle = handle
        logger.debug("Mutex de instancia única creado correctamente")
        return True

    except Exception as e:
        logger.warning(f"Error en ensure_single_instance: {e}")
        return True   # permitir continuar en caso de error inesperado


def release_single_instance() -> None:
    """
    Libera el mutex explícitamente al cerrar la app.
    Normalmente no es necesario (Windows lo libera al terminar el proceso),
    pero es buena práctica llamarlo desde tray._quit().
    """
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.ReleaseMutex(_mutex_handle)
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        logger.debug("Mutex de instancia única liberado")


def focus_existing_window() -> None:
    """
    Intenta enfocar la ventana de la instancia ya corriendo.
    Busca por título de ventana usando EnumWindows.
    """
    try:
        import ctypes.wintypes

        target_titles = {APP_NAME}
        found = ctypes.wintypes.HWND(0)

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM,
        )

        def callback(hwnd, lparam):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if title in target_titles:
                    # Un Explorador abierto en una carpeta «TagFil» también tiene ese
                    # título: solo se acepta una ventana Qt.
                    cls = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetClassNameW(hwnd, cls, 256)
                    if cls.value.startswith("Qt"):
                        found.value = hwnd
                        return False   # detener enumeración
            return True

        ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)

        if found.value:
            # Restaurar si está minimizada y enfocar
            SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(found.value, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(found.value)
            logger.info("Ventana existente enfocada")

    except Exception as e:
        logger.warning(f"No se pudo enfocar ventana existente: {e}")


# ──────────────────────────────────────────────
# Capa 3 — Validación de rutas
# ──────────────────────────────────────────────

# Caracteres inválidos en rutas de Windows
_INVALID_PATH_CHARS = set('<>"|?*\x00')

# Nombres reservados de Windows que no pueden ser rutas válidas
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def validate_path(path: str) -> tuple[bool, str]:
    """
    Valida que una ruta sea segura para guardar en la DB.

    Retorna (True, ruta_normalizada) si es válida.
    Retorna (False, mensaje_error) si no es válida.

    Validaciones:
    - No vacía
    - Sin caracteres inválidos de Windows
    - Sin nombres reservados del sistema
    - Longitud razonable (MAX_PATH = 260, pero OneDrive puede ir más)
    - Sin inyección de path traversal (../../etc)
    - Ruta absoluta
    """
    if not path or not path.strip():
        return False, "La ruta no puede estar vacía"

    path = path.strip()

    if any((ord(c) < 32 or ord(c) == 127) for c in path):
        return False, "La ruta contiene caracteres de control no permitidos"

    # Verificar longitud máxima
    if len(path) > 32767:   # límite extendido de Windows
        return False, f"Ruta demasiado larga ({len(path)} caracteres)"

    if sys.platform == "win32":
        win_path = PureWindowsPath(path)
        drive = win_path.drive
        remainder = path[len(drive):] if drive else path
        if ":" in remainder:
            return False, "La ruta no puede incluir Alternate Data Streams (:stream)"

        if path.startswith(("\\\\.\\", "\\\\?\\")):
            return False, "Las rutas de dispositivo no están permitidas"

    # Verificar caracteres inválidos
    invalid = _INVALID_PATH_CHARS.intersection(set(path))
    if invalid:
        return False, f"Caracteres inválidos en la ruta: {invalid}"

    # Verificar que sea ruta absoluta
    p = Path(path)
    if not p.is_absolute():
        return False, "La ruta debe ser absoluta (ej: C:\\carpeta\\archivo)"

    # Verificar nombres reservados
    for part in p.parts:
        name_upper = part.upper().split(".")[0]
        if name_upper in _RESERVED_NAMES:
            return False, f"Nombre reservado del sistema: {part}"

    # Verificar path traversal: solo cuenta «..» como componente completo
    # (un archivo llamado «informe..final.pdf» es válido)
    if ".." in p.parts:
        return False, "La ruta contiene secuencias '..' no permitidas"
    try:
        resolved = str(p.resolve(strict=False))
    except Exception as e:
        return False, f"Ruta inválida: {e}"

    return True, resolved


# ──────────────────────────────────────────────
# Capa 3 — Sanitización de descripciones
# ──────────────────────────────────────────────

_MAX_DESCRIPTION_LEN = 2000   # caracteres máximos
_MAX_TAG_LEN         = 50     # caracteres máximos por tag
_MAX_TAGS            = 20     # tags máximas por archivo


def sanitize_description(text: str) -> str:
    """
    Sanitiza el texto de una descripción.

    - Elimina caracteres de control (excepto saltos de línea y tabs)
    - Normaliza espacios múltiples
    - Trunca a MAX_DESCRIPTION_LEN caracteres
    - Elimina HTML/scripts si los hubiera
    """
    if not text:
        return ""

    # Eliminar caracteres de control excepto \n, \r, \t
    text = "".join(
        c for c in text
        if c in ("\n", "\r", "\t") or (ord(c) >= 32 and ord(c) != 127)
    )

    # Eliminar etiquetas HTML reales (<b>, </div>, <script ...>). Exige una letra o «/»
    # tras «<», así «Valor < 100 y > 50» o «<3» se conservan intactos.
    text = re.sub(r"</?[A-Za-z][^<>]{0,200}>", "", text)

    # Normalizar espacios (pero mantener saltos de línea)
    lines = text.splitlines()
    lines = [" ".join(line.split()) for line in lines]
    text  = "\n".join(lines)

    # Truncar
    if len(text) > _MAX_DESCRIPTION_LEN:
        text = text[:_MAX_DESCRIPTION_LEN].rstrip()
        logger.debug(f"Descripción truncada a {_MAX_DESCRIPTION_LEN} caracteres")

    return text.strip()


def sanitize_tags(tags: list[str]) -> list[str]:
    """
    Sanitiza y valida una lista de tags.

    - Normaliza a minúsculas
    - Convierte espacios en guiones y elimina caracteres especiales
      (solo letras, números, guiones, puntos)
    - Trunca tags largas
    - Limita el número total de tags
    - Elimina duplicados manteniendo orden
    """
    if not tags:
        return []

    clean = []
    seen  = set()

    for tag in tags[:_MAX_TAGS * 2]:   # procesar solo el doble del límite
        if not tag or not tag.strip():
            continue

        # Normalizar
        t = tag.strip().lower()

        # Espacios → guion, para no fusionar palabras («cuenta de cobro»)
        t = re.sub(r"\s+", "-", t)

        # Solo permitir letras, números, guiones, guiones bajos, puntos
        t = re.sub(r"[^\w\-\.]", "", t, flags=re.UNICODE).strip("-.")

        # Truncar
        if len(t) > _MAX_TAG_LEN:
            t = t[:_MAX_TAG_LEN]

        # Filtrar vacíos y duplicados
        if t and t not in seen:
            clean.append(t)
            seen.add(t)

        if len(clean) >= _MAX_TAGS:
            break

    return clean


# ──────────────────────────────────────────────
# Capa 3 — Verificación de integridad del backup
# ──────────────────────────────────────────────

_HASH_FILE = APP_DIR / "tagfil_backup.sha256"
_ENCRYPTED_BACKUP = APP_DIR / "tagfil_backup.db.dpapi"


def save_backup_hash() -> bool:
    """
    Calcula y guarda el hash SHA-256 del archivo de backup.
    Llamar inmediatamente después de crear el backup.
    """
    backup_path = APP_DIR / "tagfil_backup.db"

    if not backup_path.exists():
        return False

    try:
        sha256 = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        hash_hex = sha256.hexdigest()
        _HASH_FILE.write_text(hash_hex, encoding="utf-8")
        logger.debug(f"Hash del backup guardado: {hash_hex[:16]}...")
        return True

    except Exception as e:
        logger.warning(f"Error guardando hash del backup: {e}")
        return False


def verify_backup_hash() -> tuple[bool, str]:
    """
    Verifica la integridad del backup comparando su hash actual
    con el hash guardado previamente.

    Retorna (True, "ok") si el backup está íntegro.
    Retorna (False, mensaje) si está corrupto o no hay hash guardado.
    """
    backup_path = APP_DIR / "tagfil_backup.db"

    if not backup_path.exists():
        return False, "Archivo de backup no encontrado"

    if not _HASH_FILE.exists():
        return False, "No hay hash guardado para este backup"

    try:
        expected = _HASH_FILE.read_text(encoding="utf-8").strip()

        sha256 = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        actual = sha256.hexdigest()

        if actual == expected:
            logger.debug("Integridad del backup verificada correctamente")
            return True, "ok"
        else:
            logger.error(
                f"Hash del backup no coincide. "
                f"Esperado: {expected[:16]}... "
                f"Actual: {actual[:16]}..."
            )
            return False, "El backup puede estar corrupto (hash no coincide)"

    except Exception as e:
        logger.exception(f"Error verificando hash del backup: {e}")
        return False, f"Error al verificar: {e}"


# ──────────────────────────────────────────────
# Capa 3 — Backup cifrado opcional
# ──────────────────────────────────────────────

def encrypted_backups_enabled() -> bool:
    """Retorna True si el backup cifrado con DPAPI está activado."""
    try:
        from tagfil.settings import get_settings
        return bool(get_settings().get("encrypt_backup"))
    except Exception:
        return False


def encrypted_backup_path() -> Path:
    """Ruta del backup cifrado opcional."""
    return _ENCRYPTED_BACKUP


def _dpapi_protect(data: bytes) -> bytes:
    """Cifra bytes con Windows DPAPI para el usuario actual."""
    if sys.platform != "win32":
        raise OSError("DPAPI solo está disponible en Windows")

    import ctypes.wintypes as wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    in_buffer = ctypes.create_string_buffer(data)
    in_blob = DATA_BLOB(
        len(data),
        ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    out_blob = DATA_BLOB()

    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "TagFil backup",
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def encrypt_backup_if_enabled() -> bool:
    """
    Crea un backup cifrado con DPAPI si la preferencia encrypt_backup está activa.
    El archivo solo puede descifrarse con el mismo usuario de Windows.
    """
    if not encrypted_backups_enabled():
        return False

    backup_path = APP_DIR / "tagfil_backup.db"
    if not backup_path.exists():
        return False

    try:
        encrypted = _dpapi_protect(backup_path.read_bytes())
        tmp = _ENCRYPTED_BACKUP.with_suffix(".dpapi.tmp")
        tmp.write_bytes(encrypted)
        os.replace(tmp, _ENCRYPTED_BACKUP)
        logger.info(f"Backup cifrado creado: {_ENCRYPTED_BACKUP}")
        return True
    except Exception as e:
        logger.warning(f"No se pudo crear backup cifrado: {e}")
        return False


# ──────────────────────────────────────────────
# Capa 3 — Auditoría de seguridad
# ──────────────────────────────────────────────

def run_security_audit() -> list[dict]:
    """Ejecuta verificaciones rápidas de seguridad y retorna hallazgos."""
    findings = []

    def add(status: str, check: str, detail: str) -> None:
        findings.append({"status": status, "check": check, "detail": detail})

    if DB_PATH.exists():
        try:
            import sqlite3
            with sqlite3.connect(DB_PATH) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            add("ok" if result == "ok" else "error", "database", result)
        except Exception as e:
            add("error", "database", f"No se pudo verificar: {e}")
    else:
        add("warn", "database", "La base de datos no existe todavía")

    ok, msg = verify_backup_hash()
    add("ok" if ok else "warn", "backup-hash", msg)

    if encrypted_backups_enabled():
        encrypted_exists = _ENCRYPTED_BACKUP.exists()
        add(
            "ok" if encrypted_exists else "warn",
            "encrypted-backup",
            str(_ENCRYPTED_BACKUP) if encrypted_exists else "Activado, pero aún no existe backup cifrado",
        )
    else:
        add("info", "encrypted-backup", "Desactivado. Actívalo en Configuración.")

    try:
        test_path = APP_DIR / "audit-write.tmp"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
        add("ok", "app-dir", str(APP_DIR))
    except Exception as e:
        add("error", "app-dir", f"No se puede escribir en {APP_DIR}: {e}")

    try:
        import context_menu
        add(
            "ok" if context_menu.is_installed() else "info",
            "context-menu",
            "Instalado" if context_menu.is_installed() else "No instalado",
        )
    except Exception as e:
        add("warn", "context-menu", f"No se pudo verificar: {e}")

    return findings


# ──────────────────────────────────────────────
# Capa 3 — Protección de logs
# ──────────────────────────────────────────────

def safe_log_path(path: str) -> str:
    """
    Versión segura de una ruta para logging.
    Oculta el nombre de usuario para no exponer datos personales en logs.

    Ejemplo:
      C:\\Users\\Luis Lopera\\Documents\\archivo.pdf
      → C:\\Users\\[usuario]\\Documents\\archivo.pdf
    """
    try:
        import re as _re
        return _re.sub(
            r"(C:\\Users\\)[^\\]+",
            r"\1[usuario]",
            path,
            flags=_re.IGNORECASE,
        )
    except Exception:
        return "[ruta oculta]"


def safe_log_description(desc: str, max_chars: int = 30) -> str:
    """
    Versión segura de una descripción para logging.
    Muestra solo los primeros caracteres para no exponer contenido sensible.
    """
    if not desc:
        return "[vacía]"
    preview = desc[:max_chars].replace("\n", " ")
    return f"{preview}..." if len(desc) > max_chars else preview


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'─' * 50}")
    print(f"  {APP_NAME} — Pruebas de seguridad")
    print(f"{'─' * 50}\n")

    # Test instancia única
    result = ensure_single_instance()
    print(f"  Instancia única : {'OK — esta es la primera instancia' if result else 'Ya hay otra instancia corriendo'}")

    # Test validación de rutas
    test_paths = [
        r"C:\Users\Luis\Documents\archivo.pdf",
        r"C:\Users\Luis\..\windows\system32",
        r"../etc/passwd",
        r"CON",
        r"",
        r"D:\VS CODE\InfoFile\config.py",
    ]
    print(f"\n  Validación de rutas:")
    for p in test_paths:
        ok, msg = validate_path(p)
        status = "OK " if ok else "ERR"
        print(f"    {status}  {repr(p)[:45]:<46} {'' if ok else '→ ' + msg}")

    # Test sanitización
    print(f"\n  Sanitización de descripción:")
    desc = "  Documento <script>alert('xss')</script> con   espacios   extras  "
    clean = sanitize_description(desc)
    print(f"    Entrada : {repr(desc)}")
    print(f"    Salida  : {repr(clean)}")

    # Test tags
    print(f"\n  Sanitización de tags:")
    tags = ["  USB  ", "SEGURIDAD", "usb", "tag con espacios", "válido-tag", ""]
    clean_tags = sanitize_tags(tags)
    print(f"    Entrada : {tags}")
    print(f"    Salida  : {clean_tags}")

    # Test logs seguros
    print(f"\n  Logs seguros:")
    path = r"C:\Users\Luis Lopera\Documents\confidencial.pdf"
    print(f"    Original : {path}")
    print(f"    Log-safe : {safe_log_path(path)}")
    print(f"    Desc-safe: {safe_log_description('Esta es una descripción muy larga que no debería aparecer completa en los logs')}")

    print(f"\n{'─' * 50}\n")

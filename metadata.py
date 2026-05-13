"""
metadata.py — Integración con el Explorador de Windows

Hace que la descripción guardada en la DB aparezca en el Explorador
de Windows al pasar el cursor sobre el archivo o carpeta.

NO modifica los archivos originales. Usa dos mecanismos de Windows:

  1. Alternate Data Stream (ADS) — para archivos individuales
     Escribe la descripción en un stream oculto llamado :InfoFile
     adjunto al archivo. Invisible para el usuario, no cambia el
     contenido ni el tamaño visible del archivo.
     Ejemplo: C:\\Docs\\reporte.pdf:InfoFile

  2. desktop.ini — para carpetas
     Crea o actualiza desktop.ini en la carpeta con el campo
     InfoTip que Windows usa como tooltip en el Explorador.

  Ambos mecanismos funcionan solo en volúmenes NTFS (Windows).
  En OneDrive/SharePoint sincronizados localmente también funciona
  mientras el archivo esté disponible localmente.

Uso:
    from metadata import write_explorer_description, remove_explorer_description
    write_explorer_description("C:/Docs/reporte.pdf", "Descripción aquí")
    remove_explorer_description("C:/Docs/reporte.pdf")
"""

import os
import sys
import configparser
from pathlib import Path

from config import get_logger

logger = get_logger(__name__)

# Nombre del ADS y de la clave en desktop.ini
_STREAM_NAME  = "InfoFile"
_INI_SECTION  = ".ShellClassInfo"
_INI_KEY_TIP  = "InfoTip"
_INI_KEY_NAME = "LocalizedResourceName"
_DESKTOP_INI  = "desktop.ini"


# ──────────────────────────────────────────────
# Verificaciones de entorno
# ──────────────────────────────────────────────

def is_ntfs(path: str | Path) -> bool:
    """
    Retorna True si la ruta está en un volumen NTFS.
    ADS y desktop.ini solo funcionan en NTFS.
    FAT32/exFAT no soportan ADS.
    """
    if sys.platform != "win32":
        return False

    import ctypes
    root = Path(path).anchor   # e.g. "C:\\"
    buf  = ctypes.create_unicode_buffer(256)
    try:
        ctypes.windll.kernel32.GetVolumeInformationW(
            root, None, 0, None, None, None, buf, 256
        )
        return buf.value.upper() == "NTFS"
    except Exception:
        return False


# ──────────────────────────────────────────────
# ADS — Alternate Data Streams (archivos)
# ──────────────────────────────────────────────

def _ads_path(file_path: Path) -> str:
    """Retorna la ruta del ADS: C:\\archivo.pdf:InfoFile"""
    return f"{file_path}:{_STREAM_NAME}"


def _write_ads(file_path: Path, description: str) -> bool:
    """
    Escribe la descripción en el ADS :InfoFile del archivo.
    El ADS es invisible en el Explorador y no cambia el tamaño
    ni el contenido del archivo original.

    Limitación: ADS no se preserva al copiar a FAT32/exFAT/red SMB
    sin soporte NTFS. En OneDrive funciona si el archivo está
    disponible localmente.
    """
    ads = _ads_path(file_path)
    try:
        with open(ads, "w", encoding="utf-8") as f:
            f.write(description)
        logger.debug(f"ADS escrito: {ads}")
        return True
    except (OSError, PermissionError) as e:
        logger.warning(f"No se pudo escribir ADS en {file_path}: {e}")
        return False


def _read_ads(file_path: Path) -> str | None:
    """Lee la descripción desde el ADS :InfoFile del archivo."""
    ads = _ads_path(file_path)
    try:
        with open(ads, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except (OSError, PermissionError) as e:
        logger.warning(f"No se pudo leer ADS de {file_path}: {e}")
        return None


def _delete_ads(file_path: Path) -> bool:
    """Elimina el ADS :InfoFile del archivo."""
    ads = _ads_path(file_path)
    try:
        os.remove(ads)
        logger.debug(f"ADS eliminado: {ads}")
        return True
    except FileNotFoundError:
        return True   # ya no existía
    except (OSError, PermissionError) as e:
        logger.warning(f"No se pudo eliminar ADS de {file_path}: {e}")
        return False


# ──────────────────────────────────────────────
# desktop.ini — Tooltip de carpetas
# ──────────────────────────────────────────────

def _ini_path(folder: Path) -> Path:
    return folder / _DESKTOP_INI


def _write_desktop_ini(folder: Path, description: str) -> bool:
    """
    Crea o actualiza desktop.ini en la carpeta con el tooltip
    que Windows muestra al pasar el cursor sobre la carpeta.

    Formato que escribe:
        [.ShellClassInfo]
        InfoTip=Descripción aquí

    Pasos necesarios para que Windows lo reconozca:
      1. Crear/actualizar el archivo desktop.ini
      2. Marcar desktop.ini como System+Hidden (Windows lo ignora si no)
      3. Marcar la carpeta como ReadOnly (activa la lectura de desktop.ini)
    """
    ini_file = _ini_path(folder)

    try:
        config = configparser.ConfigParser()
        config.optionxform = str   # preservar mayúsculas en claves

        # Leer existente si ya hay uno
        if ini_file.exists():
            # Quitar atributos System+Hidden para poder leer/escribir
            _clear_ini_attrs(ini_file)
            config.read(ini_file, encoding="utf-8-sig")

        if _INI_SECTION not in config:
            config[_INI_SECTION] = {}

        config[_INI_SECTION][_INI_KEY_TIP] = description

        with open(ini_file, "w", encoding="utf-8-sig") as f:
            config.write(f)

        # Marcar como System+Hidden para que Windows lo procese
        _set_ini_attrs(ini_file)

        # Marcar la carpeta como ReadOnly para activar desktop.ini
        _set_folder_readonly(folder)

        logger.debug(f"desktop.ini actualizado: {ini_file}")
        return True

    except (OSError, PermissionError) as e:
        logger.warning(f"No se pudo escribir desktop.ini en {folder}: {e}")
        return False


def _remove_desktop_ini_tip(folder: Path) -> bool:
    """
    Elimina el campo InfoTip de desktop.ini.
    Si el archivo queda vacío o sin sección útil, lo elimina completo.
    """
    ini_file = _ini_path(folder)
    if not ini_file.exists():
        return True

    try:
        _clear_ini_attrs(ini_file)
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(ini_file, encoding="utf-8-sig")

        if _INI_SECTION in config:
            config[_INI_SECTION].pop(_INI_KEY_TIP, None)
            # Si la sección quedó vacía o solo tiene claves vacías, eliminar el archivo
            if not any(v for v in config[_INI_SECTION].values()):
                config.remove_section(_INI_SECTION)

        if not config.sections():
            ini_file.unlink(missing_ok=True)
            logger.debug(f"desktop.ini eliminado: {ini_file}")
        else:
            with open(ini_file, "w", encoding="utf-8-sig") as f:
                config.write(f)
            _set_ini_attrs(ini_file)

        return True

    except (OSError, PermissionError) as e:
        logger.warning(f"No se pudo actualizar desktop.ini en {folder}: {e}")
        return False


def _set_ini_attrs(ini_file: Path) -> None:
    """Marca desktop.ini como System + Hidden (requerido por Windows)."""
    if sys.platform == "win32":
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        FILE_ATTRIBUTE_SYSTEM = 0x04
        ctypes.windll.kernel32.SetFileAttributesW(
            str(ini_file),
            FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM,
        )


def _clear_ini_attrs(ini_file: Path) -> None:
    """Quita atributos especiales para poder editar el archivo."""
    if sys.platform == "win32":
        import ctypes
        FILE_ATTRIBUTE_NORMAL = 0x80
        ctypes.windll.kernel32.SetFileAttributesW(
            str(ini_file),
            FILE_ATTRIBUTE_NORMAL,
        )


def _set_folder_readonly(folder: Path) -> None:
    """
    Marca la carpeta como ReadOnly.
    En Windows esto activa la lectura de desktop.ini por el Explorador.
    No impide crear/editar archivos dentro — solo es una señal para el shell.
    """
    if sys.platform == "win32":
        import ctypes
        FILE_ATTRIBUTE_READONLY = 0x01
        current = ctypes.windll.kernel32.GetFileAttributesW(str(folder))
        if current != 0xFFFFFFFF:   # INVALID_FILE_ATTRIBUTES
            ctypes.windll.kernel32.SetFileAttributesW(
                str(folder),
                current | FILE_ATTRIBUTE_READONLY,
            )


# ──────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────

def write_explorer_description(path: str | Path, description: str) -> bool:
    """
    Escribe la descripción para que aparezca en el Explorador de Windows.

    Para archivos  → ADS (:InfoFile stream oculto adjunto al archivo)
    Para carpetas  → desktop.ini (campo InfoTip en la carpeta)

    Retorna True si tuvo éxito, False si hubo algún error.
    No lanza excepciones — los errores se loggean y retornan False.

    Nota: requiere NTFS. En FAT32 o exFAT retorna False sin intentarlo.
    """
    path = Path(path)

    if not is_ntfs(path):
        logger.warning(f"Volumen no NTFS — no se puede escribir metadata: {path}")
        return False

    if path.is_dir():
        return _write_desktop_ini(path, description)
    else:
        return _write_ads(path, description)


def read_explorer_description(path: str | Path) -> str | None:
    """
    Lee la descripción desde el ADS o desktop.ini.
    Retorna None si no existe descripción en el sistema de archivos.
    """
    path = Path(path)
    if path.is_dir():
        ini_file = _ini_path(path)
        if not ini_file.exists():
            return None
        try:
            _clear_ini_attrs(ini_file)
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(ini_file, encoding="utf-8-sig")
            result = config.get(_INI_SECTION, _INI_KEY_TIP, fallback=None)
            _set_ini_attrs(ini_file)
            return result
        except Exception:
            return None
    else:
        return _read_ads(path)


def remove_explorer_description(path: str | Path) -> bool:
    """
    Elimina la descripción del Explorador (ADS o desktop.ini).
    No toca la DB — eso lo maneja database.py.
    """
    path = Path(path)
    if path.is_dir():
        return _remove_desktop_ini_tip(path)
    else:
        return _delete_ads(path)


def sync_from_db(path: str | Path, description: str) -> bool:
    """
    Sincroniza la descripción de la DB hacia el Explorador.
    Llamar desde upsert_file() o al guardar en dialogs.py.

    Si la descripción está vacía, elimina la metadata del Explorador.
    """
    if description and description.strip():
        return write_explorer_description(path, description.strip())
    else:
        return remove_explorer_description(path)


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else __file__
    desc = sys.argv[2] if len(sys.argv) > 2 else "Descripción de prueba desde InfoFile"

    p = Path(path)
    print(f"\nArchivo  : {p}")
    print(f"Es NTFS  : {is_ntfs(p)}")
    print(f"Es dir   : {p.is_dir()}")

    print(f"\nEscribiendo: '{desc}'")
    ok = write_explorer_description(p, desc)
    print(f"Resultado  : {'OK' if ok else 'ERROR'}")

    print(f"\nLeyendo de vuelta:")
    result = read_explorer_description(p)
    print(f"  '{result}'")

    print(f"\nPasa el cursor sobre el archivo en el Explorador para ver el tooltip.")
    print(f"Luego corre:  py metadata.py \"{path}\" --remove  para limpiar.\n")

    if "--remove" in sys.argv:
        ok = remove_explorer_description(p)
        print(f"Eliminado: {'OK' if ok else 'ERROR'}")

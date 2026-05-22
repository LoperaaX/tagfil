"""
startup.py — Inicio automático de TagFil con Windows

Registra o elimina InfoFile en el registro de Windows para que
arranque automáticamente al iniciar sesión.

Usa HKEY_CURRENT_USER — no requiere permisos de administrador.

Clave del registro:
    HKCU\Software\Microsoft\Windows\CurrentVersion\Run
    InfoFile = "C:\...\py.exe" "C:\...\main.py"

Uso:
    from startup import enable, disable, is_enabled
    enable()    # registrar inicio automático
    disable()   # eliminar inicio automático
    is_enabled() # verificar si está activo
"""

import shutil
import sys
import winreg
from pathlib import Path

from config import APP_NAME, get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

_HIVE     = winreg.HKEY_CURRENT_USER
_RUN_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_KEY  = APP_NAME   # nombre de la entrada en el registro


def _get_command() -> str:
    """
    Construye el comando que Windows ejecuta al iniciar sesión.
    Usa py.exe (launcher) para evitar el stub de WindowsApps.
    """
    py = shutil.which("py") or sys.executable
    main = str(Path(__file__).parent / "main.py")
    return f'"{py}" "{main}"'


# ──────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────

def enable() -> bool:
    """
    Registra InfoFile para arrancar con Windows.
    Retorna True si tuvo éxito.
    """
    try:
        cmd = _get_command()
        with winreg.OpenKey(_HIVE, _RUN_KEY, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, _APP_KEY, 0, winreg.REG_SZ, cmd)
        logger.info(f"Inicio automático habilitado: {cmd}")
        return True
    except OSError as e:
        logger.exception(f"Error habilitando inicio automático: {e}")
        return False


def disable() -> bool:
    """
    Elimina InfoFile del inicio automático de Windows.
    Retorna True si tuvo éxito (o si ya no estaba registrado).
    """
    try:
        with winreg.OpenKey(_HIVE, _RUN_KEY, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, _APP_KEY)
        logger.info("Inicio automático deshabilitado")
        return True
    except FileNotFoundError:
        return True   # ya no estaba — está bien
    except OSError as e:
        logger.exception(f"Error deshabilitando inicio automático: {e}")
        return False


def is_enabled() -> bool:
    """Retorna True si InfoFile está registrado para arrancar con Windows."""
    try:
        with winreg.OpenKey(_HIVE, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _APP_KEY)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def get_registered_command() -> str | None:
    """Retorna el comando registrado actualmente, o None si no está registrado."""
    try:
        with winreg.OpenKey(_HIVE, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _APP_KEY)
            return value
    except (FileNotFoundError, OSError):
        return None


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=f"Inicio automático de {APP_NAME}")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable",  action="store_true", help="Habilitar inicio con Windows")
    group.add_argument("--disable", action="store_true", help="Deshabilitar inicio con Windows")
    group.add_argument("--status",  action="store_true", help="Ver estado actual")
    args = parser.parse_args()

    if args.enable:
        ok = enable()
        print("OK  Inicio automático habilitado" if ok else "ERR Error al habilitar")

    elif args.disable:
        ok = disable()
        print("OK  Inicio automático deshabilitado" if ok else "ERR Error al deshabilitar")

    elif args.status:
        active = is_enabled()
        cmd    = get_registered_command()
        print(f"  Estado  : {'Habilitado' if active else 'Deshabilitado'}")
        if cmd:
            print(f"  Comando : {cmd}")

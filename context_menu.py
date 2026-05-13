"""
context_menu.py — Integración con el menú contextual de Windows

Registra y elimina la entrada "Agregar / editar descripción" en el
menú contextual del Explorador de Windows para archivos Y carpetas.

Usa HKEY_CURRENT_USER — no requiere permisos de administrador.

Uso:
    from context_menu import install, uninstall, is_installed
"""

import shutil
import sys
import winreg
from pathlib import Path

from config import get_logger, APP_NAME, REGISTRY_LABEL

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Constantes de registro
# ──────────────────────────────────────────────

# Raíz: HKEY_CURRENT_USER — no necesita admin
_HIVE = winreg.HKEY_CURRENT_USER

# Claves para archivos (*) y carpetas (Directory)
_SHELL_KEYS = [
    r"Software\Classes\*\shell\InfoFile",           # cualquier archivo
    r"Software\Classes\Directory\shell\InfoFile",   # carpetas
]

# Encuentra py.exe o python.exe funcional — evita el stub de WindowsApps
# que no funciona cuando Windows llama al comando desde el Explorador.
def _find_py() -> str:
    # 1. py.exe (Python Launcher para Windows) — lo más confiable
    py = shutil.which("py")
    if py:
        return py
    # 2. python.exe real (descartando el stub de WindowsApps)
    for candidate in [sys.executable]:
        p = Path(candidate)
        if p.exists() and "WindowsApps" not in str(p):
            return str(p)
    # 3. Último recurso
    return sys.executable

_PYTHON  = _find_py()
_MAIN_PY = str(Path(__file__).parent / "main.py")
_COMMAND = f'"{_PYTHON}" "{_MAIN_PY}" --file "%1"'


# ──────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────

def _set_key(shell_key: str) -> None:
    """
    Crea o actualiza una entrada del menú contextual en el registro.

    Estructura que crea en el registro::

        HKCU\\Software\\Classes\\*\\shell\\InfoFile
            (Default)  = "Agregar / editar descripcion"
            Icon       = ruta\\al\\ejecutable
            \\command
                (Default) = "py.exe" "main.py" --file "%1"
    """
    # Clave principal — texto visible en el menú
    with winreg.CreateKeyEx(_HIVE, shell_key, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, "",     0, winreg.REG_SZ, REGISTRY_LABEL)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, _PYTHON)

    # Subclave command — qué ejecutar al hacer clic
    cmd_key = shell_key + r"\command"
    with winreg.CreateKeyEx(_HIVE, cmd_key, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _COMMAND)

    logger.debug(f"Clave registrada: HKCU\\{shell_key}")


def _delete_key_tree(shell_key: str) -> None:
    """
    Elimina la clave del menú contextual y su subclave command.
    Silencioso si la clave no existe.
    """
    # Primero la hija (command), luego la padre
    for subkey in [shell_key + r"\command", shell_key]:
        try:
            winreg.DeleteKey(_HIVE, subkey)
            logger.debug(f"Clave eliminada: HKCU\\{subkey}")
        except FileNotFoundError:
            pass   # ya no existía — está bien
        except OSError as e:
            logger.warning(f"No se pudo eliminar HKCU\\{subkey}: {e}")


def _key_exists(shell_key: str) -> bool:
    """Retorna True si la clave existe en el registro."""
    try:
        with winreg.OpenKey(_HIVE, shell_key):
            return True
    except FileNotFoundError:
        return False


# ──────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────

def install() -> bool:
    """
    Registra InfoFile en el menú contextual de Windows
    para archivos y carpetas.

    Retorna True si tuvo éxito, False si hubo algún error.
    No requiere permisos de administrador.
    """
    try:
        for key in _SHELL_KEYS:
            _set_key(key)
        logger.info("Menú contextual registrado correctamente")
        return True

    except OSError as e:
        logger.exception(f"Error registrando menú contextual: {e}")
        return False


def uninstall() -> bool:
    """
    Elimina InfoFile del menú contextual de Windows.

    Retorna True si tuvo éxito, False si hubo algún error.
    """
    try:
        for key in _SHELL_KEYS:
            _delete_key_tree(key)
        logger.info("Menú contextual eliminado correctamente")
        return True

    except OSError as e:
        logger.exception(f"Error eliminando menú contextual: {e}")
        return False


def is_installed() -> bool:
    """
    Retorna True si ambas entradas (archivos y carpetas)
    están presentes en el registro.
    """
    return all(_key_exists(k) for k in _SHELL_KEYS)


# ──────────────────────────────────────────────
# Debug / uso directo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=f"Menú contextual de {APP_NAME}")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install",   action="store_true", help="Registrar en el menú contextual")
    group.add_argument("--uninstall", action="store_true", help="Eliminar del menú contextual")
    group.add_argument("--status",    action="store_true", help="Verificar si está instalado")
    args = parser.parse_args()

    if args.install:
        ok = install()
        print("OK - Instalado correctamente" if ok else "ERROR - Falló la instalación")

    elif args.uninstall:
        ok = uninstall()
        print("OK - Desinstalado correctamente" if ok else "ERROR - Falló la desinstalación")

    elif args.status:
        installed = is_installed()
        print(f"Estado  : {'Instalado' if installed else 'No instalado'}")
        print(f"Ejecutor: {_PYTHON}")
        print(f"Comando : {_COMMAND}")

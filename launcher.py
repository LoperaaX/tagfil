"""
launcher.py — Cómo se vuelve a lanzar TagFil desde fuera (menú contextual, inicio con Windows).

Dos escenarios:
  • Empaquetado (PyInstaller): el propio ejecutable, sin main.py ni intérprete.
  • Desarrollo: el mismo intérprete que está corriendo ahora (respeta venv/uv),
    en su variante pythonw.exe para que no parpadee una ventana de consola.
"""
import sys
from pathlib import Path

from config import ICON_PATH

_MAIN_PY = Path(__file__).resolve().parent / "main.py"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def interpreter() -> str:
    """Ejecutable que se registra: el .exe empaquetado o el pythonw.exe del entorno actual."""
    exe = Path(sys.executable)
    if is_frozen():
        return str(exe)
    pyw = exe.with_name("pythonw.exe")
    return str(pyw if pyw.exists() else exe)


def command(extra_args: str = "") -> str:
    """Línea de comandos completa, lista para el registro de Windows."""
    parts = [f'"{interpreter()}"']
    if not is_frozen():
        parts.append(f'"{_MAIN_PY}"')
    if extra_args:
        parts.append(extra_args)
    return " ".join(parts)


def icon() -> str:
    """Ícono de TagFil si existe; si no, el del ejecutable."""
    return str(ICON_PATH) if Path(ICON_PATH).exists() else interpreter()

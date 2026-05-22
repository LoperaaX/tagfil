"""
shell_extension.py — Compila y registra la Shell Extension de InfoFile

Automatiza todo el proceso:
  1. Encuentra MSBuild en Visual Studio
  2. Compila TagFilOverlay.dll
  3. Crea el ícono overlay .ico
  4. Registra la DLL con regsvr32
  5. Registra la clave ShellIconOverlayIdentifiers

Requiere ejecutar como Administrador para el registro.

Uso:
  py shell_extension.py --build      # solo compilar
  py shell_extension.py --install    # compilar + registrar
  py shell_extension.py --uninstall  # desregistrar
  py shell_extension.py --status     # ver estado
"""

import ctypes
import os
import shutil
import struct
import subprocess
import sys
import winreg
from pathlib import Path

from config import APP_NAME, APP_DIR, get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

_CLSID         = "{A4E23B0E-9B4D-4E6C-A12F-7C6D8E9F0A1B}"
_OVERLAY_NAME  = f"  {APP_NAME}HasDescription"   # espacios = prioridad alta
_PROJECT_DIR   = Path(__file__).parent / "ShellExtension"
_CSPROJ        = _PROJECT_DIR / "TagFilOverlay.csproj"
_DLL_SRC       = _PROJECT_DIR / "bin" / "Release" / "TagFilOverlay.dll"
_DLL_DEST      = APP_DIR / "TagFilOverlay.dll"
_ICON_PATH     = APP_DIR / "overlay.ico"

# Claves de registro
_OVERLAY_KEY   = (
    rf"Software\Microsoft\Windows\CurrentVersion"
    rf"\Explorer\ShellIconOverlayIdentifiers\{_OVERLAY_NAME}"
)
_CLSID_KEY     = rf"CLSID\{_CLSID}"
_INPROC_KEY    = rf"CLSID\{_CLSID}\InprocServer32"


# ──────────────────────────────────────────────
# Verificar privilegios de administrador
# ──────────────────────────────────────────────

def _is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# ──────────────────────────────────────────────
# Encontrar MSBuild
# ──────────────────────────────────────────────

def _find_msbuild() -> str | None:
    """
    Busca MSBuild en las rutas típicas de Visual Studio.
    Soporta VS 2017, 2019, 2022.
    """
    candidates = [
        # Visual Studio 2022
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
        # Visual Studio 2019
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
        # Visual Studio 2017
        r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin\MSBuild.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\MSBuild.exe",
    ]

    for path in candidates:
        if Path(path).exists():
            logger.debug(f"MSBuild encontrado: {path}")
            return path

    # Fallback: buscar con vswhere
    vswhere = Path(
        r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    )
    if vswhere.exists():
        try:
            result = subprocess.run(
                [str(vswhere), "-latest", "-requires",
                 "Microsoft.Component.MSBuild",
                 "-find", r"MSBuild\**\Bin\MSBuild.exe"],
                capture_output=True, text=True
            )
            path = result.stdout.strip().splitlines()
            if path:
                return path[0]
        except Exception:
            pass

    # Último intento: PATH del sistema
    return shutil.which("msbuild")


# ──────────────────────────────────────────────
# Crear ícono overlay
# ──────────────────────────────────────────────

def _create_icon() -> bool:
    """
    Genera overlay.ico — círculo morado 16x16.
    Usa solo stdlib, sin PIL.
    """
    try:
        W, H   = 16, 16
        # Color morado de InfoFile en BGRA
        FG = (237, 58, 114, 255)   # #7C3AED → BGRA = (237, 58, 124, 255)
        BG = (0, 0, 0, 0)

        pixels = []
        cx, cy, r = W // 2, H // 2, 6
        for y in range(H):
            for x in range(W):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                pixels.append(FG if d2 <= r * r else BG)

        # BMP DIB header
        bmp_header = struct.pack(
            "<IiiHHIIiiII",
            40, W, H * 2, 1, 32, 0, 0, 0, 0, 0, 0
        )

        # Pixel data (bottom-up, BGRA)
        pixel_data = b""
        for row in reversed(range(H)):
            for col in range(W):
                b, g, rv, a = pixels[row * W + col]
                pixel_data += struct.pack("BBBB", b, g, rv, a)

        # Máscara AND
        mask_row = ((W + 31) // 32) * 4
        and_mask = b"\x00" * (mask_row * H)

        image_data = bmp_header + pixel_data + and_mask

        # ICO header + directory
        ico_header = struct.pack("<HHH", 0, 1, 1)
        ico_dir    = struct.pack(
            "<BBBBHHIi",
            W, H, 0, 0, 1, 32,
            len(image_data), 6 + 16
        )

        _ICON_PATH.write_bytes(ico_header + ico_dir + image_data)
        logger.info(f"Ícono overlay creado: {_ICON_PATH}")
        return True

    except Exception as e:
        logger.exception(f"Error creando ícono: {e}")
        return False


# ──────────────────────────────────────────────
# Compilar DLL
# ──────────────────────────────────────────────

def build() -> bool:
    """Compila TagFilOverlay.dll con MSBuild."""
    msbuild = _find_msbuild()
    if not msbuild:
        print("ERR  MSBuild no encontrado. Asegúrate de tener Visual Studio instalado.")
        return False

    if not _CSPROJ.exists():
        print(f"ERR  Proyecto no encontrado: {_CSPROJ}")
        print(f"     Asegúrate de que ShellExtension/ esté en {Path(__file__).parent}")
        return False

    print(f"  Compilando con: {msbuild}")
    try:
        result = subprocess.run(
            [msbuild, str(_CSPROJ),
             "/p:Configuration=Release",
             "/p:Platform=x64",
             "/v:minimal",
             "/nologo"],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"ERR  Compilación falló:\n{result.stdout}\n{result.stderr}")
            logger.error(f"MSBuild falló: {result.stderr}")
            return False

        if not _DLL_SRC.exists():
            print(f"ERR  DLL no generada en: {_DLL_SRC}")
            return False

        # Copiar DLL a APP_DIR
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_DLL_SRC, _DLL_DEST)
        print(f"  OK  DLL compilada: {_DLL_DEST}")
        logger.info(f"DLL compilada y copiada: {_DLL_DEST}")
        return True

    except Exception as e:
        logger.exception(f"Error compilando: {e}")
        return False


# ──────────────────────────────────────────────
# Registrar DLL
# ──────────────────────────────────────────────

def _register_dll() -> bool:
    """
    Registra la DLL manualmente en el registro (equivalente a regsvr32).
    regsvr32 no funciona bien con .NET — hay que registrar las claves
    COM directamente.
    """
    try:
        dll_path = str(_DLL_DEST)

        # CLSID principal
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE, _CLSID_KEY, 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"{APP_NAME} Overlay Icon")

        # InprocServer32 — apunta a mscoree.dll (runtime .NET)
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE, _INPROC_KEY, 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, "",              0, winreg.REG_SZ, "mscoree.dll")
            winreg.SetValueEx(key, "Class",         0, winreg.REG_SZ, "TagFilOverlay.TagFilOverlayHandler")
            winreg.SetValueEx(key, "Assembly",      0, winreg.REG_SZ, "TagFilOverlay, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null")
            winreg.SetValueEx(key, "RuntimeVersion",0, winreg.REG_SZ, "v4.0.30319")
            winreg.SetValueEx(key, "ThreadingModel",0, winreg.REG_SZ, "Both")
            winreg.SetValueEx(key, "CodeBase",      0, winreg.REG_SZ, _DLL_DEST.as_uri())

        logger.info(f"DLL registrada en HKLM: {_CLSID_KEY}")
        return True

    except OSError as e:
        logger.exception(f"Error registrando DLL: {e}")
        return False


def _register_overlay_key() -> bool:
    """Registra la clave ShellIconOverlayIdentifiers."""
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE, _OVERLAY_KEY, 0, winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _CLSID)
        logger.info(f"Overlay key registrada")
        return True
    except OSError as e:
        logger.exception(f"Error registrando overlay key: {e}")
        return False


def _unregister_all() -> bool:
    """Elimina todas las claves del registro."""
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, _INPROC_KEY),
        (winreg.HKEY_LOCAL_MACHINE, _CLSID_KEY),
        (winreg.HKEY_LOCAL_MACHINE, _OVERLAY_KEY),
    ]
    for hive, key in keys:
        try:
            winreg.DeleteKey(hive, key)
            logger.debug(f"Clave eliminada: {key}")
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning(f"No se pudo eliminar {key}: {e}")
    return True


def _restart_explorer() -> None:
    """Reinicia el Explorador para aplicar el overlay."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"],
                      capture_output=True)
        import time; time.sleep(1)
        subprocess.Popen(["explorer.exe"])
        logger.info("Explorador reiniciado")
    except Exception as e:
        logger.warning(f"No se pudo reiniciar el Explorador: {e}")


# ──────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────

def install() -> bool:
    """
    Compila la DLL, crea el ícono y registra todo.
    Requiere Administrador.
    """
    if not _is_admin():
        print("ERR  Se requieren permisos de Administrador.")
        print("     Abre PowerShell como Administrador y vuelve a correr.")
        return False

    steps = [
        ("Compilando DLL",              build),
        ("Creando ícono overlay",        _create_icon),
        ("Registrando DLL en Windows",   _register_dll),
        ("Registrando overlay icon",     _register_overlay_key),
    ]

    for desc, fn in steps:
        print(f"  {desc}...")
        if not fn():
            print(f"ERR  Falló: {desc}")
            return False
        print(f"  OK")

    _restart_explorer()
    print("\nOverlay icon instalado correctamente.")
    print("Los archivos con descripción mostrarán un punto morado en el Explorador.")
    return True


def uninstall() -> bool:
    """Desregistra el overlay y reinicia el Explorador."""
    if not _is_admin():
        print("ERR  Se requieren permisos de Administrador.")
        return False
    _unregister_all()
    _restart_explorer()
    print("Overlay icon desinstalado.")
    return True


def is_installed() -> bool:
    """Retorna True si el overlay está registrado."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _OVERLAY_KEY):
            return True
    except FileNotFoundError:
        return False


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=f"Shell Extension overlay icon para {APP_NAME}"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build",     action="store_true", help="Solo compilar la DLL")
    group.add_argument("--install",   action="store_true", help="Compilar + registrar (admin)")
    group.add_argument("--uninstall", action="store_true", help="Desregistrar (admin)")
    group.add_argument("--status",    action="store_true", help="Ver estado")
    args = parser.parse_args()

    if args.build:
        ok = build()
        print("OK  DLL compilada" if ok else "ERR  Compilación falló")

    elif args.install:
        ok = install()
        sys.exit(0 if ok else 1)

    elif args.uninstall:
        ok = uninstall()
        sys.exit(0 if ok else 1)

    elif args.status:
        msbuild   = _find_msbuild()
        installed = is_installed()
        dll_ok    = _DLL_DEST.exists()
        icon_ok   = _ICON_PATH.exists()
        print(f"  Estado overlay : {'Instalado' if installed else 'No instalado'}")
        print(f"  DLL            : {'OK' if dll_ok else 'No compilada'} ({_DLL_DEST})")
        print(f"  Ícono          : {'OK' if icon_ok else 'No existe'} ({_ICON_PATH})")
        dotnet = shutil.which('dotnet')
        print(f"  dotnet         : {dotnet or 'NO ENCONTRADO'}")
        print(f"  Admin          : {'Sí' if _is_admin() else 'No'}")

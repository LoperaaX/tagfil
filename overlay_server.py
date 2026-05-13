"""
overlay_server.py — COM Server Python para overlay icon de InfoFile

Implementa IShellIconOverlayIdentifier usando pywin32.
Más compatible con Windows 10/11 que la DLL C#.

Instalación (como Administrador):
    py overlay_server.py --install
    py overlay_server.py --uninstall
    py overlay_server.py --status
"""

import sys
import os
import winreg
from pathlib import Path

from config import APP_NAME, APP_DIR, get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

CLSID         = "{A4E23B0E-9B4D-4E6C-A12F-7C6D8E9F0A1B}"
OVERLAY_NAME  = f"  {APP_NAME}HasDescription"
ICON_PATH     = str(APP_DIR / "overlay.ico")
DB_PATH       = str(APP_DIR / "infofile.db")
_PROJECT_DIR  = str(Path(__file__).parent)

# Claves de registro
_CLSID_KEY    = rf"CLSID\{CLSID}"
_INPROC_KEY   = rf"CLSID\{CLSID}\InprocServer32"
_OVERLAY_KEY  = (
    rf"Software\Microsoft\Windows\CurrentVersion"
    rf"\Explorer\ShellIconOverlayIdentifiers\{OVERLAY_NAME}"
)


# ──────────────────────────────────────────────
# Crear ícono overlay
# ──────────────────────────────────────────────

def _create_icon() -> bool:
    """Genera overlay.ico — círculo morado 16x16."""
    import struct, math
    try:
        W, H = 16, 16
        FG = (237, 58, 124, 255)   # morado BGRA
        BG = (0, 0, 0, 0)
        pixels = []
        cx, cy, r = W//2, H//2, 6
        for y in range(H):
            for x in range(W):
                d = math.sqrt((x-cx)**2+(y-cy)**2)
                if d <= r:
                    pixels.append(FG)
                else:
                    pixels.append(BG)

        bmp_hdr = struct.pack("<IiiHHIIiiII", 40, W, H*2, 1, 32, 0, 0, 0, 0, 0, 0)
        px_data = b""
        for row in reversed(range(H)):
            for col in range(W):
                b,g,rv,a = pixels[row*W+col]
                px_data += struct.pack("BBBB", b, g, rv, a)
        mask = b"\x00"*(((W+31)//32)*4*H)
        img  = bmp_hdr + px_data + mask

        ico_hdr = struct.pack("<HHH", 0, 1, 1)
        ico_dir = struct.pack("<BBBBHHIi", W, H, 0, 0, 1, 32, len(img), 6+16)

        Path(ICON_PATH).write_bytes(ico_hdr + ico_dir + img)
        logger.info(f"Ícono overlay creado: {ICON_PATH}")
        return True
    except Exception as e:
        logger.exception(f"Error creando ícono: {e}")
        return False


# ──────────────────────────────────────────────
# COM Server class
# ──────────────────────────────────────────────

def _get_server_class():
    """Retorna la clase COM server. Solo importa pywin32 cuando se necesita."""
    import pythoncom
    import win32com.server.register

    class InfoFileOverlay:
        """
        IShellIconOverlayIdentifier — Windows llama estos métodos
        por cada archivo visible en el Explorador.
        """
        _reg_clsid_       = CLSID
        _reg_progid_      = f"{APP_NAME}.OverlayIcon"
        _reg_desc_        = f"{APP_NAME} Overlay Icon"
        _public_methods_  = ["GetOverlayInfo", "GetPriority", "IsMemberOf"]
        _com_interfaces_  = [pythoncom.IID_IUnknown]

        def GetOverlayInfo(self):
            """Retorna ruta del ícono, índice y flags."""
            return (ICON_PATH, 0, 1)   # path, index, ISIOI_ICONFILE

        def GetPriority(self):
            """Prioridad 0-100. Menor = más alta."""
            return 50

        def IsMemberOf(self, path, attrib):
            """
            Retorna S_OK (0) si el archivo tiene descripción.
            Retorna S_FALSE (1) si no.
            """
            try:
                import sqlite3
                if not Path(DB_PATH).exists():
                    return 1

                # Normalizar ruta
                path = str(Path(path).resolve(strict=False))

                conn = sqlite3.connect(DB_PATH, timeout=2)
                conn.row_factory = sqlite3.Row
                try:
                    row = conn.execute(
                        "SELECT 1 FROM files WHERE path=? "
                        "AND description IS NOT NULL "
                        "AND TRIM(description)!='' LIMIT 1",
                        (path,)
                    ).fetchone()
                    return 0 if row else 1
                finally:
                    conn.close()
            except Exception:
                return 1

    return InfoFileOverlay


# ──────────────────────────────────────────────
# Registro manual (más confiable que UseCommandLine)
# ──────────────────────────────────────────────

def _register_com(py_exe: str, script_path: str) -> bool:
    """
    Registra el COM server manualmente en el registro.
    Usa LocalServer32 en lugar de InprocServer32 — más compatible
    con Windows 10/11 que no permite InprocServer32 de Python en
    el proceso del Explorador por seguridad.
    """
    try:
        # HKCR\CLSID\{...}
        with winreg.CreateKeyEx(
            winreg.HKEY_CLASSES_ROOT, _CLSID_KEY, 0, winreg.KEY_WRITE
        ) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"{APP_NAME} Overlay Icon")

        # LocalServer32 — Windows lanza el proceso en lugar de cargarlo en-proceso
        local_key = rf"CLSID\{CLSID}\LocalServer32"
        cmd = f'"{py_exe}" "{script_path}" --com-server'
        with winreg.CreateKeyEx(
            winreg.HKEY_CLASSES_ROOT, local_key, 0, winreg.KEY_WRITE
        ) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)

        # ProgID
        progid_key = rf"CLSID\{CLSID}\ProgID"
        with winreg.CreateKeyEx(
            winreg.HKEY_CLASSES_ROOT, progid_key, 0, winreg.KEY_WRITE
        ) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"{APP_NAME}.OverlayIcon")

        logger.info("COM server registrado en HKCR")
        return True

    except OSError as e:
        logger.exception(f"Error registrando COM: {e}")
        return False


def _register_overlay_key() -> bool:
    """Registra la clave ShellIconOverlayIdentifiers en HKLM."""
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE, _OVERLAY_KEY, 0, winreg.KEY_WRITE
        ) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, CLSID)
        logger.info("Overlay key registrada en HKLM")
        return True
    except OSError as e:
        logger.exception(f"Error registrando overlay key: {e}")
        return False


def _unregister_all() -> None:
    """Elimina todas las claves del registro."""
    keys_hkcr = [
        rf"CLSID\{CLSID}\LocalServer32",
        rf"CLSID\{CLSID}\ProgID",
        _CLSID_KEY,
    ]
    keys_hklm = [_OVERLAY_KEY]

    for key in keys_hkcr:
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key)
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning(f"No se pudo eliminar {key}: {e}")

    for key in keys_hklm:
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key)
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning(f"No se pudo eliminar {key}: {e}")


def _restart_explorer() -> None:
    import subprocess, time
    try:
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True)
        time.sleep(1)
        subprocess.Popen(["explorer.exe"])
        logger.info("Explorador reiniciado")
    except Exception as e:
        logger.warning(f"No se pudo reiniciar el Explorador: {e}")


def _find_py() -> str:
    import shutil
    return shutil.which("py") or sys.executable


def _is_admin() -> bool:
    import ctypes
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# ──────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────

def install() -> bool:
    """Instala el overlay icon. Requiere Administrador."""
    if not _is_admin():
        print("ERR  Se requieren permisos de Administrador.")
        return False

    try:
        import pythoncom
        import win32com
    except ImportError:
        print("ERR  pywin32 no instalado. Corre: py -m pip install pywin32")
        return False

    py_exe     = _find_py()
    script     = str(Path(__file__).resolve())

    steps = [
        ("Creando ícono overlay",        _create_icon),
        ("Registrando COM server",        lambda: _register_com(py_exe, script)),
        ("Registrando overlay key",       _register_overlay_key),
    ]

    for desc, fn in steps:
        print(f"  {desc}...")
        if not fn():
            print(f"ERR  Falló: {desc}")
            return False
        print(f"  OK")

    _restart_explorer()
    print("\nOverlay icon instalado. Los archivos con descripción mostrarán un punto morado.")
    return True


def uninstall() -> bool:
    """Desinstala el overlay icon."""
    if not _is_admin():
        print("ERR  Se requieren permisos de Administrador.")
        return False
    _unregister_all()
    _restart_explorer()
    print("Overlay icon desinstalado.")
    return True


def is_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _OVERLAY_KEY):
            return True
    except FileNotFoundError:
        return False


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=f"Overlay icon para {APP_NAME}")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install",    action="store_true")
    group.add_argument("--uninstall",  action="store_true")
    group.add_argument("--status",     action="store_true")
    group.add_argument("--com-server", action="store_true",
                       help="Modo servidor COM (llamado por Windows)")
    args = parser.parse_args()

    if args.install:
        sys.exit(0 if install() else 1)

    elif args.uninstall:
        sys.exit(0 if uninstall() else 1)

    elif args.status:
        try:
            import pythoncom
            has_pywin32 = True
        except ImportError:
            has_pywin32 = False
        print(f"  Estado   : {'Instalado' if is_installed() else 'No instalado'}")
        print(f"  pywin32  : {'OK' if has_pywin32 else 'NO instalado'}")
        print(f"  Ícono    : {'OK' if Path(ICON_PATH).exists() else 'No existe'}")
        print(f"  Admin    : {'Sí' if _is_admin() else 'No'}")

    elif args.com_server:
        # Windows lanza este proceso como servidor COM
        import pythoncom
        import win32com.server.register

        OverlayClass = _get_server_class()
        pythoncom.CoInitialize()
        try:
            factory = pythoncom.MakeRegisteredComponentFactory(OverlayClass._reg_clsid_)
            pythoncom.EnableSocketLog()
            pythoncom.PumpMessages()
        except Exception as e:
            logger.exception(f"Error en COM server: {e}")
        finally:
            pythoncom.CoUninitialize()

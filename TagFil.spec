# InfoFile.spec
# Archivo de configuración de PyInstaller para InfoFile
#
# Uso:
#   pyinstaller InfoFile.spec
#
# El .exe queda en: dist\InfoFile\InfoFile.exe

import sys
from pathlib import Path

# ──────────────────────────────────────────────
# Análisis de dependencias
# ──────────────────────────────────────────────

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Incluir la carpeta assets con el ícono
        ('assets', 'assets'),
        # Incluir la carpeta ShellExtension con la DLL compilada
        ('ShellExtension/bin/Release/net48/InfoFileOverlay.dll', 'ShellExtension'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # Módulos propios de InfoFile
        'config',
        'database',
        'context_menu',
        'dialogs',
        'main_window',
        'tray',
        'metadata',
        'startup',
        'security',
        'shell_extension',
        # stdlib que PyInstaller a veces no detecta
        'sqlite3',
        'winreg',
        'ctypes',
        'configparser',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir lo que no necesitamos para reducir tamaño
        'tkinter',
        'unittest',
        'email',
        'html',
        'http',
        'urllib',
        'xml',
        'pydoc',
        'doctest',
        'difflib',
        # 'pickle',  # necesario para logging.handlers
        'multiprocessing',
    ],
    noarchive=False,
    optimize=1,
)

# ──────────────────────────────────────────────
# Empaquetado
# ──────────────────────────────────────────────

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TagFil',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # comprimir con UPX si está disponible
    console=False,      # sin ventana de consola (app gráfica)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',   # ícono del .exe
    version='version_info.txt',  # metadata de versión
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TagFil',
)

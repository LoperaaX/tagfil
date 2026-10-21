# TagFil.spec
# Configuración de PyInstaller para TagFil
#
# Uso (desde la raíz del repo, con el entorno de desarrollo activo):
#   pyinstaller TagFil.spec --noconfirm
#
# El .exe queda en: dist\TagFil\TagFil.exe
#
# El overlay de Explorador (ShellExtension/) es experimental y NO se empaqueta
# en el 0.2: su DLL no está firmada y no se registra por sí sola.

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Carpeta assets con el ícono y recursos visuales
        ('assets', 'assets'),
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # Módulos propios de TagFil
        'config',
        'database',
        'context_menu',
        'dialogs',
        'launcher',
        'core',
        'core.naming',
        'tagfil',
        'tagfil.main_window',
        'tagfil.settings',
        'tagfil.sidebar',
        'tagfil.theme',
        'tagfil.pages.resumen',
        'tagfil.pages.archivos',
        'tagfil.pages.etiquetas',
        'tagfil.pages.buscar',
        'tagfil.pages.configuracion',
        'tagfil.pages.papelera',
        'tagfil.widgets.import_worker',
        'tagfil.widgets.search_worker',
        'tagfil.widgets.starfield',
        'tagfil.widgets.ui_helpers',
        'tagfil.widgets.toggle_switch',
        'tagfil.widgets.theme_selector',
        'tagfil.widgets.neon_icon',
        'tray',
        'metadata',
        'startup',
        'security',
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
        # Solo se excluye lo que seguro no se usa. xml, email, http, urllib,
        # html y multiprocessing se quitaron de esta lista: pywin32 y logging
        # los importan de forma indirecta y romperían el .exe en tiempo de ejecución.
        'tkinter',
    ],
    noarchive=False,
    optimize=1,
)

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
    upx=False,          # UPX sobre Qt provoca falsos positivos de antivirus y cuelgues
    console=False,      # sin ventana de consola (app gráfica)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TagFil',
)

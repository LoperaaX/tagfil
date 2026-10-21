# TagFil

Aplicación de escritorio para Windows que permite describir y etiquetar archivos, buscarlos al instante y ver esa información en el Explorador de Windows (tooltip). Hecha con Python y PyQt6; los datos viven en SQLite con búsqueda de texto completo (FTS5).

> Estado: **0.2.0-dev** — en desarrollo activo. Las auditorías técnicas y sus correcciones están en [`docs/`](docs/) y en el [CHANGELOG](CHANGELOG.md).

## Funciones

- Descripción, etiquetas y nombre corto estructurado por archivo.
- Búsqueda por nombre, descripción y etiquetas (coincidencia por prefijo, sin importar acentos ni mayúsculas).
- Importación de carpetas completas, con cancelación.
- Papelera con restauración.
- Menú contextual del Explorador («Agregar / editar descripción») e inicio con Windows.
- Descripción visible en el Explorador (flujo alterno NTFS / `desktop.ini` en carpetas).
- Copias de seguridad automáticas con rotación, verificación de integridad y recuperación.

## Requisitos

- Windows 10/11
- Python 3.12 o superior

## Instalación (desarrollo)

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py main.py
```

## Tests

```powershell
py -m unittest discover -s tests -v
```

Los tests aíslan sus datos con la variable de entorno `TAGFIL_HOME`, así que no tocan tu base de datos real. Esa misma variable sirve para ejecutar la app con otra carpeta de datos.

## Empaquetado

```powershell
py -m pip install pyinstaller
pyinstaller TagFil.spec --noconfirm
```

El ejecutable queda en `dist\TagFil\TagFil.exe`. El overlay del Explorador (`ShellExtension/`) es experimental y no se incluye en el empaquetado.

## Datos y privacidad

Todo se guarda localmente en `%APPDATA%\TagFil` (o en `TAGFIL_HOME` si está definida): base de datos, copias de seguridad, `settings.json` y registros. La auditoría interna no guarda rutas completas ni descripciones, solo hashes y conteos.

## Estructura

Ver [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) y [`docs/NAMING.md`](docs/NAMING.md).

# Estructura actual de TagFil

Revisada el 2026-10-21 tras integrar las mejoras.

- `assets/`: icono y recursos de la aplicación.
- `core/`: generación de nombres estructurados (`naming.py`).
- `tagfil/`: ventana, navegación, estilos y preferencias.
- `tagfil/pages/`: las seis páginas de la interfaz.
- `tagfil/widgets/`: componentes e hilos de búsqueda e importación.
- `tests/`: pruebas con datos temporales mediante `TAGFIL_HOME`.
- `docs/`: documentación y auditorías.
- `.github/workflows/`: pruebas automáticas de GitHub Actions.
- `ShellExtension/`: código fuente del overlay experimental .NET.

La entrada sigue siendo `main.py`. Los módulos de datos, seguridad e integración
con Windows permanecen en la raíz: `config.py`, `database.py`, `security.py`,
`metadata.py`, `context_menu.py`, `startup.py`, `launcher.py`, `dialogs.py` y
`tray.py`. `TagFil.spec` y `version_info.txt` configuran el empaquetado.
`demodata.py` conserva la utilidad opcional de datos de demostración.

## Carpetas necesarias

`.git/` conserva el historial y `.venv/` contiene Python y las dependencias
instaladas. No son residuos; ambas se conservaron, igual que el código, las
pruebas, los recursos y la documentación.

## Limpieza

Se retiraron `build/`, `dist/`, `bin/`, `obj/`, los `__pycache__/` del código,
`ShellExtension/bin/`, `ShellExtension/obj/`, el archivo `.lscache`, los dos PDF
de prueba vacíos y el `desktop.ini` de la raíz. Se guardaron fuera del proyecto
y están incluidos en el respaldo ZIP anterior a la integración.

Python y los compiladores pueden recrear estas carpetas. `.gitignore` evita
versionarlas; no impide que se creen al ejecutar o compilar.

## Datos

Los datos reales viven en `%APPDATA%\TagFil`, o en `TAGFIL_HOME` si se define.
No se modificaron durante la limpieza ni las verificaciones de esta integración.

## Overlay experimental

Se conservan `ShellExtension/`, `shell_extension.py` y `overlay_server.py` porque
son código fuente, aunque no se incluyen en el ejecutable principal. Las
herramientas mantienen referencias heredadas `InfoFileOverlay`/`TagFilOverlay`
que requieren una revisión específica antes de compilar y registrar COM.
No se compiló ni registró el overlay durante esta integración.

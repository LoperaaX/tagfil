# Auditoria de TagFil

Fecha: 2026-10-06  
Proyecto auditado: `C:\VS CODE\TagFil`  
Nota: en esta sesion no estaba montado el disco `D:`; se audito la copia disponible en `C:\VS CODE\TagFil`, que conserva la estructura y cambios recientes de TagFil.

## Resumen ejecutivo

TagFil ya tiene una base mucho mas solida que al inicio: hay separacion por paginas, base SQLite con migraciones, FTS5, papelera, auditoria de eventos, pruebas unitarias, validacion de rutas, backup con hash y un flujo inicial de importacion de carpetas. El proyecto ya no esta en fase de experimento: esta entrando en fase de estabilizacion.

El principal riesgo ahora no es una falla puntual, sino la dispersion: hay mezcla de nombres `InfoFile`/`TagFil`, funciones reales junto con controles aun ficticios, textos de demostracion en UI, empaquetado todavia desactualizado y algunas decisiones de seguridad/backup que necesitan cerrarse antes de confiar en la app como herramienta diaria.

Recomendacion central: enfocar el siguiente ciclo en un milestone `0.2 estable`, no en seguir agregando features. Ese milestone deberia cerrar marca, flujos principales, instalacion, importacion, backup y configuracion real.

## Verificaciones ejecutadas

Comandos ejecutados:

```powershell
uv run python -m unittest discover -s tests -v
uv run python -m compileall database.py security.py main.py tagfil tests
uv run python main.py security-check
git status --short
```

Resultado:

- Pruebas unitarias: OK, 7 pruebas pasan.
- Compilacion Python: OK.
- Auditoria CLI: OK en DB, hash de backup y carpeta de app.
- Estados informativos: backup cifrado desactivado, menu contextual no instalado.
- Git: cambios locales en `.gitignore` y `requirements.txt`; `desktop.ini` aparece sin versionar.

## Estado del producto

### Fortalezas

- La app ya tiene un flujo de escritorio reconocible: tray, ventana principal, paginas, dialogo contextual y busqueda.
- La base de datos soporta archivos, tags, papelera, FTS5, metadata estructurada y auditoria.
- La seguridad mejoro: validacion de rutas, bloqueo de ADS manual, bloqueo de rutas de dispositivo, hash de backup y auditoria visible.
- La importacion de carpetas es un salto importante de valor: TagFil puede organizar volumen, no solo archivos individuales.
- Ya hay pruebas unitarias para DB y seguridad.

### Debilidades

- Marca inconsistente: muchos archivos y comentarios aun dicen `InfoFile`.
- Configuracion mezcla controles reales con controles visuales que no persisten.
- Empaquetado PyInstaller esta desactualizado y no incluye los modulos nuevos.
- El backup cifrado existe como mecanismo, pero solo se activa por variable de entorno y no tiene restauracion UI/CLI.
- La importacion masiva todavia no tiene pruebas unitarias ni cancelacion visible desde UI.
- La salida CLI muestra mojibake en consola Windows cuando no esta en UTF-8.

## Hallazgos principales

### P1 - Empaquetado desactualizado

`TagFil.spec` todavia esta comentado como `InfoFile`, referencia `InfoFileOverlay.dll` y no lista modulos nuevos como `tagfil.widgets.import_worker` ni `tagfil.widgets.starfield`.

Impacto:

- El ejecutable puede compilar incompleto o fallar al usar importacion de carpetas.
- La distribucion puede salir con nombres viejos o artefactos faltantes.

Archivos relacionados:

- `TagFil.spec`
- `tagfil/widgets/import_worker.py`
- `tagfil/widgets/starfield.py`

Recomendacion:

- Actualizar `TagFil.spec` a marca TagFil.
- Incluir todos los modulos nuevos.
- Validar build con `pyinstaller TagFil.spec`.
- Crear una prueba manual de smoke: abrir app, importar carpeta, buscar, backup, cerrar desde tray.

### P1 - Configuracion muestra estados no reales

La tarjeta de copia de seguridad muestra una fecha fija: `Sab 28/03/2026, 13:32:00`. Las integraciones OneDrive/Google Drive/SharePoint tienen toggles y boton guardar, pero el estado no persiste y solo hace `print`.

Impacto:

- Puede dar falsa confianza al usuario.
- El usuario puede creer que backup automatico o integraciones estan funcionando cuando no lo estan.

Archivos relacionados:

- `tagfil/pages/configuracion.py`

Recomendacion:

- Reemplazar fecha fija por lectura real de `last_backup.txt`.
- Guardar preferencias en un archivo `settings.json` o tabla `settings`.
- Marcar integraciones como "Proximamente" o esconderlas hasta implementarlas.

### P1 - Mezcla InfoFile / TagFil

Hay referencias a `InfoFile` en docstrings, spec, shell extension, overlay, comentarios, requirements y algunos nombres de backup.

Impacto:

- Confusion para mantenimiento.
- Riesgo de instalar claves de registro o overlays con nombre viejo.
- Dificulta empaquetar y documentar.

Archivos relacionados:

- `main.py`
- `database.py`
- `tray.py`
- `context_menu.py`
- `shell_extension.py`
- `overlay_server.py`
- `TagFil.spec`
- `requirements.txt`

Recomendacion:

- Decidir si el producto se llama TagFil definitivamente.
- Hacer una migracion de nombres controlada.
- Mantener compatibilidad solo donde sea necesario: `LEGACY_DB_PATH = infofile.db`.

### P2 - Backup cifrado sin flujo completo de restauracion

El backup cifrado con DPAPI puede crearse cuando `TAGFIL_ENCRYPT_BACKUP=1`, pero no hay UI/CLI para restaurarlo ni para explicar sus limitaciones.

Impacto:

- Buena defensa incompleta.
- El usuario puede activar backup cifrado sin saber que depende del mismo usuario Windows.

Archivos relacionados:

- `security.py`
- `database.py`
- `tagfil/pages/configuracion.py`

Recomendacion:

- Agregar `backup --create`, `backup --verify`, `backup --restore`.
- Mostrar en UI si el backup cifrado existe y cuando fue creado.
- Documentar que DPAPI depende del usuario y equipo Windows.

### P2 - Importacion de carpetas sin cobertura de pruebas

`FolderScanWorker` e `FolderImportWorker` compilan y el diseño es razonable, pero no tienen pruebas.

Impacto:

- Riesgo de regresiones en una de las features mas importantes.
- Casos como carpetas con permisos raros, duplicados, extensiones, limite de 5000 y tags sugeridos pueden romperse sin aviso.

Archivos relacionados:

- `tagfil/widgets/import_worker.py`

Recomendacion:

- Extraer funciones puras testeables: `scan_folder(...)`, `suggest_tags(...)`.
- Probar: duplicados, extensiones no soportadas, limites, tags por carpeta/nombre, archivo grande.
- Mantener el QThread como envoltorio de UI.

### P2 - Auditoria de eventos guarda datos utiles, pero aun no es una bitacora completa

La tabla `audit_events` evita rutas completas y descripciones, lo cual es positivo. Sin embargo, la app todavia no tiene politica de retencion ni exportacion.

Impacto:

- En uso prolongado, la tabla puede crecer sin control.
- Falta forma de analizar eventos o limpiar historial.

Archivos relacionados:

- `database.py`
- `tagfil/pages/configuracion.py`

Recomendacion:

- Agregar retencion configurable: ultimos 1000/5000 eventos.
- Agregar accion `audit.clear`.
- Agregar exportacion CSV sin rutas completas.

### P2 - Salida CLI con mojibake en PowerShell

`security-check` funciona, pero en esta consola se vio `TagFil � Auditor�a`. Esto no rompe la logica, pero da mala impresion.

Impacto:

- Mala experiencia de consola en Windows con codepage no UTF-8.
- Puede afectar mensajes con tildes o simbolos.

Archivos relacionados:

- `main.py`
- `config.py`

Recomendacion:

- Usar salida ASCII para comandos CLI criticos o configurar `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` cuando sea posible.
- Evitar separadores Unicode en CLI.

### P2 - Dependencia de metadata ADS puede ser sensible

TagFil escribe metadata en ADS `:InfoFile` para archivos NTFS. Es util, pero puede sorprender al usuario porque modifica metadata invisible del archivo.

Impacto:

- Posible friccion con antivirus, sincronizadores o herramientas corporativas.
- Algunos usuarios pueden no querer ADS.

Archivos relacionados:

- `metadata.py`
- `database.py`
- `security.py`

Recomendacion:

- Crear setting real: "Sincronizar metadata con Explorador".
- Permitir modo "solo DB".
- Documentar el uso de ADS y desktop.ini.

### P3 - `.gitignore` no ignora `desktop.ini`

Git muestra `desktop.ini` como untracked. `.gitignore` ignora `Thumbs.db` y `.DS_Store`, pero no `desktop.ini`.

Impacto:

- Ruido de repositorio.
- Riesgo de commitear archivos de sistema.

Recomendacion:

- Agregar `desktop.ini` a `.gitignore`.

### P3 - Version y autor no estan listos

`APP_VERSION` sigue en `0.1.0` y `APP_AUTHOR` dice `"Tu nombre"`.

Impacto:

- No esta listo para release.

Recomendacion:

- Cambiar a `0.2.0-dev` mientras se estabiliza.
- Actualizar autor.

## Evaluacion por areas

### Arquitectura

Estado: aceptable, pero creciendo.

`database.py` ya supera un tamano donde conviene separarlo. Por ahora funciona, pero mezcla: schema, migraciones, backup, auditoria, CRUD, busqueda, papelera, tags y utilidades.

Recomendacion futura:

- `database/connection.py`
- `database/schema.py`
- `database/files.py`
- `database/tags.py`
- `database/trash.py`
- `database/audit.py`
- `database/search.py`

No lo haria inmediatamente si el objetivo es estabilizar; lo haria despues de release 0.2.

### Seguridad

Estado: mejor que la media para una app local temprana.

Bien:

- Validacion de rutas.
- Bloqueo de ADS manual.
- Bloqueo de rutas de dispositivo.
- Hash de backup.
- Backup DPAPI opcional.
- Auditoria sin rutas completas.

Falta:

- Restauracion segura.
- Preferencia persistente para backup cifrado.
- UI para activar/desactivar sincronizacion ADS.
- Politica de retencion de auditoria.

### UX/UI

Estado: atractiva, pero con controles que prometen mas de lo que hacen.

Bien:

- Paginas separadas.
- Estilo visual consistente.
- Seguridad y actividad ya visibles.
- Importacion integrada en Archivos.

Falta:

- Estados vacios mas guiados.
- Primer uso / onboarding.
- Mensajes de error mas concretos en importacion.
- Indicador de progreso real con cancelacion.
- Evitar textos ficticios en Configuracion.

### Datos y busqueda

Estado: bueno.

Bien:

- SQLite + WAL.
- FTS5 con fallback LIKE.
- Tags normalizadas.
- Papelera.
- Auditoria.

Riesgo:

- FTS usa triggers y sincronizacion manual. Esto funciona, pero requiere pruebas de consistencia.
- Importacion masiva llama `upsert_file` archivo por archivo, con sync de metadata Explorer por cada uno. Puede ser lento para miles de archivos.

Recomendacion:

- Agregar modo `bulk=True` o `sync_metadata=False` para importacion masiva.

### Testing

Estado: base inicial buena, cobertura insuficiente.

Actual:

- 7 pruebas.
- Cubren DB basica y seguridad.

Falta:

- Import worker.
- Naming.
- Migraciones desde schemas antiguos.
- Search/FTS.
- Papelera.
- Backup restore.
- CLI.

Meta razonable para 0.2:

- 20-30 pruebas unitarias enfocadas en DB, seguridad, importacion y naming.

### Packaging / release

Estado: no listo.

Bloqueadores:

- Spec desactualizado.
- Marca vieja en comentarios y rutas.
- Dependencias y pywin32 necesitan estrategia clara.
- No hay checklist de smoke test.
- Menu contextual no instalado en auditoria.

Recomendacion:

- Crear `RELEASE_CHECKLIST.md`.
- Actualizar `TagFil.spec`.
- Probar build en entorno limpio.

## Roadmap recomendado

### Milestone 0.2 estable

Objetivo: TagFil usable de punta a punta en tu equipo.

Checklist:

- Unificar marca TagFil.
- Arreglar Configuracion para mostrar solo estados reales.
- Persistir settings basicos.
- Actualizar PyInstaller spec.
- Agregar pruebas de importacion.
- Agregar comandos backup.
- Smoke test manual completo.

### Milestone 0.3 productividad

Objetivo: hacer que organizar carpetas sea rapido.

Features:

- Importacion con progreso visual y cancelar.
- Previsualizacion con lista de archivos antes de importar.
- Reglas de tags personalizadas.
- Deteccion de duplicados por hash/tamano.
- Filtros avanzados de fecha/tags.

### Milestone 0.4 distribucion

Objetivo: instalar y usar como app normal.

Features:

- Instalador.
- Acceso directo.
- Menu contextual robusto.
- Overlay opcional.
- Autoarranque configurable.

## Acciones recomendadas inmediatas

1. Agregar `desktop.ini` a `.gitignore`.
2. Cambiar `APP_AUTHOR`.
3. Actualizar textos `InfoFile` -> `TagFil` donde no sea compatibilidad.
4. Quitar fecha fija de backup en Configuracion.
5. Ocultar o persistir toggles de integraciones.
6. Agregar pruebas para `import_worker.py`.
7. Actualizar `TagFil.spec`.
8. Crear `RELEASE_CHECKLIST.md`.

## Decision sugerida

No agregaria mas funciones nuevas esta semana. El mejor siguiente paso es cerrar deuda de producto:

- limpiar marca,
- hacer Configuracion honesta,
- probar importacion,
- preparar empaquetado.

Eso te saca del estancamiento porque convierte TagFil en algo que puedes usar, probar y enseñar sin explicar "esto todavia es demo".


# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar] — 0.2.0-dev

Correcciones de la auditoría técnica 01 (2026-10-19).

Integración local del 2026-10-21: limpieza de compilaciones, cachés y PDF de
prueba; estructura documentada y corrección adicional de la rotación diaria
para conservar generaciones incluso con respaldos frecuentes.

### Corregido
- **Búsqueda / base de datos (crítico):** el índice FTS5 era una tabla con *content table* y una columna `tags` inexistente, escrita a la vez por triggers y por código. Provocaba `database disk image is malformed` al eliminar permanentemente archivos, dejaba tags borrados todavía «encontrables» y no se podía reconstruir. Ahora es una tabla standalone mantenida por una única función (`_reindex_file`). Migración automática v4 → v5 con copia previa de la base de datos.
- Guardar un archivo solo con descripción o etiquetas (CLI, modo terminal) ya no borra el nombre corto, tipo, entidad, fecha, consecutivo ni calificador. Los campos omitidos se conservan; pasar `None` o `''` los vacía explícitamente.
- Volver a registrar un archivo que está en la papelera lo restaura (antes quedaba invisible pero contado como importado).
- Importar una carpeta ya no borra descripciones existentes del Explorador: las adopta. Tampoco escribe al disco archivo por archivo.
- Menú contextual e inicio con Windows funcionan en el `.exe` empaquetado, usan `pythonw` en desarrollo (sin ventana de consola) y el intérprete del entorno actual; ícono propio de TagFil.
- Etiquetas con espacios («Cuenta de cobro») ya no se fusionan («cuentadecobro»): se convierten en `cuenta-de-cobro`.
- Las descripciones ya no pierden texto con «<» y «>» («Valor < 100 y > 50»); solo se eliminan etiquetas HTML reales.
- `validate_path` ya no rechaza nombres con «..» legítimos (`informe..final.pdf`); solo `..` como componente de ruta.
- Tooltip de carpetas con «%» ya no falla; se quitan saltos de línea y se libera el atributo de solo lectura al quitar el tip.
- La instancia única es por sesión (`Local\`) y solo enfoca una ventana Qt con el título exacto de la app.
- Búsqueda: el hilo de la UI ya no se bloquea mientras se escribe; el límite de resultados se aplica en SQL y solo se consulta el disco de lo que se muestra. Los errores de búsqueda se muestran.
- Cerrar la app durante una importación detiene los hilos de forma ordenada; la importación puede cancelarse desde su botón.
- `settings.json`: lectura tolerante a archivos dañados, escritura atómica y sin pisar cambios de otro proceso.
- Respaldos: una DB dañada ya no sobrescribe el último backup bueno; se conservan hasta 3 generaciones diarias; la recuperación elige la generación sana más reciente y descarta los `-wal`/`-shm` del archivo dañado.
- Retención de auditoría (`audit_retention`) ahora se aplica al iniciar.
- Escritura atómica del backup cifrado; código de error real en DPAPI.

- **Pestaña «Todos los archivos»:** el botón «Importar carpeta» ya no tapa a la búsqueda (la cabecera pasa a dos filas y la búsqueda se ensancha según el espacio), la lupa se ve sin recuadro y el chip «Todos» (y los de cada tipo) ya no se corta.
- Los botones del tema (p. ej. «Importar carpeta» y «Más usados») recuperan su fondo en todas las páginas: dos reglas `background: transparent` sin selector en `main_window.py` se heredaban a todos los hijos y lo anulaban.

### Añadido
- **Página de etiquetas:** integración del rediseño con tarjetas y cuadrícula
  adaptables, métricas actualizadas sin reconstruir widgets, botón «Nueva etiqueta»,
  búsqueda con foco y orden segmentado. Prueba de integración con datos aislados
  para creación, búsqueda, orden, cobertura, ranking y tamaños de ventana.
- `launcher.py` (comando de relanzamiento para el registro de Windows).
- `check_fts_integrity()`, `rebuild_search_index()`, `prune_audit_events()`.
- Soporte de `TAGFIL_HOME` para aislar los datos (tests, instalaciones portables).
- Suite de regresiones (`tests/test_regressions.py`), base de tests aislados (`tests/_base.py`) y CI en GitHub Actions (Windows y Linux).
- README y este CHANGELOG.

### Cambiado
- `TagFil.spec`: sin DLL del overlay, sin exclusiones agresivas de la stdlib, sin UPX, con los módulos nuevos; `version_info.txt` en 0.2.0.
- `requirements.txt`: `pywin32` solo en Windows; `PyQt6` con límite superior.
- `.gitignore`: las reglas finales tenían sangría y no se aplicaban; se dejan de versionar PDFs de prueba y `.lscache`.
- Test de backup cifrado actualizado a `settings.json`.

"""
demo_data.py — Datos de prueba para TagFil.
 
Uso:
    cd D:\\VS CODE\\TagFil
    py demo_data.py            # insertar datos de prueba
    py demo_data.py --limpiar  # borrar todos los datos de prueba
    py demo_data.py --reset    # limpiar + reinsertar
 
Los archivos no necesitan existir en disco — TagFil los registra igual.
"""
 
import sys
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
 
# ── Path para encontrar config.py y database.py desde la raíz ─────────
sys.path.insert(0, str(Path(__file__).parent))
 
import database as db
 
 
# ══════════════════════════════════════════════════════════════════════
# DATOS FALSOS
# ══════════════════════════════════════════════════════════════════════
 
# (path_falso, descripción, [etiquetas], días_atrás)
ARCHIVOS_DEMO = [
    # ── Trabajo / Finanzas ────────────────────────────────────────────
    (r"C:\Users\Demo\Documents\Trabajo\Reporte_Q1_2026.pdf",
     "Reporte trimestral de ventas Q1 2026. Incluye comparativa con Q4 2025 y proyecciones.",
     ["trabajo", "finanzas", "reportes", "2026"], 2),
 
    (r"C:\Users\Demo\Documents\Trabajo\Propuesta_ClienteX.docx",
     "Propuesta comercial para Cliente X. Servicios de consultoría y desarrollo.",
     ["trabajo", "clientes", "propuestas"], 5),
 
    (r"C:\Users\Demo\Documents\Trabajo\Presupuesto_2026.xlsx",
     "Presupuesto anual 2026. Desglose por departamentos y proyectos.",
     ["trabajo", "finanzas", "presupuesto", "2026"], 1),
 
    (r"C:\Users\Demo\Documents\Trabajo\Contrato_Proveedor_ABC.pdf",
     "Contrato de servicios con Proveedor ABC. Válido hasta diciembre 2026.",
     ["trabajo", "legal", "contratos", "proveedores"], 10),
 
    (r"C:\Users\Demo\Documents\Trabajo\Presentacion_Directivos.pptx",
     "Presentación para la junta directiva. Resultados Q1 y estrategia Q2.",
     ["trabajo", "presentaciones", "directivos"], 3),
 
    (r"C:\Users\Demo\Documents\Trabajo\Factura_001_2026.pdf",
     "Factura #001 emitida a Cliente X por servicios de enero 2026.",
     ["trabajo", "finanzas", "facturas"], 15),
 
    (r"C:\Users\Demo\Documents\Trabajo\Acta_Reunion_Marzo.docx",
     "Acta de reunión del 15 de marzo. Acuerdos y compromisos del equipo.",
     ["trabajo", "reuniones", "actas"], 7),
 
    (r"C:\Users\Demo\Documents\Trabajo\Plan_Marketing_Q2.xlsx",
     "Plan de marketing para Q2 2026. Canales digitales, presupuesto y KPIs.",
     ["trabajo", "marketing", "planificacion"], 4),
 
    # ── Personal / Documentos ─────────────────────────────────────────
    (r"C:\Users\Demo\Documents\Personal\Cedula_Ciudadania.pdf",
     "Copia digital de cédula de ciudadanía. Escaneada en alta resolución.",
     ["personal", "documentos", "identidad"], 90),
 
    (r"C:\Users\Demo\Documents\Personal\Pasaporte_2024.pdf",
     "Pasaporte vigente hasta 2030. Incluye páginas de visas.",
     ["personal", "documentos", "viajes", "identidad"], 120),
 
    (r"C:\Users\Demo\Documents\Personal\CV_Luis_2026.docx",
     "Currículum vitae actualizado. Versión en español para Colombia.",
     ["personal", "trabajo", "cv"], 30),
 
    (r"C:\Users\Demo\Documents\Personal\Seguro_Medico_2026.pdf",
     "Póliza de seguro médico. Compañía: Sura. Vigencia enero-diciembre 2026.",
     ["personal", "seguros", "salud"], 45),
 
    (r"C:\Users\Demo\Documents\Personal\Declaracion_Renta_2025.pdf",
     "Declaración de renta año gravable 2025. Radicada en febrero 2026.",
     ["personal", "finanzas", "impuestos", "legal"], 60),
 
    # ── Desarrollo / Código ───────────────────────────────────────────
    (r"C:\Users\Demo\Projects\TagFil\main_window.py",
     "Ventana principal de TagFil. Contiene MainWindow, Sidebar y páginas.",
     ["dev", "python", "tagfil", "pyqt6"], 0),
 
    (r"C:\Users\Demo\Projects\TagFil\database.py",
     "Capa de datos de TagFil. SQLite con FTS5 para búsqueda full-text.",
     ["dev", "python", "tagfil", "sqlite"], 1),
 
    (r"C:\Users\Demo\Projects\API_REST\app.py",
     "API REST con FastAPI. Endpoints para gestión de usuarios y productos.",
     ["dev", "python", "fastapi", "backend"], 8),
 
    (r"C:\Users\Demo\Projects\Web\index.html",
     "Landing page del proyecto. HTML5 + TailwindCSS. Responsive.",
     ["dev", "web", "html", "frontend"], 12),
 
    (r"C:\Users\Demo\Projects\Scripts\backup_automatico.py",
     "Script de backup automático. Comprime y sube a S3 cada noche.",
     ["dev", "python", "scripts", "backup"], 20),
 
    # ── Imágenes / Diseño ─────────────────────────────────────────────
    (r"C:\Users\Demo\Pictures\Logo_TagFil_v3.png",
     "Logo final de TagFil versión 3. Fondo transparente, 1024x1024px.",
     ["diseño", "logos", "tagfil"], 14),
 
    (r"C:\Users\Demo\Pictures\Captura_UI_Resumen.png",
     "Screenshot de la página Resumen. Para documentación y README.",
     ["diseño", "capturas", "tagfil"], 2),
 
    (r"C:\Users\Demo\Pictures\Banner_LinkedIn.jpg",
     "Banner para perfil de LinkedIn. Dimensiones 1584x396px.",
     ["diseño", "redes-sociales", "personal"], 25),
 
    # ── Multimedia ────────────────────────────────────────────────────
    (r"C:\Users\Demo\Videos\Tutorial_TagFil_v1.mp4",
     "Tutorial de uso de TagFil. Duración 8 minutos. Grabado con OBS.",
     ["videos", "tutoriales", "tagfil"], 6),
 
    (r"C:\Users\Demo\Music\Playlist_Trabajo.mp3",
     "Playlist de concentración para trabajo profundo. Lo-fi hip hop mix.",
     ["musica", "personal"], 50),
 
    # ── Archivos comprimidos ──────────────────────────────────────────
    (r"C:\Users\Demo\Downloads\Proyecto_Entregable_Final.zip",
     "Entregable final del proyecto. Código fuente + documentación + assets.",
     ["trabajo", "proyectos", "entregables"], 9),
 
    (r"C:\Users\Demo\Downloads\Backup_Configuraciones.rar",
     "Backup de configuraciones del sistema. VS Code, terminal, Git.",
     ["dev", "backup", "configuraciones"], 35),
 
    # ── Texto plano ───────────────────────────────────────────────────
    (r"C:\Users\Demo\Documents\Notas\Ideas_App_Mobile.txt",
     "Lista de ideas para la versión mobile de TagFil. Features y prioridades.",
     ["personal", "ideas", "tagfil", "mobile"], 11),
 
    (r"C:\Users\Demo\Documents\Notas\Pendientes_Semana.txt",
     "Lista de tareas pendientes para esta semana. Actualizar cada lunes.",
     ["personal", "productividad", "tareas"], 1),
]
 
 
# ══════════════════════════════════════════════════════════════════════
# DATOS PARA LA PAPELERA
# (path, descripción, [etiquetas], días_creado_atrás, días_eliminado_atrás)
# ══════════════════════════════════════════════════════════════════════
 
ARCHIVOS_PAPELERA = [
    (r"C:\Users\Demo\Documents\Trabajo\Borrador_Informe_Viejo.docx",
     "Borrador descartado del informe anual. Reemplazado por la versión final.",
     ["trabajo", "borradores"], 45, 3),
 
    (r"C:\Users\Demo\Documents\Personal\Foto_Perfil_Antigua.png",
     "Foto de perfil anterior. Ya no está en uso, subida la nueva versión.",
     ["personal", "imágenes"], 90, 5),
 
    (r"C:\Users\Demo\Projects\TagFil\main_window_v1_backup.py",
     "Versión antigua de la ventana principal antes del rediseño de UI.",
     ["dev", "python", "tagfil", "backup"], 60, 2),
 
    (r"C:\Users\Demo\Downloads\Instalador_VLC_viejo.exe",
     "Instalador de VLC versión 3.0.18. Ya actualizado a versión 3.0.21.",
     ["descargas", "software"], 30, 7),
 
    (r"C:\Users\Demo\Documents\Trabajo\Contrato_Vencido_2024.pdf",
     "Contrato de proveedor vencido en diciembre 2024. Ya no vigente.",
     ["trabajo", "legal", "contratos"], 120, 10),
 
    (r"C:\Users\Demo\Documents\Notas\Notas_Reunion_Cancelada.txt",
     "Notas de reunión que fue cancelada el 12 de febrero. Sin valor actual.",
     ["trabajo", "reuniones"], 15, 1),
 
    (r"C:\Users\Demo\Pictures\Capturas_Prueba_UI.zip",
     "Capturas de pantalla de pruebas de interfaz de versiones obsoletas.",
     ["diseño", "capturas", "tagfil"], 20, 4),
 
    (r"C:\Users\Demo\Documents\Personal\Recibo_Servicio_Cancelado.pdf",
     "Recibo de pago de suscripción cancelada en enero 2026.",
     ["personal", "finanzas", "recibos"], 75, 8),
 
    (r"C:\Users\Demo\Projects\Scripts\test_debug_temporal.py",
     "Script temporal para depurar el bug #47. Bug ya resuelto y cerrado.",
     ["dev", "python", "scripts"], 10, 1),
 
    (r"C:\Users\Demo\Documents\Trabajo\Presentacion_Draft_v2.pptx",
     "Segunda versión del borrador. Descartada tras cambio de enfoque estratégico.",
     ["trabajo", "presentaciones", "borradores"], 25, 6),
]
 
 
# ══════════════════════════════════════════════════════════════════════
# FUNCIONES
# ══════════════════════════════════════════════════════════════════════
 
def _utc_ago(days: int) -> str:
    """Timestamp UTC de hace N días."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
 
 
def _insertar_archivo(conn, path, descripcion, etiquetas, ts_created, deleted_at=None):
    """Helper: inserta un archivo con etiquetas y FTS. Retorna (file_id, 'ok'|'skip'|'error')."""
    nombre = Path(path).name
    existe = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
    if existe:
        return None, "skip"
    try:
        row = conn.execute(
            """
            INSERT INTO files (path, name, description, created_at, updated_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (path, nombre, descripcion, ts_created, ts_created, deleted_at),
        ).fetchone()
        file_id = row["id"]
 
        if etiquetas:
            conn.executemany("INSERT OR IGNORE INTO tags(name) VALUES (?)", [(t,) for t in etiquetas])
            placeholders = ",".join("?" * len(etiquetas))
            tag_rows = conn.execute(
                f"SELECT id, name FROM tags WHERE name IN ({placeholders})", etiquetas
            ).fetchall()
            tag_map = {r["name"]: r["id"] for r in tag_rows}
            conn.executemany(
                "INSERT OR IGNORE INTO file_tags(file_id, tag_id) VALUES (?, ?)",
                [(file_id, tag_map[t]) for t in etiquetas if t in tag_map],
            )
 
        conn.execute(
            "INSERT INTO files_fts(files_fts, rowid, name, description, tags) VALUES ('delete', ?, ?, ?, '')",
            (file_id, nombre, descripcion),
        )
        conn.execute(
            "INSERT INTO files_fts(rowid, name, description, tags) VALUES (?, ?, ?, ?)",
            (file_id, nombre, descripcion, " ".join(etiquetas)),
        )
        conn.commit()
        return file_id, "ok"
    except sqlite3.Error as e:
        return None, f"error:{e}"
 
 
def insertar_datos():
    """Inserta todos los archivos de demo (activos + papelera) en la base de datos."""
    print("\n🚀 Insertando datos de prueba en TagFil...\n")
    db.init_db()
    conn = db.get_connection()
 
    # ── Archivos activos ──────────────────────────────────────────────
    print("  📁 Archivos activos:")
    ins_ok = ins_skip = 0
    for path, descripcion, etiquetas, dias in ARCHIVOS_DEMO:
        nombre = Path(path).name
        ts = _utc_ago(dias)
        _, status = _insertar_archivo(conn, path, descripcion, etiquetas, ts, deleted_at=None)
        if status == "ok":
            ins_ok += 1
            tags_str = ", ".join(etiquetas[:3]) + (f" +{len(etiquetas)-3}" if len(etiquetas) > 3 else "")
            print(f"    ✅ {nombre:<45} [{tags_str}]")
        elif status == "skip":
            ins_skip += 1
            print(f"    ⏭  Ya existe: {nombre}")
        else:
            print(f"    ❌ {nombre}: {status}")
 
    # ── Archivos en papelera ──────────────────────────────────────────
    print("\n  🗑  Papelera:")
    pap_ok = pap_skip = 0
    for path, descripcion, etiquetas, dias_creado, dias_eliminado in ARCHIVOS_PAPELERA:
        nombre = Path(path).name
        ts_created = _utc_ago(dias_creado)
        ts_deleted = _utc_ago(dias_eliminado)
        _, status = _insertar_archivo(conn, path, descripcion, etiquetas, ts_created, deleted_at=ts_deleted)
        if status == "ok":
            pap_ok += 1
            tags_str = ", ".join(etiquetas[:3]) + (f" +{len(etiquetas)-3}" if len(etiquetas) > 3 else "")
            print(f"    🗑  {nombre:<45} [{tags_str}] (eliminado hace {dias_eliminado}d)")
        elif status == "skip":
            pap_skip += 1
            print(f"    ⏭  Ya existe: {nombre}")
        else:
            print(f"    ❌ {nombre}: {status}")
 
    conn.close()
    print(f"\n{chr(9472)*60}")
    print(f"  Activos insertados   : {ins_ok}  (omitidos: {ins_skip})")
    print(f"  Papelera insertados  : {pap_ok}  (omitidos: {pap_skip})")
    print(f"{chr(9472)*60}")
    print("\n✨ Listo. Abre TagFil y verás los datos en todas las páginas.\n")
 
 
def limpiar_datos():
    """Elimina (permanentemente) todos los archivos de demo de la base de datos."""
    print("\n🧹 Limpiando datos de prueba...\n")
 
    db.init_db()
    conn = db.get_connection()
    eliminados = 0
 
    todas_rutas = (
        [p for p, *_ in ARCHIVOS_DEMO] +
        [p for p, *_ in ARCHIVOS_PAPELERA]
    )
 
    for path in todas_rutas:
        nombre = Path(path).name
        row = conn.execute(
            "SELECT id, name, description FROM files WHERE path = ?", (path,)
        ).fetchone()
 
        if not row:
            continue
 
        file_id = row["id"]
        conn.execute(
            "INSERT INTO files_fts(files_fts, rowid, name, description, tags) "
            "VALUES ('delete', ?, ?, ?, '')",
            (file_id, row["name"], row["description"]),
        )
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        eliminados += 1
        print(f"  🗑  {nombre}")
 
    cursor = conn.execute(
        "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM file_tags)"
    )
    conn.commit()
    orphans = cursor.rowcount
    conn.close()
 
    print(f"\n{chr(9472)*60}")
    print(f"  Archivos eliminados  : {eliminados}")
    print(f"  Tags huérfanas       : {orphans}")
    print(f"{chr(9472)*60}\n")
 
 
def mostrar_stats():
    """Muestra estadísticas actuales de la base de datos."""
    db.init_db()
    stats = db.get_stats()
    tags  = db.get_all_tags()
 
    print(f"\n{'─'*60}")
    print(f"  📊 Estado actual de la base de datos")
    print(f"{'─'*60}")
    print(f"  Archivos totales  : {stats['total_files']}")
    print(f"  Etiquetas únicas  : {stats['total_tags']}")
    print(f"  Con descripción   : {stats['files_with_desc']}")
    print(f"  Sin descripción   : {stats['files_without_desc']}")
    if tags:
        print(f"\n  Etiquetas: {', '.join(tags[:15])}", end="")
        if len(tags) > 15:
            print(f" ... +{len(tags)-15} más")
        else:
            print()
    print(f"{'─'*60}\n")
 
 
# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════
 
if __name__ == "__main__":
    args = sys.argv[1:]
 
    if "--limpiar" in args:
        limpiar_datos()
        mostrar_stats()
 
    elif "--reset" in args:
        limpiar_datos()
        insertar_datos()
        mostrar_stats()
 
    elif "--stats" in args:
        mostrar_stats()
 
    else:
        insertar_datos()
        mostrar_stats()

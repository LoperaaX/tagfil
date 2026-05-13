"""
database.py — Capa de datos de InfoFile

Todas las rutas y el logger vienen de config.py.
No hardcodees rutas aquí.
"""

import sqlite3
import shutil
from datetime import datetime, timezone
from pathlib import Path

from config import APP_DIR, DB_PATH, get_logger


# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────

DB_BACKUP    = APP_DIR / "infofile_backup.db"
LAST_BACKUP  = APP_DIR / "last_backup.txt"   # control de frecuencia de backup (#2)
BACKUP_EVERY = 3600                           # segundos mínimos entre backups (1 hora)

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _utc_now() -> str:
    """Retorna timestamp UTC consistente para SQLite. (#1)"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ──────────────────────────────────────────────
# Backup
# ──────────────────────────────────────────────

def backup_db(force: bool = False) -> bool:
    """
    Backup consistente usando SQLite backup API.
    Seguro con WAL mode — snapshot atómico.

    Solo ejecuta el backup si pasó más de BACKUP_EVERY segundos
    desde el último backup, a menos que force=True. (#2)
    """
    if not DB_PATH.exists():
        return False

    # Control de frecuencia (#2)
    if not force:
        if LAST_BACKUP.exists():
            try:
                last = float(LAST_BACKUP.read_text().strip())
                elapsed = datetime.now(timezone.utc).timestamp() - last
                if elapsed < BACKUP_EVERY:
                    logger.debug(f"Backup omitido — faltan {int(BACKUP_EVERY - elapsed)}s")
                    return True
            except (ValueError, OSError):
                pass   # si el archivo está corrupto, hacemos backup igual

    src  = None
    dest = None

    try:
        src  = sqlite3.connect(DB_PATH)

        # WAL checkpoint antes del backup — garantiza que todos los datos
        # del archivo .db-wal estén en el archivo principal antes de copiar (#1)
        src.execute("PRAGMA wal_checkpoint(FULL)")

        dest = sqlite3.connect(DB_BACKUP)
        src.backup(dest)

        # Registrar timestamp del backup exitoso (#2)
        LAST_BACKUP.write_text(str(datetime.now(timezone.utc).timestamp()))

        logger.info(f"Backup creado: {DB_BACKUP}")
        return True

    except (sqlite3.Error, OSError) as e:   # específico en lugar de Exception (#3)
        logger.exception(f"Error creando backup: {e}")
        return False

    finally:
        if src:  src.close()
        if dest: dest.close()


# ──────────────────────────────────────────────
# Integridad
# ──────────────────────────────────────────────

def check_integrity() -> bool:
    """Ejecuta integrity_check sobre la DB."""
    if not DB_PATH.exists():
        return True

    conn = None
    try:
        conn   = sqlite3.connect(DB_PATH)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        ok     = result == "ok"
        if ok:
            logger.debug("integrity_check: ok")
        else:
            logger.error(f"integrity_check falló: {result}")
        return ok

    except sqlite3.Error as e:   # específico (#3)
        logger.exception(f"Error verificando integridad: {e}")
        return False

    finally:
        if conn: conn.close()


def _attempt_recovery() -> bool:
    """Recupera la DB desde backup."""
    if not DB_BACKUP.exists():
        logger.error("No existe backup para recuperación")
        return False

    try:
        corrupted = APP_DIR / "infofile_corrupted.db"
        if DB_PATH.exists():
            shutil.move(str(DB_PATH), str(corrupted))
        shutil.copy2(DB_BACKUP, DB_PATH)
        logger.warning(f"DB recuperada desde backup. Corrupto guardado en: {corrupted}")
        return True

    except (OSError, shutil.Error) as e:   # específico (#3)
        logger.exception(f"Error recuperando DB: {e}")
        return False


# ──────────────────────────────────────────────
# Conexión
# ──────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Retorna conexión SQLite configurada."""
    APP_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES,
        timeout=10,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    # NOTA: en SQLite, cache_size negativo = kilobytes (no páginas)
    # -10000 = ~10 MB de caché en RAM. Positivo = número de páginas. (#4)
    conn.execute("PRAGMA cache_size=-10000")
    return conn


# ──────────────────────────────────────────────
# Inicialización
# ──────────────────────────────────────────────

def init_db() -> None:
    """
    Inicializa tablas, índices y tabla FTS5 con content table.
    Verifica integridad y crea backup automático.
    """
    APP_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists() and not check_integrity():
        logger.warning("DB corrupta detectada")
        if _attempt_recovery():
            logger.info("Recovery exitoso")
        else:
            logger.error("Recovery fallido")

    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                path        TEXT    NOT NULL UNIQUE,
                name        TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT    NOT NULL UNIQUE COLLATE NOCASE
            );

            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                tag_id  INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
                PRIMARY KEY (file_id, tag_id)
            );

            CREATE INDEX IF NOT EXISTS idx_files_path      ON files(path);
            CREATE INDEX IF NOT EXISTS idx_tags_name       ON tags(name);

            -- Índices en file_tags — aceleran JOINs, búsquedas por tag y limpiezas (#5)
            CREATE INDEX IF NOT EXISTS idx_file_tags_file_id ON file_tags(file_id);
            CREATE INDEX IF NOT EXISTS idx_file_tags_tag_id  ON file_tags(tag_id);

            -- FTS5 con content table — no duplica datos en disco (#2)
            -- Lee name/description desde la tabla files directamente
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                name,
                description,
                tags,
                content=files,
                content_rowid=id,
                tokenize='unicode61 remove_diacritics 2'
            );

            -- Triggers para mantener FTS5 sincronizado (#2)
            CREATE TRIGGER IF NOT EXISTS files_fts_insert
            AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, name, description, tags)
                VALUES (new.id, new.name, new.description, '');
            END;

            CREATE TRIGGER IF NOT EXISTS files_fts_delete
            AFTER DELETE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, name, description, tags)
                VALUES ('delete', old.id, old.name, old.description, '');
            END;

            CREATE TRIGGER IF NOT EXISTS files_fts_update
            AFTER UPDATE ON files BEGIN
                INSERT INTO files_fts(files_fts, rowid, name, description, tags)
                VALUES ('delete', old.id, old.name, old.description, '');
                INSERT INTO files_fts(rowid, name, description, tags)
                VALUES (new.id, new.name, new.description, '');
            END;
        """)

    backup_db()
    _run_migrations(get_connection())
    logger.info(f"DB lista: {DB_PATH} (schema v{DB_SCHEMA_VERSION})")


# ──────────────────────────────────────────────
# Versionado y migraciones (#3)
# ──────────────────────────────────────────────

# Incrementar cuando cambies el schema (nuevas columnas, tablas, índices).
# NUNCA decrementar — SQLite no soporta rollback de schema.
DB_SCHEMA_VERSION = 1

def _run_migrations(conn: sqlite3.Connection) -> None:
    """
    Aplica migraciones incrementales según PRAGMA user_version.

    Cómo agregar una migración nueva:
      1. Incrementar DB_SCHEMA_VERSION
      2. Agregar un bloque `if version < N:` con los cambios de schema
      3. El bloque DEBE ser idempotente (usar IF NOT EXISTS, IF EXISTS, etc.)

    Ejemplo de migración futura:
        if version < 2:
            conn.execute("ALTER TABLE files ADD COLUMN last_accessed TEXT")
            logger.info("Migración v2: columna last_accessed agregada")
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    logger.debug(f"Schema version actual: {version}, esperada: {DB_SCHEMA_VERSION}")

    if version == DB_SCHEMA_VERSION:
        return   # ya está actualizada

    if version < 1:
        # v1 — schema inicial (ya creado por init_db)
        logger.info("Migración v1: schema inicial aplicado")

    # Actualizar user_version al final de todas las migraciones
    conn.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION}")
    logger.info(f"Schema actualizado a v{DB_SCHEMA_VERSION}")


# ──────────────────────────────────────────────
# FTS5 sync helper
# ──────────────────────────────────────────────

def _sync_fts(
    conn: sqlite3.Connection,
    file_id: int,
    name: str,
    description: str,
    tags: list[str],
) -> None:
    """
    Sincroniza manualmente el registro con FTS5.
    Necesario para mantener el campo 'tags' actualizado
    ya que los triggers solo cubren name y description.
    """
    # Eliminar entrada anterior
    conn.execute(
        "INSERT INTO files_fts(files_fts, rowid, name, description, tags) "
        "VALUES ('delete', ?, ?, ?, '')",
        (file_id, name, description),
    )
    # Insertar entrada actualizada con tags
    conn.execute(
        "INSERT INTO files_fts(rowid, name, description, tags) VALUES (?, ?, ?, ?)",
        (file_id, name, description, " ".join(tags)),
    )


# ──────────────────────────────────────────────
# Operaciones principales
# ──────────────────────────────────────────────

def upsert_file(
    path: str,
    description: str,
    tags: list[str] | None = None,
) -> int:
    """Crea o actualiza metadatos de un archivo."""
    from security import validate_path, sanitize_description, sanitize_tags, save_backup_hash
    ok, result = validate_path(path)
    if not ok:
        raise ValueError(f"Ruta inválida: {result}")
    path = result
    name = Path(path).name
    now  = _utc_now()
    description = sanitize_description(description)
    tags = sanitize_tags(tags or [])

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO files (path, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    name        = excluded.name,
                    description = excluded.description,
                    updated_at  = excluded.updated_at
                RETURNING id
                """,
                (path, name, description, now, now),
            ).fetchone()

            file_id = row["id"]

            # Reemplazar etiquetas
            conn.execute("DELETE FROM file_tags WHERE file_id = ?", (file_id,))

            if tags:
                conn.executemany(
                    "INSERT OR IGNORE INTO tags(name) VALUES (?)",
                    [(t,) for t in tags],
                )
                placeholders = ",".join("?" * len(tags))
                tag_rows = conn.execute(
                    f"SELECT id, name FROM tags WHERE name IN ({placeholders})",
                    tags,
                ).fetchall()
                tag_map = {r["name"]: r["id"] for r in tag_rows}
                conn.executemany(
                    "INSERT OR IGNORE INTO file_tags(file_id, tag_id) VALUES (?, ?)",
                    [(file_id, tag_map[t]) for t in tags if t in tag_map],
                )

            # Sync FTS5 con tags actualizados
            _sync_fts(conn, file_id, name, description, tags)


            # Sincronizar descripción con el Explorador de Windows
            try:
                from metadata import sync_from_db
                sync_from_db(path, description)
            except Exception as _meta_err:
                logger.warning(f"metadata sync falló (no crítico): {_meta_err}")
            return file_id

    except sqlite3.Error as e:
        logger.exception(f"Error en upsert_file ({path}): {e}")
        raise


def get_file(path: str) -> dict | None:
    """Retorna metadatos de un archivo por ruta."""
    path = str(Path(path).resolve(strict=False))

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE path = ?", (path,)
            ).fetchone()

            if not row:
                return None

            tags = conn.execute(
                """
                SELECT t.name FROM tags t
                JOIN file_tags ft ON ft.tag_id = t.id
                WHERE ft.file_id = ?
                ORDER BY t.name
                """,
                (row["id"],),
            ).fetchall()

            return {
                "id":          row["id"],
                "path":        row["path"],
                "name":        row["name"],
                "description": row["description"],
                "tags":        [t["name"] for t in tags],
                "created_at":  row["created_at"],
                "updated_at":  row["updated_at"],
                "file_exists": Path(row["path"]).exists(),  # (#4)
            }

    except sqlite3.Error as e:
        logger.exception(f"Error en get_file ({path}): {e}")
        raise


def delete_file(path: str) -> bool:
    """Elimina metadatos y sincroniza FTS5."""
    path = str(Path(path).resolve(strict=False))

    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, name, description FROM files WHERE path = ?", (path,)
            ).fetchone()

            if not row:
                return False

            file_id = row["id"]

            # Limpiar FTS5 explícitamente antes del DELETE
            conn.execute(
                "INSERT INTO files_fts(files_fts, rowid, name, description, tags) "
                "VALUES ('delete', ?, ?, ?, '')",
                (file_id, row["name"], row["description"]),
            )

            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

            # Limpiar tags huérfanas dentro de la misma transacción (#3)
            conn.execute("""
                DELETE FROM tags
                WHERE id NOT IN (SELECT DISTINCT tag_id FROM file_tags)
            """)

            # Limpiar descripción del Explorador
            try:
                from metadata import remove_explorer_description
                remove_explorer_description(path)
            except Exception as _meta_err:
                logger.warning(f"metadata remove falló (no crítico): {_meta_err}")

            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en delete_file ({path}): {e}")
        raise


# ──────────────────────────────────────────────
# Queries
# ──────────────────────────────────────────────

def _rows_to_dicts(rows, check_exists: bool = False) -> list[dict]:
    """
    Convierte rows SQLite a dicts normalizados.

    check_exists: si True, verifica en disco si cada archivo existe.
    Por defecto False — evita I/O costoso con NAS, OneDrive o miles
    de archivos. La UI puede pasar True cuando necesite mostrar el estado. (#2)

    NOTA: GROUP_CONCAT(DISTINCT t.name) no garantiza orden en SQLite.
    El sorted() de abajo asegura consistencia. (#6)
    """
    return [
        {
            "id":          row["id"],
            "path":        row["path"],
            "name":        row["name"],
            "description": row["description"],
            "tags":        sorted(row["tags"].split(",")) if row["tags"] else [],
            "updated_at":  row["updated_at"],
            "file_exists": Path(row["path"]).exists() if check_exists else None,
        }
        for row in rows
    ]


def list_all_files(check_exists: bool = False) -> list[dict]:
    """
    Lista todos los archivos registrados.
    check_exists=True valida en disco si cada archivo existe. (#2)
    """
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    f.id, f.path, f.name, f.description, f.updated_at,
                    GROUP_CONCAT(DISTINCT t.name) AS tags
                FROM files f
                LEFT JOIN file_tags ft ON ft.file_id = f.id
                LEFT JOIN tags t       ON t.id = ft.tag_id
                GROUP BY f.id
                ORDER BY f.updated_at DESC
                """
            ).fetchall()
            return _rows_to_dicts(rows, check_exists=check_exists)

    except sqlite3.Error as e:
        logger.exception(f"Error en list_all_files: {e}")
        raise


# ──────────────────────────────────────────────
# Búsqueda
# ──────────────────────────────────────────────

def _sanitize_fts_query(query: str) -> str:
    """
    Sanitiza query para FTS5 — evita errores con caracteres especiales.
    Si detecta operadores o símbolos especiales, envuelve en comillas literales.
    """
    query = query.strip()
    if not query:
        return query

    FTS_SPECIAL   = set('"()[]{}:*^~+-')
    FTS_OPERATORS = {"OR", "AND", "NOT"}

    needs_quoting = (
        any(c in query for c in FTS_SPECIAL) or
        any(w.upper() in FTS_OPERATORS for w in query.split())
    )

    if needs_quoting:
        escaped = query.replace('"', '""')
        return f'"{escaped}"'

    return query


def search(query: str, check_exists: bool = False) -> list[dict]:
    """
    Busca archivos usando FTS5 con fallback a LIKE.
    check_exists=True valida en disco si cada archivo existe. (#2)
    """
    query = query.strip()
    if not query:
        return list_all_files(check_exists=check_exists)

    try:
        with get_connection() as conn:
            try:
                safe_query = _sanitize_fts_query(query)
                rows = conn.execute(
                    """
                    SELECT
                        f.id, f.path, f.name, f.description, f.updated_at,
                        GROUP_CONCAT(DISTINCT t.name) AS tags
                    FROM files_fts
                    JOIN files f ON f.id = files_fts.rowid
                    LEFT JOIN file_tags ft ON ft.file_id = f.id
                    LEFT JOIN tags t       ON t.id = ft.tag_id
                    WHERE files_fts MATCH ?
                    GROUP BY f.id
                    ORDER BY bm25(files_fts), f.updated_at DESC
                    """,
                    (safe_query,),
                ).fetchall()

            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                logger.warning(f"FTS5 falló para '{query}', usando fallback LIKE")
                like = f"%{query.lower()}%"
                rows = conn.execute(
                    """
                    SELECT
                        f.id, f.path, f.name, f.description, f.updated_at,
                        GROUP_CONCAT(DISTINCT t.name) AS tags
                    FROM files f
                    LEFT JOIN file_tags ft ON ft.file_id = f.id
                    LEFT JOIN tags t       ON t.id = ft.tag_id
                    WHERE
                        LOWER(f.name)        LIKE ? OR
                        LOWER(f.description) LIKE ? OR
                        LOWER(t.name)        LIKE ?
                    GROUP BY f.id
                    ORDER BY f.updated_at DESC
                    """,
                    (like, like, like),
                ).fetchall()

            return _rows_to_dicts(rows, check_exists=check_exists)

    except sqlite3.Error as e:
        logger.exception(f"Error en search ('{query}'): {e}")
        raise


# ──────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────

def get_all_tags() -> list[str]:
    """Retorna todas las etiquetas ordenadas."""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT name FROM tags ORDER BY name"
            ).fetchall()
            return [r["name"] for r in rows]

    except sqlite3.Error as e:
        logger.exception(f"Error en get_all_tags: {e}")
        raise


def get_stats() -> dict:
    """Retorna estadísticas generales."""
    try:
        with get_connection() as conn:
            total_files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            total_tags  = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
            with_desc   = conn.execute(
                "SELECT COUNT(*) FROM files WHERE description != ''"
            ).fetchone()[0]

            return {
                "total_files":        total_files,
                "total_tags":         total_tags,
                "files_with_desc":    with_desc,
                "files_without_desc": total_files - with_desc,
            }

    except sqlite3.Error as e:
        logger.exception(f"Error en get_stats: {e}")
        raise


def clean_orphan_tags() -> int:
    """
    Elimina tags huérfanas (sin archivos asociados).
    Simplificado — siempre usa su propia conexión (#3).
    Para limpieza dentro de transacciones, usar el inline en delete_file().
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM tags
                WHERE id NOT IN (SELECT DISTINCT tag_id FROM file_tags)
            """)
            removed = cursor.rowcount
            if removed:
                logger.info(f"Tags huérfanas eliminadas: {removed}")
            return removed

    except sqlite3.Error as e:
        logger.exception(f"Error en clean_orphan_tags: {e}")
        raise


def optimize_db() -> None:
    """
    Ejecuta PRAGMA optimize — mejora el rendimiento del planificador de queries.
    Recomendado llamar después de operaciones masivas (indexaciones, deletes en lote).
    SQLite lo ejecuta automáticamente en algunos casos, pero llamarlo explícitamente
    es más confiable tras cambios significativos en los datos. (#7)

    Cuándo llamarlo:
        - Después de indexar muchos archivos de una vez
        - Después de limpiar tags huérfanas masivamente
        - Al cerrar la aplicación (desde tray.py)
    """
    try:
        with get_connection() as conn:
            conn.execute("PRAGMA optimize")
            logger.info("PRAGMA optimize ejecutado")
    except sqlite3.Error as e:
        logger.exception(f"Error en optimize_db: {e}")


# ──────────────────────────────────────────────
# Debug
# ──────────────────────────────────────────────

if __name__ == "__main__":
    init_db()

    upsert_file(
        path=r"C:\Docs\usb.docx",
        description="Política USB corporativa",
        tags=["usb", "seguridad", "corporativo"],
    )

    print(search("usb"))
    print(get_stats())

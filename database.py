"""
database.py — Capa de datos de TagFil

Todas las rutas y el logger vienen de config.py.
No hardcodees rutas aquí.
"""

import sqlite3
import shutil
import json
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import APP_DIR, DB_PATH, get_logger


# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────

DB_BACKUP    = APP_DIR / "tagfil_backup.db"
LAST_BACKUP  = APP_DIR / "last_backup.txt"   # control de frecuencia de backup (#2)
BACKUP_EVERY = 3600                           # segundos mínimos entre backups (1 hora)
BACKUP_KEEP  = 3                              # generaciones diarias previas que se conservan
BACKUP_ROTATE_EVERY = 24 * 3600               # una generación nueva como máximo por día


def _backup_generation(n: int) -> Path:
    """Ruta de la generación n del backup (0 = más reciente)."""
    if n == 0:
        return DB_BACKUP
    return DB_BACKUP.with_name(f"{DB_BACKUP.stem}.{n}{DB_BACKUP.suffix}")


def _rotate_backups() -> None:
    """Desplaza las generaciones (.2→.3, .1→.2, actual→.1) como máximo una vez al día."""
    if not DB_BACKUP.exists():
        return
    # La fecha del backup principal cambia en cada copia (normalmente cada
    # hora). Medirla impediría rotar durante el uso continuo de la aplicación.
    generation = _backup_generation(1)
    if generation.exists():
        age = datetime.now(timezone.utc).timestamp() - generation.stat().st_mtime
        if age < BACKUP_ROTATE_EVERY:
            return
    for n in range(BACKUP_KEEP, 1, -1):
        older, newer = _backup_generation(n), _backup_generation(n - 1)
        if newer.exists():
            shutil.copy2(newer, older)
    # La fecha de .1 registra la rotación, no la fecha de la copia original.
    shutil.copyfile(DB_BACKUP, generation)
    generation.touch()


def _is_healthy_db(path: Path) -> bool:
    """True si el archivo SQLite pasa integrity_check (sin abrir la DB real)."""
    if not path.exists():
        return False
    conn = None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    except sqlite3.Error:
        return False
    finally:
        if conn:
            conn.close()


def _snapshot_before_migration() -> None:
    """Copia de seguridad previa a migrar el schema (las migraciones no son reversibles)."""
    if not DB_PATH.exists():
        return
    src = dest = None
    try:
        src = sqlite3.connect(DB_PATH)
        version = src.execute("PRAGMA user_version").fetchone()[0]
        has_files = src.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='files'"
        ).fetchone()
        if version >= DB_SCHEMA_VERSION or not has_files:
            return
        target = APP_DIR / f"tagfil_pre_migracion_v{version}.db"
        dest = sqlite3.connect(target)
        src.backup(dest)
        logger.info(f"Copia previa a la migración v{version}→v{DB_SCHEMA_VERSION}: {target}")
    except sqlite3.Error as e:
        logger.warning(f"No se pudo crear la copia previa a la migración: {e}")
    finally:
        if dest: dest.close()
        if src:  src.close()
DB_SCHEMA_VERSION = 5

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _utc_now() -> str:
    """Retorna timestamp UTC consistente para SQLite. (#1)"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_path(path: str | None) -> str:
    """Hash estable para auditar rutas sin guardarlas completas."""
    if not path:
        return ""
    return hashlib.sha256(str(path).encode("utf-8", errors="ignore")).hexdigest()


def hash_path(path: str | None) -> str:
    """Hash público de ruta para reportes que no deben exponer rutas completas."""
    return _hash_path(path)


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

    # No sobrescribir el último backup bueno con un estado dañado
    # (integrity_check normal no ve el FTS ni errores lógicos)
    if not check_integrity() or not check_fts_integrity():
        logger.error("Backup omitido: la DB actual no pasa las verificaciones; se conserva el anterior")
        return False

    src  = None
    dest = None

    try:
        _rotate_backups()
        src  = sqlite3.connect(DB_PATH)

        # WAL checkpoint antes del backup — garantiza que todos los datos
        # del archivo .db-wal estén en el archivo principal antes de copiar (#1)
        src.execute("PRAGMA wal_checkpoint(FULL)")

        dest = sqlite3.connect(DB_BACKUP)
        src.backup(dest)
        dest.close()
        dest = None

        # Registrar timestamp del backup exitoso (#2)
        LAST_BACKUP.write_text(str(datetime.now(timezone.utc).timestamp()))

        try:
            from security import save_backup_hash
            save_backup_hash()
        except Exception as hash_err:
            logger.warning(f"No se pudo guardar hash del backup: {hash_err}")

        try:
            from security import encrypt_backup_if_enabled
            encrypt_backup_if_enabled()
        except Exception as enc_err:
            logger.warning(f"No se pudo crear backup cifrado: {enc_err}")

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
    """Recupera la DB desde la generación de backup más reciente que esté sana."""
    candidates = [g for g in (_backup_generation(n) for n in range(BACKUP_KEEP + 1)) if g.exists()]
    if not candidates:
        logger.error("No existe backup para recuperación")
        return False

    chosen = None
    for cand in candidates:
        if cand == DB_BACKUP:
            try:
                from security import verify_backup_hash
                ok, msg = verify_backup_hash()
                if not ok and "No hay hash" not in msg:
                    logger.error(f"Backup principal descartado: {msg}")
                    continue
                if not ok:
                    logger.warning(f"Recovery sin hash verificable: {msg}")
            except Exception as hash_err:
                logger.warning(f"No se pudo verificar hash del backup: {hash_err}")
        if _is_healthy_db(cand):
            chosen = cand
            break
        logger.error(f"Backup descartado (integrity_check falló): {cand.name}")

    if chosen is None:
        logger.error("Ningún backup pasó la verificación")
        return False

    try:
        corrupted = APP_DIR / "tagfil_corrupted.db"
        if DB_PATH.exists():
            shutil.move(str(DB_PATH), str(corrupted))
        # Los -wal/-shm del archivo dañado no deben quedar junto a la DB restaurada
        for suffix in ("-wal", "-shm"):
            stale = Path(str(DB_PATH) + suffix)
            if stale.exists():
                shutil.move(str(stale), str(corrupted) + suffix)
        shutil.copy2(chosen, DB_PATH)
        logger.warning(f"DB recuperada desde {chosen.name}. Corrupto guardado en: {corrupted}")
        return True

    except (OSError, shutil.Error) as e:   # específico en lugar de Exception (#3)
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
    # LOWER() de SQLite solo baja ASCII: «Éxito»/«Ñandú» no coincidirían
    conn.create_function("ulower", 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True)
    return conn


@contextmanager
def _managed_connection():
    """Abre una conexión, maneja commit/rollback y siempre la cierra."""
    conn = get_connection()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Inicialización
# ──────────────────────────────────────────────

def init_db() -> None:
    """
    Inicializa tablas, índices y tabla FTS5 standalone.
    Verifica integridad y crea backup automático.
    """
    APP_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists() and not check_integrity():
        logger.warning("DB corrupta detectada")
        if _attempt_recovery():
            logger.info("Recovery exitoso")
        else:
            logger.error("Recovery fallido")

    with _managed_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                path            TEXT    NOT NULL UNIQUE,
                name            TEXT    NOT NULL,
                original_name   TEXT    DEFAULT '',
                short_name      TEXT    DEFAULT '',
                document_type   TEXT    DEFAULT '',
                entity          TEXT    DEFAULT '',
                document_date   TEXT    DEFAULT '',
                sequence_number INTEGER,
                qualifier       TEXT    DEFAULT '',
                provider        TEXT    DEFAULT 'local',
                description     TEXT    DEFAULT '',
                deleted_at      TEXT    DEFAULT NULL,
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
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

            CREATE TABLE IF NOT EXISTS audit_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                action      TEXT    NOT NULL,
                file_id     INTEGER,
                path_hash   TEXT    DEFAULT '',
                file_name   TEXT    DEFAULT '',
                details     TEXT    DEFAULT '{}',
                created_at  TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_audit_events_action
                ON audit_events(action);
            CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
                ON audit_events(created_at);

            -- FTS5 standalone (sin content table): name/description/tags viven
            -- solo en el índice. La sincronización la hace _reindex_file(),
            -- una única función llamada desde cada operación que cambia datos.
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                name,
                description,
                tags,
                tokenize='unicode61 remove_diacritics 2'
            );
        """)

    _snapshot_before_migration()

    with _managed_connection() as conn:
        _run_migrations(conn)

    try:
        from tagfil.settings import get_settings
        prune_audit_events(int(get_settings().get("audit_retention") or 0))
    except Exception as e:
        logger.debug(f"No se pudo aplicar la retención de auditoría: {e}")

    backup_db()
    logger.info(f"DB lista: {DB_PATH} (schema v{DB_SCHEMA_VERSION})")


# ──────────────────────────────────────────────
# Versionado y migraciones (#3)
# ──────────────────────────────────────────────

# Incrementar cuando cambies el schema (nuevas columnas, tablas, índices).
# NUNCA decrementar — SQLite no soporta rollback de schema.

def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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

    if version < 2:
        # v2 — columna deleted_at para soft-delete (papelera)
        _add_column_if_missing(conn, "files", "deleted_at", "TEXT DEFAULT NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_deleted_at ON files(deleted_at)")
        logger.info("Migración v2: columna deleted_at agregada (papelera)")

    if version < 3:
        # v3 — metadatos estructurados para nombres cortos e integraciones futuras
        columns = {
            "original_name": "TEXT DEFAULT ''",
            "short_name": "TEXT DEFAULT ''",
            "document_type": "TEXT DEFAULT ''",
            "entity": "TEXT DEFAULT ''",
            "document_date": "TEXT DEFAULT ''",
            "sequence_number": "INTEGER",
            "qualifier": "TEXT DEFAULT ''",
            "provider": "TEXT DEFAULT 'local'",
        }
        for column, definition in columns.items():
            _add_column_if_missing(conn, "files", column, definition)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_short_name ON files(short_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_document_type ON files(document_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_entity ON files(entity)")
        logger.info("Migración v3: metadatos estructurados agregados")

    if version < 4:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                action      TEXT    NOT NULL,
                file_id     INTEGER,
                path_hash   TEXT    DEFAULT '',
                file_name   TEXT    DEFAULT '',
                details     TEXT    DEFAULT '{}',
                created_at  TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_events_action
                ON audit_events(action);
            CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
                ON audit_events(created_at);
        """)
        logger.info("Migración v4: auditoría de eventos agregada")

    if version < 5:
        # v5 — FTS5 standalone: elimina triggers y content table (columna
        # 'tags' inexistente en files, doble 'delete', tokens huérfanos)
        _rebuild_fts_index(conn)
        logger.info("Migración v5: índice FTS reconstruido (standalone)")

    # Actualizar user_version al final de todas las migraciones
    conn.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION}")
    logger.info(f"Schema actualizado a v{DB_SCHEMA_VERSION}")


# ──────────────────────────────────────────────
# FTS5 sync helper
# ──────────────────────────────────────────────

def _reindex_file(conn: sqlite3.Connection, file_id: int) -> None:
    """
    Reindexa un archivo en FTS5 leyendo su estado actual desde la DB.
    Única vía de escritura al índice: borra la entrada previa por rowid
    (siempre válido en una tabla standalone) y la inserta de nuevo.
    """
    conn.execute("DELETE FROM files_fts WHERE rowid = ?", (file_id,))
    row = conn.execute(
        """
        SELECT name, description, short_name, document_type, entity,
               document_date, qualifier, provider
        FROM files WHERE id = ?
        """,
        (file_id,),
    ).fetchone()
    if row is None:
        return
    tags = [
        r[0] for r in conn.execute(
            """
            SELECT t.name FROM tags t
            JOIN file_tags ft ON ft.tag_id = t.id
            WHERE ft.file_id = ?
            ORDER BY t.name
            """,
            (file_id,),
        )
    ]
    extra = [
        row["short_name"], row["document_type"], row["entity"],
        row["document_date"], row["qualifier"], row["provider"],
    ]
    terms = " ".join(t for t in tags + extra if t)
    conn.execute(
        "INSERT INTO files_fts(rowid, name, description, tags) VALUES (?, ?, ?, ?)",
        (file_id, row["name"] or "", row["description"] or "", terms),
    )


def _rebuild_fts_index(conn: sqlite3.Connection) -> None:
    """Descarta triggers y tabla FTS anteriores y reconstruye el índice completo."""
    conn.executescript("""
        DROP TRIGGER IF EXISTS files_fts_insert;
        DROP TRIGGER IF EXISTS files_fts_delete;
        DROP TRIGGER IF EXISTS files_fts_update;
        DROP TABLE IF EXISTS files_fts;
        CREATE VIRTUAL TABLE files_fts USING fts5(
            name,
            description,
            tags,
            tokenize='unicode61 remove_diacritics 2'
        );
    """)
    for (file_id,) in conn.execute("SELECT id FROM files").fetchall():
        _reindex_file(conn, file_id)


def check_fts_integrity() -> bool:
    """Verifica la estructura del índice FTS5 (integrity_check normal no la ve)."""
    try:
        with _managed_connection() as conn:
            conn.execute("INSERT INTO files_fts(files_fts, rank) VALUES('integrity-check', 0)")
        return True
    except sqlite3.Error as e:
        logger.error(f"Índice FTS dañado: {e}")
        return False


def rebuild_search_index() -> int:
    """Reconstruye el índice de búsqueda desde cero. Retorna archivos indexados."""
    with _managed_connection() as conn:
        _rebuild_fts_index(conn)
        return conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]


def prune_audit_events(keep: int) -> int:
    """Conserva solo los últimos `keep` eventos de auditoría. 0 o negativo = sin límite."""
    if keep <= 0:
        return 0
    with _managed_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM audit_events
            WHERE id <= COALESCE(
                (SELECT id FROM audit_events ORDER BY id DESC LIMIT 1 OFFSET ?), 0
            )
            """,
            (keep,),
        )
        if cur.rowcount:
            logger.info(f"Auditoría: {cur.rowcount} eventos antiguos eliminados (retención {keep})")
        return cur.rowcount


def _log_event(
    conn: sqlite3.Connection,
    action: str,
    file_id: int | None = None,
    path: str | None = None,
    details: dict | None = None,
) -> None:
    """Registra un evento sin guardar rutas completas ni descripciones."""
    try:
        conn.execute(
            """
            INSERT INTO audit_events (
                action, file_id, path_hash, file_name, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                file_id,
                _hash_path(path),
                Path(path).name if path else "",
                json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
                _utc_now(),
            ),
        )
    except sqlite3.Error as e:
        logger.warning(f"No se pudo registrar auditoría ({action}): {e}")


# ──────────────────────────────────────────────
# Operaciones principales
# ──────────────────────────────────────────────

class _Keep:
    """Valor centinela: «conservar lo que ya hay guardado»."""
    def __repr__(self) -> str:
        return "KEEP"


KEEP = _Keep()


def _clean(value, default: str = "") -> str:
    return default if value is None else str(value).strip()


def upsert_file(
    path: str,
    description: "str | _Keep",
    tags: "list[str] | None | _Keep" = KEEP,
    short_name: "str | None | _Keep" = KEEP,
    document_type: "str | None | _Keep" = KEEP,
    entity: "str | None | _Keep" = KEEP,
    document_date: "str | None | _Keep" = KEEP,
    sequence_number: "int | str | None | _Keep" = KEEP,
    qualifier: "str | None | _Keep" = KEEP,
    provider: "str | None | _Keep" = KEEP,
    sync_metadata: bool | None = None,
) -> int:
    """
    Crea o actualiza metadatos de un archivo.

    Actualización parcial: un argumento omitido (KEEP) conserva el valor ya
    guardado. Pasar None o '' lo vacía explícitamente. Al crear, los campos
    omitidos toman su valor por defecto. Si el archivo estaba en la papelera,
    volver a registrarlo lo restaura.
    """
    from security import validate_path, sanitize_description, sanitize_tags
    ok, result = validate_path(path)
    if not ok:
        raise ValueError(f"Ruta inválida: {result}")
    path = result
    name = Path(path).name
    now = _utc_now()

    try:
        with _managed_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM files WHERE path = ?", (path,)
            ).fetchone()

            def pick(value, column: str, default: str = "") -> str:
                if isinstance(value, _Keep):
                    if existing is not None and existing[column] not in (None, ""):
                        return existing[column]
                    return default
                return _clean(value, default)

            description = (
                existing["description"] or ""
                if isinstance(description, _Keep) and existing is not None
                else sanitize_description("" if isinstance(description, _Keep) else description)
            )
            short_name = pick(short_name, "short_name")
            document_type = pick(document_type, "document_type")
            entity = pick(entity, "entity")
            document_date = pick(document_date, "document_date")
            qualifier = pick(qualifier, "qualifier")
            provider = pick(provider, "provider", "local") or "local"

            if isinstance(sequence_number, _Keep):
                sequence_number = existing["sequence_number"] if existing is not None else None
            elif sequence_number in ("", None):
                sequence_number = None
            else:
                sequence_number = int(sequence_number)

            row = conn.execute(
                """
                INSERT INTO files (
                    path, name, original_name, short_name,
                    document_type, entity, document_date, sequence_number,
                    qualifier, provider, description, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    name            = excluded.name,
                    original_name   = CASE
                        WHEN files.original_name IS NULL OR files.original_name = ''
                        THEN excluded.original_name
                        ELSE files.original_name
                    END,
                    short_name      = excluded.short_name,
                    document_type   = excluded.document_type,
                    entity          = excluded.entity,
                    document_date   = excluded.document_date,
                    sequence_number = excluded.sequence_number,
                    qualifier       = excluded.qualifier,
                    provider        = excluded.provider,
                    description     = excluded.description,
                    updated_at      = excluded.updated_at,
                    deleted_at      = NULL
                RETURNING id
                """,
                (
                    path, name, name, short_name,
                    document_type, entity, document_date, sequence_number,
                    qualifier, provider, description, now, now,
                ),
            ).fetchone()

            file_id = row["id"]

            # Etiquetas: solo se reemplazan si el llamador las pasó
            if not isinstance(tags, _Keep):
                tags = sanitize_tags(tags or [])
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

            _reindex_file(conn, file_id)

            _log_event(
                conn,
                "file.upsert",
                file_id=file_id,
                path=path,
                details={
                    "has_description": bool(description),
                    "has_short_name": bool(short_name),
                    "provider": provider,
                },
            )

            # Sincronizar descripción con el Explorador de Windows
            if sync_metadata is None:
                try:
                    from tagfil.settings import get_settings
                    sync_metadata = bool(get_settings().get("sync_explorer_metadata"))
                except Exception:
                    sync_metadata = True
            if sync_metadata:
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
        with _managed_connection() as conn:
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
                "original_name": row["original_name"],
                "short_name": row["short_name"],
                "document_type": row["document_type"],
                "entity": row["entity"],
                "document_date": row["document_date"],
                "sequence_number": row["sequence_number"],
                "qualifier": row["qualifier"],
                "provider": row["provider"],
                "description": row["description"],
                "tags":        [t["name"] for t in tags],
                "created_at":  row["created_at"],
                "updated_at":  row["updated_at"],
                "file_exists": Path(row["path"]).exists(),  # (#4)
            }

    except sqlite3.Error as e:
        logger.exception(f"Error en get_file ({path}): {e}")
        raise


def update_file_path(old_path: str, new_path: str) -> bool:
    """Actualiza la ruta y nombre de un registro existente."""
    old_path = str(Path(old_path).resolve(strict=False))
    new_path = str(Path(new_path).resolve(strict=False))
    new_name = Path(new_path).name

    try:
        with _managed_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    id, description, short_name, document_type, entity,
                    document_date, qualifier, provider
                FROM files
                WHERE path = ?
                """,
                (old_path,),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                """
                UPDATE files
                SET path = ?, name = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_path, new_name, _utc_now(), row["id"]),
            )

            _reindex_file(conn, row["id"])
            _log_event(
                conn,
                "file.rename",
                file_id=row["id"],
                path=new_path,
                details={
                    "old_path_hash": _hash_path(old_path),
                    "old_name": Path(old_path).name,
                },
            )
            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en update_file_path ({old_path} -> {new_path}): {e}")
        raise


def delete_file(path: str) -> bool:
    """
    Mueve el archivo a la papelera (soft-delete).
    Usa deleted_at para marcar como eliminado sin borrar datos.
    Para eliminar permanentemente, usar purge_file() o empty_trash().
    """
    path = str(Path(path).resolve(strict=False))

    try:
        with _managed_connection() as conn:
            row = conn.execute(
                "SELECT id, deleted_at FROM files WHERE path = ?", (path,)
            ).fetchone()

            if not row:
                return False

            if row["deleted_at"] is not None:
                return True  # ya está en papelera

            conn.execute(
                "UPDATE files SET deleted_at = ? WHERE id = ?",
                (_utc_now(), row["id"]),
            )
            _log_event(conn, "file.trash", file_id=row["id"], path=path)
            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en delete_file ({path}): {e}")
        raise


def purge_file(path: str) -> bool:
    """Elimina permanentemente un archivo de la DB (sin papelera)."""
    path = str(Path(path).resolve(strict=False))

    try:
        with _managed_connection() as conn:
            row = conn.execute(
                "SELECT id, name, description FROM files WHERE path = ?", (path,)
            ).fetchone()

            if not row:
                return False

            file_id = row["id"]

            conn.execute("DELETE FROM files_fts WHERE rowid = ?", (file_id,))
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.execute("""
                DELETE FROM tags
                WHERE id NOT IN (SELECT DISTINCT tag_id FROM file_tags)
            """)
            _log_event(conn, "file.purge", file_id=file_id, path=path)

            try:
                from metadata import remove_explorer_description
                remove_explorer_description(path)
            except Exception as _meta_err:
                logger.warning(f"metadata remove falló (no crítico): {_meta_err}")

            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en purge_file ({path}): {e}")
        raise


def move_to_trash(path: str) -> bool:
    """Alias explícito de delete_file — mueve a papelera."""
    return delete_file(path)


def restore_from_trash(path: str) -> bool:
    """Restaura un archivo desde la papelera (limpia deleted_at)."""
    path = str(Path(path).resolve(strict=False))

    try:
        with _managed_connection() as conn:
            row = conn.execute(
                "SELECT id, deleted_at FROM files WHERE path = ?", (path,)
            ).fetchone()

            if not row or row["deleted_at"] is None:
                return False  # no existe o no está en papelera

            conn.execute(
                "UPDATE files SET deleted_at = NULL, updated_at = ? WHERE id = ?",
                (_utc_now(), row["id"]),
            )
            _log_event(conn, "file.restore", file_id=row["id"], path=path)
            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en restore_from_trash ({path}): {e}")
        raise


def empty_trash() -> int:
    """
    Elimina permanentemente todos los archivos en la papelera.
    Retorna la cantidad de archivos eliminados.
    """
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, description FROM files WHERE deleted_at IS NOT NULL"
            ).fetchall()

            if not rows:
                return 0

            ids = [r["id"] for r in rows]
            placeholders = ",".join("?" * len(ids))
            conn.execute(f"DELETE FROM files_fts WHERE rowid IN ({placeholders})", ids)
            conn.execute(f"DELETE FROM files WHERE id IN ({placeholders})", ids)
            conn.execute("""
                DELETE FROM tags
                WHERE id NOT IN (SELECT DISTINCT tag_id FROM file_tags)
            """)
            _log_event(
                conn,
                "trash.empty",
                details={"purged_count": len(rows)},
            )

            logger.info(f"Papelera vaciada: {len(rows)} archivos eliminados permanentemente")
            return len(rows)

    except sqlite3.Error as e:
        logger.exception(f"Error en empty_trash: {e}")
        raise


def list_trash() -> list[dict]:
    """Lista todos los archivos en la papelera ordenados por fecha de eliminación."""
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    f.id, f.path, f.name, f.description,
                    f.updated_at, f.deleted_at,
                    GROUP_CONCAT(DISTINCT t.name) AS tags
                FROM files f
                LEFT JOIN file_tags ft ON ft.file_id = f.id
                LEFT JOIN tags t       ON t.id = ft.tag_id
                WHERE f.deleted_at IS NOT NULL
                GROUP BY f.id
                ORDER BY f.deleted_at DESC
                """
            ).fetchall()

            return [
                {
                    "id":          row["id"],
                    "path":        row["path"],
                    "name":        row["name"],
                    "description": row["description"],
                    "tags":        sorted(row["tags"].split(",")) if row["tags"] else [],
                    "updated_at":  row["updated_at"],
                    "deleted_at":  row["deleted_at"],
                    "file_exists": Path(row["path"]).exists(),
                }
                for row in rows
            ]

    except sqlite3.Error as e:
        logger.exception(f"Error en list_trash: {e}")
        raise


def get_trash_stats() -> dict:
    """Estadísticas de la papelera: total, tipos, espacio recuperable estimado."""
    try:
        with _managed_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM files WHERE deleted_at IS NOT NULL"
            ).fetchone()[0]

            oldest = conn.execute(
                "SELECT MIN(deleted_at) FROM files WHERE deleted_at IS NOT NULL"
            ).fetchone()[0]

            # Contar por extensión
            rows = conn.execute(
                "SELECT name FROM files WHERE deleted_at IS NOT NULL"
            ).fetchall()

            folders = sum(1 for r in rows if not Path(r["name"]).suffix)
            files   = total - folders

            return {
                "total":        total,
                "total_files":  files,
                "total_folders": folders,
                "oldest_deleted_at": oldest,
            }

    except sqlite3.Error as e:
        logger.exception(f"Error en get_trash_stats: {e}")
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
    result = []
    for row in rows:
        p = Path(row["path"])
        exists = p.exists() if check_exists else None
        try:
            size_b = p.stat().st_size if (check_exists and exists) else 0
        except OSError:
            size_b = 0
        result.append({
            "id":          row["id"],
            "path":        row["path"],
            "name":        row["name"],
            "original_name": row["original_name"],
            "short_name": row["short_name"],
            "document_type": row["document_type"],
            "entity": row["entity"],
            "document_date": row["document_date"],
            "sequence_number": row["sequence_number"],
            "qualifier": row["qualifier"],
            "provider": row["provider"],
            "description": row["description"],
            "tags":        sorted(row["tags"].split(",")) if row["tags"] else [],
            "updated_at":  row["updated_at"],
            "file_exists": exists,
            "size":        size_b,
        })
    return result


def list_all_files(check_exists: bool = False, limit: int | None = None) -> list[dict]:
    """
    Lista todos los archivos registrados.
    check_exists=True valida en disco si cada archivo existe. (#2)
    limit recorta en SQL, antes de consultar el disco.
    """
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    f.id, f.path, f.name, f.original_name, f.short_name,
                    f.document_type, f.entity, f.document_date,
                    f.sequence_number, f.qualifier, f.provider,
                    f.description, f.updated_at,
                    GROUP_CONCAT(DISTINCT t.name) AS tags
                FROM files f
                LEFT JOIN file_tags ft ON ft.file_id = f.id
                LEFT JOIN tags t       ON t.id = ft.tag_id
                WHERE f.deleted_at IS NULL
                GROUP BY f.id
                ORDER BY f.updated_at DESC
                LIMIT ?
                """,
                (int(limit) if limit else -1,),
            ).fetchall()
            return _rows_to_dicts(rows, check_exists=check_exists)

    except sqlite3.Error as e:
        logger.exception(f"Error en list_all_files: {e}")
        raise


def get_all_files(check_exists: bool = False) -> list[dict]:
    """Alias usado por la UI para listar archivos activos."""
    return list_all_files(check_exists=check_exists)


def get_recent_files(limit: int = 6, check_exists: bool = False) -> list[dict]:
    """Retorna los archivos activos modificados más recientemente."""
    limit = max(1, int(limit or 1))
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    f.id, f.path, f.name, f.original_name, f.short_name,
                    f.document_type, f.entity, f.document_date,
                    f.sequence_number, f.qualifier, f.provider,
                    f.description, f.updated_at,
                    GROUP_CONCAT(DISTINCT t.name) AS tags
                FROM files f
                LEFT JOIN file_tags ft ON ft.file_id = f.id
                LEFT JOIN tags t       ON t.id = ft.tag_id
                WHERE f.deleted_at IS NULL
                GROUP BY f.id
                ORDER BY f.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return _rows_to_dicts(rows, check_exists=check_exists)

    except sqlite3.Error as e:
        logger.exception(f"Error en get_recent_files: {e}")
        raise


def get_untagged_files(check_exists: bool = False) -> list[dict]:
    """Lista archivos activos que no tienen ninguna etiqueta."""
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    f.id, f.path, f.name, f.original_name, f.short_name,
                    f.document_type, f.entity, f.document_date,
                    f.sequence_number, f.qualifier, f.provider,
                    f.description, f.updated_at,
                    '' AS tags
                FROM files f
                WHERE f.deleted_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM file_tags ft WHERE ft.file_id = f.id
                  )
                ORDER BY f.updated_at DESC
                """
            ).fetchall()
            return _rows_to_dicts(rows, check_exists=check_exists)

    except sqlite3.Error as e:
        logger.exception(f"Error en get_untagged_files: {e}")
        raise


# ──────────────────────────────────────────────
# Búsqueda
# ──────────────────────────────────────────────

def _sanitize_fts_query(query: str) -> str:
    """
    Convierte lo que escribe el usuario en una consulta FTS5 segura con
    coincidencia por prefijo: «fact 2026» → "fact"* "2026"*  (AND implícito).
    Cada término va entre comillas, así que operadores y símbolos son literales.
    Devuelve '' si no queda ningún término utilizable.
    """
    terms = []
    for raw in query.split():
        term = raw.replace('"', "").strip()
        if any(ch.isalnum() for ch in term):
            terms.append(f'"{term}"*')
    return " ".join(terms)


def _escape_like(text: str) -> str:
    """Escapa % y _ para usar el texto del usuario de forma literal en LIKE."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search(query: str, check_exists: bool = False, limit: int | None = None) -> list[dict]:
    """
    Busca archivos usando FTS5 (por prefijo) con fallback a LIKE para
    subcadenas. check_exists=True valida en disco solo las filas devueltas;
    limit recorta en SQL.
    """
    query = query.strip()
    if not query:
        return list_all_files(check_exists=check_exists, limit=limit)

    sql_limit = int(limit) if limit else -1

    try:
        with _managed_connection() as conn:
            like = f"%{_escape_like(query.lower())}%"
            like_sql = """
                    SELECT
                        f.id, f.path, f.name, f.original_name, f.short_name,
                        f.document_type, f.entity, f.document_date,
                        f.sequence_number, f.qualifier, f.provider,
                        f.description, f.updated_at,
                        GROUP_CONCAT(DISTINCT t.name) AS tags
                    FROM files f
                    LEFT JOIN file_tags ft ON ft.file_id = f.id
                    LEFT JOIN tags t       ON t.id = ft.tag_id
                    WHERE f.deleted_at IS NULL AND (
                        ULOWER(f.name)          LIKE ? ESCAPE '\\' OR
                        ULOWER(f.original_name) LIKE ? ESCAPE '\\' OR
                        ULOWER(f.short_name)    LIKE ? ESCAPE '\\' OR
                        ULOWER(f.document_type) LIKE ? ESCAPE '\\' OR
                        ULOWER(f.entity)        LIKE ? ESCAPE '\\' OR
                        ULOWER(f.document_date) LIKE ? ESCAPE '\\' OR
                        ULOWER(f.qualifier)     LIKE ? ESCAPE '\\' OR
                        ULOWER(f.provider)      LIKE ? ESCAPE '\\' OR
                        ULOWER(f.description)   LIKE ? ESCAPE '\\' OR
                        ULOWER(t.name)          LIKE ? ESCAPE '\\')
                    GROUP BY f.id
                    ORDER BY f.updated_at DESC
                    LIMIT ?
                    """
            like_args = (like,) * 10 + (sql_limit,)
            safe_query = _sanitize_fts_query(query)
            if not safe_query:
                rows = conn.execute(like_sql, like_args).fetchall()
                return _rows_to_dicts(rows, check_exists=check_exists)
            try:
                rows = conn.execute(
                    """
                    SELECT
                        f.id, f.path, f.name, f.original_name, f.short_name,
                        f.document_type, f.entity, f.document_date,
                        f.sequence_number, f.qualifier, f.provider,
                        f.description, f.updated_at,
                        GROUP_CONCAT(DISTINCT t.name) AS tags
                    FROM files_fts
                    JOIN files f ON f.id = files_fts.rowid
                    LEFT JOIN file_tags ft ON ft.file_id = f.id
                    LEFT JOIN tags t       ON t.id = ft.tag_id
                    WHERE files_fts MATCH ? AND f.deleted_at IS NULL
                    GROUP BY f.id
                    ORDER BY bm25(files_fts), f.updated_at DESC
                    LIMIT ?
                    """,
                    (safe_query, sql_limit),
                ).fetchall()
                if not rows:
                    rows = conn.execute(like_sql, like_args).fetchall()

            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                logger.warning("FTS5 falló para la consulta, usando fallback LIKE")
                rows = conn.execute(like_sql, like_args).fetchall()

            return _rows_to_dicts(rows, check_exists=check_exists)

    except sqlite3.Error as e:
        logger.exception(f"Error en search: {e}")
        raise


# ──────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────

def get_all_tags() -> list[str]:
    """Retorna todas las etiquetas ordenadas."""
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                "SELECT name FROM tags ORDER BY name"
            ).fetchall()
            return [r["name"] for r in rows]

    except sqlite3.Error as e:
        logger.exception(f"Error en get_all_tags: {e}")
        raise


def get_tag_counts() -> list[dict]:
    """Retorna etiquetas con conteo de archivos activos asociados."""
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.name,
                    COUNT(DISTINCT CASE
                        WHEN f.deleted_at IS NULL THEN ft.file_id
                    END) AS count
                FROM tags t
                LEFT JOIN file_tags ft ON ft.tag_id = t.id
                LEFT JOIN files f       ON f.id = ft.file_id
                GROUP BY t.id, t.name
                ORDER BY t.name COLLATE NOCASE
                """
            ).fetchall()
            return [{"name": row["name"], "count": row["count"]} for row in rows]

    except sqlite3.Error as e:
        logger.exception(f"Error en get_tag_counts: {e}")
        raise


def create_tag(name: str) -> bool:
    """Crea una etiqueta sin asociarla todavía a un archivo."""
    from security import sanitize_tags

    tags = sanitize_tags([name])
    if not tags:
        raise ValueError("Nombre de etiqueta inválido")

    try:
        with _managed_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tags[0],))
            _log_event(conn, "tag.create", details={"tag": tags[0]})
            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en create_tag ({name}): {e}")
        raise


def delete_tag(name: str) -> bool:
    """Elimina una etiqueta y la quita de los archivos que la usaban."""
    name = (name or "").strip()
    if not name:
        return False

    try:
        with _managed_connection() as conn:
            tag = conn.execute(
                "SELECT id FROM tags WHERE name = ? COLLATE NOCASE",
                (name,),
            ).fetchone()
            if not tag:
                return False

            rows = conn.execute(
                """
                SELECT
                    f.id, f.name, f.description, f.short_name,
                    f.document_type, f.entity, f.document_date,
                    f.qualifier, f.provider
                FROM files f
                JOIN file_tags ft ON ft.file_id = f.id
                WHERE ft.tag_id = ?
                """,
                (tag["id"],),
            ).fetchall()

            affected_ids = [row["id"] for row in rows]
            conn.execute("DELETE FROM file_tags WHERE tag_id = ?", (tag["id"],))
            conn.execute("DELETE FROM tags WHERE id = ?", (tag["id"],))

            for row in rows:
                _reindex_file(conn, row["id"])

            logger.info(f"Etiqueta eliminada: {name} ({len(affected_ids)} archivos actualizados)")
            _log_event(
                conn,
                "tag.delete",
                details={"tag": name, "affected_count": len(affected_ids)},
            )
            return True

    except sqlite3.Error as e:
        logger.exception(f"Error en delete_tag ({name}): {e}")
        raise


def get_stats() -> dict:
    """Retorna estadísticas generales."""
    try:
        with _managed_connection() as conn:
            total_files = conn.execute("SELECT COUNT(*) FROM files WHERE deleted_at IS NULL").fetchone()[0]
            total_tags  = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
            with_desc   = conn.execute(
                "SELECT COUNT(*) FROM files WHERE description != '' AND deleted_at IS NULL"
            ).fetchone()[0]

            # Calcular espacio total sumando tamaños en disco
            paths = conn.execute(
                "SELECT path FROM files WHERE deleted_at IS NULL"
            ).fetchall()
            total_size_bytes = 0
            for row in paths:
                try:
                    p = Path(row["path"])
                    if p.exists():
                        total_size_bytes += p.stat().st_size
                except OSError:
                    pass   # archivo inaccesible o ruta inválida — se omite

            # Archivos sin ninguna etiqueta
            without_tags = conn.execute(
                "SELECT COUNT(*) FROM files WHERE deleted_at IS NULL "
                "AND id NOT IN (SELECT DISTINCT file_id FROM file_tags)"
            ).fetchone()[0]

            return {
                "total_files":        total_files,
                "total_tags":         total_tags,
                "files_with_desc":    with_desc,
                "files_without_desc": total_files - with_desc,
                "files_without_tags": without_tags,
                "total_size_bytes":   total_size_bytes,
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
        with _managed_connection() as conn:
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


def get_audit_events(limit: int = 100) -> list[dict]:
    """Retorna los eventos recientes de auditoría."""
    limit = max(1, min(int(limit or 100), 1000))
    try:
        with _managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, action, file_id, path_hash, file_name, details, created_at
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            events = []
            for row in rows:
                try:
                    details = json.loads(row["details"] or "{}")
                except json.JSONDecodeError:
                    details = {}
                events.append({
                    "id": row["id"],
                    "action": row["action"],
                    "file_id": row["file_id"],
                    "path_hash": row["path_hash"],
                    "file_name": row["file_name"],
                    "details": details,
                    "created_at": row["created_at"],
                })
            return events

    except sqlite3.Error as e:
        logger.exception(f"Error en get_audit_events: {e}")
        raise


def log_audit_event(
    action: str,
    path: str | None = None,
    file_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Registra un evento de auditoría desde flujos externos a database.py."""
    try:
        with _managed_connection() as conn:
            _log_event(conn, action, file_id=file_id, path=path, details=details)
    except sqlite3.Error as e:
        logger.warning(f"No se pudo registrar auditoría externa ({action}): {e}")


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
        with _managed_connection() as conn:
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

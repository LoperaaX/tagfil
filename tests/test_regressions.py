"""
Regresiones de la auditoría 01 (2026-10-19). Cada test fija un bug que se corrigió.
"""
import importlib
import os
import sqlite3
import sys
import time
import unittest
from pathlib import Path

from _base import DbTestCase


def _scalar(db, sql, *args):
    conn = sqlite3.connect(db.DB_PATH)
    try:
        return conn.execute(sql, args).fetchone()[0]
    finally:
        conn.close()


class FtsIndexTest(DbTestCase):
    """C1 — el índice FTS5 ya no se corrompe ni acumula tokens huérfanos."""

    def test_purge_after_upsert_does_not_crash(self):
        path = self._file()
        self.db.upsert_file(str(path), "Contrato", tags=["legal"])
        self.assertTrue(self.db.purge_file(str(path)))
        self.assertTrue(self.db.check_fts_integrity())

    def test_empty_trash_after_upsert_does_not_crash(self):
        path = self._file()
        self.db.upsert_file(str(path), "Contrato", tags=["legal"])
        self.db.delete_file(str(path))
        self.assertEqual(self.db.empty_trash(), 1)
        self.assertTrue(self.db.check_fts_integrity())

    def test_removed_tag_is_no_longer_searchable(self):
        path = self._file()
        self.db.upsert_file(str(path), "Factura", tags=["servicios"])
        self.db.upsert_file(str(path), "Factura", tags=["otro"])
        self.assertEqual(self.db.search("servicios"), [])
        self.assertEqual(len(self.db.search("otro")), 1)

    def test_trash_and_restore_keep_tags_indexed(self):
        path = self._file()
        self.db.upsert_file(str(path), "Factura", tags=["servicios"])
        self.db.delete_file(str(path))
        self.db.restore_from_trash(str(path))
        self.assertEqual(len(self.db.search("servicios")), 1)

    def test_index_can_be_rebuilt(self):
        self.db.upsert_file(str(self._file("a.pdf")), "Uno", tags=["x"])
        self.db.upsert_file(str(self._file("b.pdf")), "Dos", tags=["x"])
        self.assertEqual(self.db.rebuild_search_index(), 2)
        self.assertEqual(len(self.db.search("x")), 2)
        self.assertTrue(self.db.check_fts_integrity())

    def test_migration_from_v4_content_table(self):
        path = self._file()
        self.db.upsert_file(str(path), "Contrato", tags=["legal"])
        # Reconstruir el estado de la v4: FTS con content table + triggers
        conn = sqlite3.connect(self.db.DB_PATH)
        conn.executescript("""
            DROP TABLE files_fts;
            CREATE VIRTUAL TABLE files_fts USING fts5(
                name, description, tags, content=files, content_rowid=id,
                tokenize='unicode61 remove_diacritics 2');
            CREATE TRIGGER files_fts_insert AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, name, description, tags)
                VALUES (new.id, new.name, new.description, ''); END;
            PRAGMA user_version = 4;
        """)
        conn.close()

        self.db.init_db()

        self.assertEqual(_scalar(self.db, "PRAGMA user_version"), self.db.DB_SCHEMA_VERSION)
        self.assertEqual(_scalar(self.db, "SELECT count(*) FROM sqlite_master WHERE type='trigger'"), 0)
        self.assertEqual(len(self.db.search("legal")), 1)
        self.assertTrue(self.db.check_fts_integrity())
        pre = list(Path(self.db.APP_DIR).glob("tagfil_pre_migracion_v4.db"))
        self.assertEqual(len(pre), 1, "debe existir la copia previa a la migración")


class PartialUpsertTest(DbTestCase):
    """H1 / H5 — guardar parcialmente no borra lo que ya había."""

    def test_omitted_fields_are_kept(self):
        path = self._file()
        self.db.upsert_file(str(path), "Doc", tags=["x"], short_name="FAC-1",
                            document_type="factura", entity="ACME", sequence_number=7)
        self.db.upsert_file(str(path), "Doc editado")
        rec = self.db.get_file(str(path))
        self.assertEqual((rec["short_name"], rec["document_type"], rec["entity"], rec["sequence_number"]),
                         ("FAC-1", "factura", "ACME", 7))
        self.assertEqual(rec["tags"], ["x"])
        self.assertEqual(rec["description"], "Doc editado")

    def test_explicit_empty_values_clear_fields(self):
        path = self._file()
        self.db.upsert_file(str(path), "Doc", tags=["x"], short_name="FAC-1", sequence_number=7)
        self.db.upsert_file(str(path), "Doc", tags=[], short_name="", sequence_number=None)
        rec = self.db.get_file(str(path))
        self.assertEqual((rec["short_name"], rec["sequence_number"], rec["tags"]), ("", None, []))

    def test_registering_a_trashed_file_restores_it(self):
        path = self._file()
        self.db.upsert_file(str(path), "Doc", tags=["x"])
        self.db.delete_file(str(path))
        self.db.upsert_file(str(path), self.db.KEEP, sync_metadata=False)
        names = [r["name"] for r in self.db.list_all_files()]
        self.assertIn(path.name, names)
        self.assertEqual(self.db.get_file(str(path))["description"], "Doc")


class SearchTest(DbTestCase):
    """M1 / M7 — búsqueda por prefijo, acentos, literales y límite."""

    def setUp(self):
        super().setUp()
        self.db.upsert_file(str(self._file("factura_luz.pdf")), "Recibo servicios", tags=["servicios"])
        self.db.upsert_file(str(self._file("Éxito 100%.pdf")), "Reporte final")

    def names(self, query):
        return sorted(r["name"] for r in self.db.search(query))

    def test_prefix_match(self):
        self.assertEqual(self.names("fact"), ["factura_luz.pdf"])
        self.assertEqual(self.names("serv"), ["factura_luz.pdf"])

    def test_substring_falls_back_to_like(self):
        self.assertEqual(self.names("ctura"), ["factura_luz.pdf"])

    def test_accents_and_case(self):
        self.assertEqual(self.names("ÉXITO"), ["Éxito 100%.pdf"])
        self.assertEqual(self.names("éxito"), ["Éxito 100%.pdf"])

    def test_percent_and_underscore_are_literal(self):
        self.assertEqual(self.names("100%"), ["Éxito 100%.pdf"])
        self.assertEqual(self.names("%"), ["Éxito 100%.pdf"])
        self.assertEqual(self.names("_"), ["factura_luz.pdf"])

    def test_limit_is_applied_in_sql(self):
        self.assertEqual(len(self.db.search("a", limit=1)), 1)
        self.assertEqual(len(self.db.list_all_files(limit=1)), 1)

    def test_special_characters_do_not_break_fts(self):
        for q in ['"', "(", "a OR", "x:y", "***", "-", "^"]:
            self.db.search(q)   # no debe lanzar


class AuditRetentionTest(DbTestCase):
    """M8 — la retención de auditoría se aplica."""

    def test_prune_keeps_only_latest_events(self):
        for i in range(10):
            self.db.log_audit_event("test.event", details={"i": i})
        self.db.prune_audit_events(4)
        self.assertEqual(_scalar(self.db, "SELECT count(*) FROM audit_events"), 4)
        newest = _scalar(self.db, "SELECT max(id) FROM audit_events")
        self.assertEqual(_scalar(self.db, "SELECT min(id) FROM audit_events"), newest - 3)

    def test_zero_means_unlimited(self):
        for _ in range(5):
            self.db.log_audit_event("test.event")
        self.assertEqual(self.db.prune_audit_events(0), 0)


class BackupTest(DbTestCase):
    """H4 — backups con rotación, verificados y recuperación limpia."""

    def test_rotation_keeps_daily_generation(self):
        self.db.upsert_file(str(self._file()), "Doc")
        self.assertTrue(self.db.backup_db(force=True))
        old = time.time() - 2 * 86400
        os.utime(self.db.DB_BACKUP, (old, old))
        self.assertTrue(self.db.backup_db(force=True))
        self.assertTrue(self.db._backup_generation(1).exists())

    def test_frequent_backups_still_rotate_daily(self):
        self.db.backup_db(force=True)
        first = self.db._backup_generation(1)
        self.assertTrue(first.exists())
        first.write_bytes(b"generacion anterior")
        old = time.time() - 2 * 86400
        os.utime(first, (old, old))
        # El principal acaba de actualizarse: no debe impedir la rotacion.
        os.utime(self.db.DB_BACKUP, None)
        self.assertTrue(self.db.backup_db(force=True))
        self.assertEqual(self.db._backup_generation(2).read_bytes(), b"generacion anterior")
        self.assertTrue(self.db.backup_db(force=True))
        self.assertFalse(self.db._backup_generation(3).exists())

    def test_corrupt_db_does_not_overwrite_good_backup(self):
        self.db.upsert_file(str(self._file()), "Doc")
        self.db.backup_db(force=True)
        good = self.db.DB_BACKUP.read_bytes()
        self.db.DB_PATH.write_bytes(b"basura" * 2000)
        self.assertFalse(self.db.backup_db(force=True))
        self.assertEqual(self.db.DB_BACKUP.read_bytes(), good)

    def test_recovery_restores_and_removes_stale_wal(self):
        self.db.upsert_file(str(self._file()), "Doc")
        self.db.backup_db(force=True)
        self.db.DB_PATH.write_bytes(b"basura" * 2000)
        stale = Path(str(self.db.DB_PATH) + "-wal")
        stale.write_bytes(b"wal-viejo")
        self.assertTrue(self.db._attempt_recovery())
        self.assertFalse(stale.exists())
        self.assertTrue(self.db.check_integrity())
        self.assertEqual(len(self.db.list_all_files()), 1)

    def test_recovery_skips_unhealthy_generation(self):
        self.db.upsert_file(str(self._file()), "Doc")
        self.db.backup_db(force=True)
        shutil_copy = self.db._backup_generation(1)
        shutil_copy.write_bytes(self.db.DB_BACKUP.read_bytes())   # generación sana
        self.db.DB_BACKUP.write_bytes(b"x" * 5000)                # la más reciente, dañada
        self.db.DB_PATH.write_bytes(b"basura" * 2000)
        self.assertTrue(self.db._attempt_recovery())
        self.assertTrue(self.db.check_integrity())


class SanitizerTest(DbTestCase):
    """M4 / M5 — los sanitizers ya no destruyen texto legítimo."""

    def setUp(self):
        super().setUp()
        self.security = importlib.import_module("security")

    def test_tags_keep_word_boundaries(self):
        self.assertEqual(self.security.sanitize_tags(["Cuenta de cobro", "Factura 2026"]),
                         ["cuenta-de-cobro", "factura-2026"])

    def test_description_keeps_comparisons_but_strips_html(self):
        clean = self.security.sanitize_description
        self.assertEqual(clean("Valor < 100 y > 50"), "Valor < 100 y > 50")
        self.assertEqual(clean("amor <3"), "amor <3")
        self.assertEqual(clean("hola <b>mundo</b> <script>x</script>"), "hola mundo x")

    def test_double_dots_allowed_in_names_but_not_as_component(self):
        ok, _ = self.security.validate_path(str(self.appdata / "informe..final.pdf"))
        self.assertTrue(ok)
        ok, msg = self.security.validate_path(str(self.appdata / "a" / ".." / "b.pdf"))
        self.assertFalse(ok)
        self.assertIn("..", msg)


class SettingsTest(DbTestCase):
    """Settings tolerante a archivos dañados y con escritura atómica."""

    def setUp(self):
        super().setUp()
        self.settings = importlib.import_module("tagfil.settings")
        self.path = Path(self.db.APP_DIR) / "settings.json"

    def test_corrupt_file_falls_back_to_defaults(self):
        self.path.write_text("{no es json", encoding="utf-8")
        self.assertTrue(self.settings.get_settings().get("sync_explorer_metadata"))

    def test_non_dict_json_is_ignored(self):
        self.path.write_text("[1, 2, 3]", encoding="utf-8")
        self.assertEqual(self.settings.get_settings().get("audit_retention"), 5000)

    def test_set_preserves_changes_made_by_another_process(self):
        a = self.settings.Settings(self.path)
        a.set("encrypt_backup", True)
        stale = self.settings.Settings(self.path)
        self.path.write_text('{"encrypt_backup": true, "audit_retention": 100}', encoding="utf-8")
        stale.set("sync_explorer_metadata", False)
        reloaded = self.settings.Settings(self.path)
        self.assertEqual(reloaded.get("audit_retention"), 100)
        self.assertFalse(reloaded.get("sync_explorer_metadata"))
        self.assertFalse(list(self.path.parent.glob("*.tmp")))


class LauncherTest(DbTestCase):
    """H2 — el comando registrado funciona en desarrollo y empaquetado."""

    def setUp(self):
        super().setUp()
        self.launcher = importlib.import_module("launcher")

    def test_dev_command_runs_main_py(self):
        cmd = self.launcher.command('--file "%1"')
        self.assertIn("main.py", cmd)
        self.assertTrue(cmd.endswith('--file "%1"'))

    def test_frozen_command_is_just_the_exe(self):
        sys.frozen = True
        old_exe = sys.executable
        sys.executable = r"C:\Program Files\TagFil\TagFil.exe"
        try:
            self.assertEqual(self.launcher.command('--file "%1"'),
                             r'"C:\Program Files\TagFil\TagFil.exe" --file "%1"')
        finally:
            del sys.frozen
            sys.executable = old_exe


if __name__ == "__main__":
    unittest.main()

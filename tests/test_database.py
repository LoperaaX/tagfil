import importlib
import unittest

from _base import DbTestCase


class DatabaseTest(DbTestCase):
    def test_tag_lifecycle_updates_counts_and_search(self):
        path = self._file()

        self.db.upsert_file(
            path=str(path),
            description="Factura de servicios ACME",
            tags=["factura", "acme"],
        )
        self.db.create_tag("pendiente")

        counts = {row["name"]: row["count"] for row in self.db.get_tag_counts()}
        self.assertEqual(counts["factura"], 1)
        self.assertEqual(counts["acme"], 1)
        self.assertEqual(counts["pendiente"], 0)

        results = self.db.search("factura")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], path.name)

        self.assertTrue(self.db.delete_tag("factura"))
        counts = {row["name"]: row["count"] for row in self.db.get_tag_counts()}
        self.assertNotIn("factura", counts)
        self.assertEqual(counts["acme"], 1)

        events = self.db.get_audit_events()
        actions = [event["action"] for event in events]
        self.assertIn("file.upsert", actions)
        self.assertIn("tag.create", actions)
        self.assertIn("tag.delete", actions)
        self.assertTrue(all("description" not in event["details"] for event in events))

    def test_recent_and_untagged_helpers(self):
        tagged = self._file("tagged.pdf")
        untagged = self._file("untagged.pdf")

        self.db.upsert_file(str(tagged), "Con etiqueta", ["demo"])
        self.db.upsert_file(str(untagged), "Sin etiqueta", [])

        self.assertEqual(len(self.db.get_recent_files(1)), 1)

        untagged_names = {row["name"] for row in self.db.get_untagged_files()}
        self.assertIn("untagged.pdf", untagged_names)
        self.assertNotIn("tagged.pdf", untagged_names)

    def test_backup_hash_is_created_and_verified(self):
        self.db.backup_db(force=True)

        security = importlib.import_module("security")
        ok, msg = security.verify_backup_hash()

        self.assertTrue(ok, msg)


if __name__ == "__main__":
    unittest.main()

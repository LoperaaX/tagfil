import importlib
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path


class SecurityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.old_appdata = os.environ.get("APPDATA")
        os.environ["APPDATA"] = self._tmp.name

        for name in ["security", "config"]:
            sys.modules.pop(name, None)

        self.security = importlib.import_module("security")

    def tearDown(self):
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

        for name in ["security", "config"]:
            sys.modules.pop(name, None)

        if self.old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self.old_appdata

        self._tmp.cleanup()

    def test_validate_path_blocks_ads_and_device_paths(self):
        normal = Path(self._tmp.name) / "documento.pdf"
        ok, normalized = self.security.validate_path(str(normal))
        self.assertTrue(ok, normalized)

        ok, msg = self.security.validate_path(str(normal) + ":TagFil")
        self.assertFalse(ok)
        self.assertIn("Alternate Data Streams", msg)

        ok, msg = self.security.validate_path(r"\\?\C:\temp\documento.pdf")
        self.assertFalse(ok)
        self.assertIn("dispositivo", msg)

    def test_validate_path_blocks_control_chars(self):
        normal = Path(self._tmp.name) / "doc.pdf"
        ok, msg = self.security.validate_path(str(normal) + "\x01")
        self.assertFalse(ok)
        self.assertIn("control", msg)

    def test_security_audit_reports_findings(self):
        findings = self.security.run_security_audit()
        checks = {item["check"] for item in findings}

        self.assertIn("database", checks)
        self.assertIn("backup-hash", checks)
        self.assertIn("encrypted-backup", checks)

    def test_encrypted_backup_toggle(self):
        old_value = os.environ.get("TAGFIL_ENCRYPT_BACKUP")
        try:
            os.environ["TAGFIL_ENCRYPT_BACKUP"] = "1"
            self.assertTrue(self.security.encrypted_backups_enabled())
        finally:
            if old_value is None:
                os.environ.pop("TAGFIL_ENCRYPT_BACKUP", None)
            else:
                os.environ["TAGFIL_ENCRYPT_BACKUP"] = old_value


if __name__ == "__main__":
    unittest.main()

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
        self.old_home = os.environ.get("TAGFIL_HOME")
        os.environ["APPDATA"] = self._tmp.name
        os.environ["TAGFIL_HOME"] = str(Path(self._tmp.name) / "TagFilData")

        for name in ["security", "config", "tagfil.settings"]:
            sys.modules.pop(name, None)

        self.security = importlib.import_module("security")

    def tearDown(self):
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

        for name in ["security", "config", "tagfil.settings"]:
            sys.modules.pop(name, None)

        if self.old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self.old_appdata
        if self.old_home is None:
            os.environ.pop("TAGFIL_HOME", None)
        else:
            os.environ["TAGFIL_HOME"] = self.old_home

        self._tmp.cleanup()

    @unittest.skipUnless(sys.platform == "win32", "Rutas ADS y de dispositivo: solo Windows")
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
        # La preferencia vive en settings.json (ya no en una variable de entorno)
        self.assertFalse(self.security.encrypted_backups_enabled())
        settings = importlib.import_module("tagfil.settings")
        settings.get_settings().set("encrypt_backup", True)
        self.assertTrue(self.security.encrypted_backups_enabled())


if __name__ == "__main__":
    unittest.main()

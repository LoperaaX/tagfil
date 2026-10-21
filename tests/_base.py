"""Base común: cada test corre con una carpeta de datos temporal y módulos recién importados."""
import importlib
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

_MODULES = ["metadata", "security", "database", "config", "launcher", "tagfil.settings"]
_ENV = ("APPDATA", "TAGFIL_HOME")


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.appdata = Path(self._tmp.name)
        self._old_env = {k: os.environ.get(k) for k in _ENV}
        os.environ["APPDATA"] = str(self.appdata)
        os.environ["TAGFIL_HOME"] = str(self.appdata / "TagFilData")   # aísla en cualquier SO

        for name in _MODULES:
            sys.modules.pop(name, None)

        self.db = importlib.import_module("database")
        self.db.init_db()

    def tearDown(self):
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

        for name in _MODULES:
            sys.modules.pop(name, None)

        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        self._tmp.cleanup()

    def _file(self, name="factura.pdf"):
        path = self.appdata / name
        path.write_text("demo", encoding="utf-8")
        return path

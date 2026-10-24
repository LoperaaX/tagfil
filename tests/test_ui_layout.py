"""
Regresiones de la pestaña «Todos los archivos» (QSS/layout). Se ejecutan en un
subproceso con Qt sin pantalla para no mezclar módulos entre tests; se saltan si
PyQt6 no está instalado.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HAS_QT = importlib.util.find_spec("PyQt6") is not None

_SCRIPT = r"""
import json, sys, time
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/tagfil")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect
app = QApplication([])
import database as db; db.init_db()
import pathlib
docs = pathlib.Path(DOCS); docs.mkdir(exist_ok=True)
for n in ("a.pdf", "b.docx", "c.xlsx"):
    (docs / n).write_text("x"); db.upsert_file(str(docs / n), "d", tags=["t"], sync_metadata=False)
from tagfil.main_window import MainWindow
win = MainWindow(); win.show()
arch = [p for p in win._pages if p.__class__.__name__ == "ArchivosPage"][0]
win._stack.setCurrentIndex(win._pages.index(arch)); arch.refresh()
def pump(s):
    end = time.time() + s
    while time.time() < end: app.processEvents(); time.sleep(0.02)
pump(2)
def rect(w): return QRect(w.mapTo(arch, w.rect().topLeft()), w.size())
out = {"overlap": {}, "chips": {}}
for width in (960, 1150, 1600):
    win.resize(width, 720); pump(0.5)
    search = arch._search_input.parentWidget()
    bad = [n for n, w in (("importar", arch._btn_import), ("mas_usados", arch._btn_mas),
                          ("az", arch._btn_az), ("panel", arch._btn_toggle_panel))
           if rect(search).intersects(rect(w))]
    out["overlap"][width] = bad
    out["chips"][width] = {k: [b.width(), b.layout().sizeHint().width()] for k, b in arch._filter_widgets.items()}
out["search_frame_qss"] = arch._search_input.parentWidget().styleSheet()
out["stack_qss"] = win._stack.styleSheet()
out["wrap_qss"] = win._content_wrap.styleSheet()
print("JSON:" + json.dumps(out))
"""


@unittest.skipUnless(HAS_QT, "PyQt6 no está instalado")
class ArchivosLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.mkdtemp()
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "TAGFIL_HOME": tmp,
               "APPDATA": tmp}
        code = f"ROOT = {str(ROOT)!r}\nDOCS = {str(Path(tmp) / 'docs')!r}\n" + _SCRIPT
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                              env=env, timeout=120)
        line = next((l for l in proc.stdout.splitlines() if l.startswith("JSON:")), None)
        if line is None:
            raise AssertionError(f"No se pudo medir la UI:\n{proc.stdout}\n{proc.stderr}")
        cls.m = json.loads(line[5:])

    def test_search_never_overlaps_other_controls(self):
        for width, overlapped in self.m["overlap"].items():
            self.assertEqual(overlapped, [], f"con {width}px la búsqueda se solapa con {overlapped}")

    def test_filter_chips_are_not_clipped(self):
        for width, chips in self.m["chips"].items():
            self.assertTrue(chips, "no se crearon chips de filtro")
            for key, (actual, needed) in chips.items():
                self.assertGreaterEqual(actual, needed, f"chip {key} cortado a {width}px")

    def test_stylesheets_are_scoped(self):
        # Con selector: un «background: transparent» suelto se hereda a todos los hijos
        # y anula el fondo de los botones del tema (p. ej. «Importar carpeta»).
        self.assertIn("QFrame#search_frame", self.m["search_frame_qss"])
        self.assertTrue(self.m["stack_qss"].startswith("QStackedWidget#"))
        self.assertTrue(self.m["wrap_qss"].startswith("QWidget#"))


if __name__ == "__main__":
    unittest.main()

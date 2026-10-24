"""Integración de la página de etiquetas en un proceso y base de datos aislados."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = r'''
import sys, time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, ROOT)
sys.path.insert(0, str(Path(ROOT) / "tagfil"))
from PyQt6.QtCore import QEvent, QRect
from PyQt6.QtWidgets import QApplication
import database as db
from tagfil.main_window import MainWindow
from pages.etiquetas import TagCard, RankingModal, EmptyState

app = QApplication([])
db.init_db()
win = MainWindow()
page = win._pages[2]
win._stack.setCurrentIndex(2)
win.show()
def pump():
    for _ in range(15):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        time.sleep(0.01)
try:
    page.refresh()
    pump()
    assert isinstance(page._empty, EmptyState), "Falta el estado vacío"
    with patch("pages.etiquetas.QInputDialog.getText", return_value=("Nueva", True)):
        page._btn_new.click()
    assert any(t["name"] == "nueva" for t in db.get_tag_counts()), "No crea etiquetas"
    docs = Path(DATA) / "docs"
    docs.mkdir()
    for i in range(8):
        p = docs / f"archivo{i}.txt"
        p.write_text("ejemplo")
        tags = ["Trabajo", f"Etiqueta{i}"] if i < 7 else []
        db.upsert_file(str(p), "", tags=tags, sync_metadata=False)
    page.refresh()
    pump()
    assert len(page._cards) == len(db.get_tag_counts())
    assert page._stats_bar._s_coverage._val._full == "87.5%"
    assert page._stats_bar._s_untagged._val._full == "1"
    assert page._stats_bar._alert.isVisible()
    columns = []
    for width in (960, 1150, 1600, 960):
        win.resize(width, 720)
        pump()
        columns.append(page._cols)
        search = page._search_frame
        def rect(w):
            return QRect(w.mapTo(page, w.rect().topLeft()), w.size())
        for b in (page._btn_mas, page._btn_az, page._btn_ranking, page._btn_new):
            assert not rect(search).intersects(rect(b)), f"Controles solapados a {width}px"
        assert len(page._cards) == page._grid.count(), "Widgets duplicados"
        for card in page._cards:
            assert card.width() >= page._CARD_MIN_W, f"Tarjeta estrecha a {width}px"
            assert card.x() + card.width() <= page._scroll.viewport().width()
    assert columns[0] < columns[2], f"Cuadrícula no adaptable: {columns}"
    page._btn_az.click()
    assert page._btn_az.isChecked() and not page._btn_mas.isChecked()
    names = [c._name for c in page._cards]
    assert names == sorted(names, key=str.lower)
    page._on_stat_clicked("top")
    assert page._search_input.text() == "trabajo", "Más usada falla tras ordenar A-Z"
    assert len(page._cards) == 1
    page._search_input.setText("NoExiste")
    pump()
    assert isinstance(page._empty, EmptyState) and not page._cards
    page._clear_btn.click()
    page._btn_mas.click()
    pump()
    assert page._cards[0]._name == "trabajo"
    assert len(page._grid_container.findChildren(TagCard)) == len(page._cards)
    modal = RankingModal(page._tags_data, page)
    modal.show()
    pump()
    modal.close()
    print("ETIQUETAS_OK", columns)
finally:
    win.shutdown_workers()
    win.close()
    app.processEvents()
'''


@unittest.skipUnless(importlib.util.find_spec("PyQt6"), "PyQt6 no está instalado")
class EtiquetasUiTest(unittest.TestCase):
    def test_page_workflow_and_responsive_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "QT_QPA_PLATFORM": "offscreen",
                   "TAGFIL_HOME": tmp, "APPDATA": tmp}
            code = f"ROOT = {str(ROOT)!r}\nDATA = {tmp!r}\n" + SCRIPT
            proc = subprocess.run([sys.executable, "-c", code], env=env,
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("ETIQUETAS_OK", proc.stdout)

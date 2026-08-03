"""
search_worker.py — Worker de búsqueda en hilo separado.
"""
from PyQt6.QtCore import QThread, pyqtSignal

import database as db
from config import get_logger, SEARCH_MAX_RESULTS

logger = get_logger(__name__)


class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error         = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query      = query
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            if self._cancelled:
                return
            results = db.search(self.query, check_exists=True)[:SEARCH_MAX_RESULTS]
            if not self._cancelled:
                self.results_ready.emit(results)
        except Exception as e:
            logger.exception(f"Error en búsqueda: {e}")
            if not self._cancelled:
                self.error.emit(str(e))

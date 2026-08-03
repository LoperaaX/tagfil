"""
toggle_switch.py — Widget ToggleSwitch animado para TagFil.
"""
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget

from theme import C


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._pos     = 1.0 if checked else 0.0
        self.setFixedSize(46, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._timer = QTimer(self)
        self._timer.setInterval(10)
        self._timer.timeout.connect(self._tick)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        if val != self._checked:
            self._checked = val
            self._timer.start()

    def _tick(self):
        target = 1.0 if self._checked else 0.0
        diff   = target - self._pos
        if abs(diff) < 0.04:
            self._pos = target
            self._timer.stop()
        else:
            self._pos += diff * 0.22
        self.update()

    def mousePressEvent(self, _):
        self._checked = not self._checked
        self._timer.start()
        self.toggled.emit(self._checked)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r    = h / 2

        off_c = QColor(C.BG5)
        on_c  = QColor(C.PURPLE)
        t     = self._pos
        tc    = QColor(
            int(off_c.red()   + (on_c.red()   - off_c.red())   * t),
            int(off_c.green() + (on_c.green() - off_c.green()) * t),
            int(off_c.blue()  + (on_c.blue()  - off_c.blue())  * t),
        )
        p.setBrush(QBrush(tc))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, r, r)

        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, r - 1, r - 1)

        mg = 3
        tx = mg + (w - h) * self._pos
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 60)))
        p.drawEllipse(QRectF(tx + 0.5, mg + 1, h - 2 * mg, h - 2 * mg))
        p.setBrush(QBrush(QColor("white")))
        p.drawEllipse(QRectF(tx, mg, h - 2 * mg, h - 2 * mg))
        p.end()

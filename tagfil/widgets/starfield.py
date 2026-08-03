"""
widgets/starfield.py — Fondo animado para TagFil.

Modos:
  "space"  — campo de estrellas parpadeantes + cometas con cola
  "city"   — skyline nocturna con ventanas iluminadas + neblina morada
  "none"   — sin fondo (oscuro puro)

Uso:
    bg = StarfieldBackground(mode="space", parent=self)
    bg.setGeometry(self.rect())
    bg.lower()
"""

import math
import random
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient,
    QPainterPath,
)
from PyQt6.QtWidgets import QWidget


# ── Tipos de datos ────────────────────────────────────────────────────

@dataclass
class Star:
    x: float
    y: float
    r: float          # radio
    alpha: float      # opacidad actual 0-1
    alpha_dir: float  # velocidad de parpadeo
    twinkle_speed: float

@dataclass
class Comet:
    x: float
    y: float
    vx: float
    vy: float
    length: int       # longitud de la cola en píxeles
    alpha: float      # opacidad de la cabeza
    width: float      # grosor cabeza
    color: QColor
    active: bool = True

@dataclass
class Building:
    x: int
    y: int            # base (bottom)
    w: int
    h: int
    windows: list     # lista de (wx, wy, on, blink_timer) relativas al edificio

@dataclass
class Particle:
    x: float
    y: float
    r: float
    alpha: float
    drift: float      # velocidad horizontal suave


# ══════════════════════════════════════════════════════════════════════

class StarfieldBackground(QWidget):
    """Widget de fondo animado — se coloca detrás de todo el contenido."""

    MODES = ("space", "city", "none")

    def __init__(self, mode: str = "space", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        self._mode = mode if mode in self.MODES else "space"
        self._tick = 0

        # ── Space assets ──────────────────────────────────────────
        self._stars:   list[Star]   = []
        self._comets:  list[Comet]  = []
        self._nebulae: list[tuple]  = []   # (x, y, rx, ry, color)

        # ── City assets ───────────────────────────────────────────
        self._buildings: list[Building] = []
        self._city_particles: list[Particle] = []

        self._initialized = False

        # Timer ~50 fps
        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._tick_frame)
        self._timer.start()

    # ── API pública ───────────────────────────────────────────────────

    def set_mode(self, mode: str):
        if mode not in self.MODES:
            return
        self._mode = mode
        self._initialized = False
        self._stars.clear()
        self._comets.clear()
        self._buildings.clear()
        self._city_particles.clear()
        self.update()

    def get_mode(self) -> str:
        return self._mode

    # ── Inicialización de escena ──────────────────────────────────────

    def _init_space(self):
        W, H = self.width(), self.height()
        if W == 0 or H == 0:
            return

        # Estrellas — 3 capas de densidad
        self._stars = []
        for _ in range(220):   # pequeñas lejanas
            self._stars.append(Star(
                x=random.uniform(0, W), y=random.uniform(0, H),
                r=random.uniform(0.4, 1.0),
                alpha=random.uniform(0.2, 0.7),
                alpha_dir=random.choice([-1, 1]) * random.uniform(0.004, 0.012),
                twinkle_speed=random.uniform(0.003, 0.01),
            ))
        for _ in range(80):    # medianas
            self._stars.append(Star(
                x=random.uniform(0, W), y=random.uniform(0, H),
                r=random.uniform(1.0, 1.8),
                alpha=random.uniform(0.4, 0.9),
                alpha_dir=random.choice([-1, 1]) * random.uniform(0.006, 0.015),
                twinkle_speed=random.uniform(0.005, 0.012),
            ))
        for _ in range(20):    # grandes brillantes
            self._stars.append(Star(
                x=random.uniform(0, W), y=random.uniform(0, H),
                r=random.uniform(1.8, 2.8),
                alpha=random.uniform(0.6, 1.0),
                alpha_dir=random.choice([-1, 1]) * random.uniform(0.008, 0.018),
                twinkle_speed=random.uniform(0.007, 0.016),
            ))

        # Nebulosas (manchas de color suaves)
        self._nebulae = [
            (W * 0.15, H * 0.25, W * 0.35, H * 0.30, QColor(80, 30, 160, 18)),
            (W * 0.70, H * 0.15, W * 0.40, H * 0.35, QColor(40, 60, 180, 14)),
            (W * 0.50, H * 0.65, W * 0.45, H * 0.40, QColor(100, 20, 140, 12)),
            (W * 0.85, H * 0.55, W * 0.30, H * 0.28, QColor(60, 40, 200, 10)),
        ]

        self._initialized = True

    def _init_city(self):
        W, H = self.width(), self.height()
        if W == 0 or H == 0:
            return

        self._buildings = []
        horizon = int(H * 0.55)   # línea del horizonte
        x = 0
        while x < W + 60:
            bw = random.randint(28, 80)
            bh = random.randint(60, int(H * 0.48))
            by = horizon
            # Ventanas
            wins = []
            cols = max(1, (bw - 8) // 12)
            rows = max(1, (bh - 10) // 18)
            for wr in range(rows):
                for wc in range(cols):
                    wx = 6 + wc * 12
                    wy = bh - 10 - wr * 18
                    on = random.random() < 0.55
                    wins.append([wx, wy, on, random.randint(80, 400)])
            self._buildings.append(Building(x=x, y=by, w=bw, h=bh, windows=wins))
            x += bw + random.randint(0, 4)

        # Partículas flotantes (polvo luminoso)
        self._city_particles = []
        for _ in range(40):
            self._city_particles.append(Particle(
                x=random.uniform(0, W),
                y=random.uniform(H * 0.1, H * 0.6),
                r=random.uniform(0.8, 2.2),
                alpha=random.uniform(0.1, 0.5),
                drift=random.uniform(-0.3, 0.3),
            ))

        self._initialized = True

    # ── Tick de animación ─────────────────────────────────────────────

    def _tick_frame(self):
        if self._mode == "none":
            return

        W, H = self.width(), self.height()
        if W == 0 or H == 0:
            return

        if not self._initialized:
            if self._mode == "space":
                self._init_space()
            elif self._mode == "city":
                self._init_city()

        self._tick += 1

        if self._mode == "space":
            self._tick_space(W, H)
        elif self._mode == "city":
            self._tick_city(W, H)

        self.update()

    def _tick_space(self, W, H):
        # Parpadeo de estrellas
        for s in self._stars:
            s.alpha += s.alpha_dir
            if s.alpha >= 1.0:
                s.alpha = 1.0
                s.alpha_dir = -abs(s.alpha_dir)
            elif s.alpha <= 0.1:
                s.alpha = 0.1
                s.alpha_dir = abs(s.alpha_dir)

        # Cometas
        for c in self._comets:
            c.x += c.vx
            c.y += c.vy
            c.alpha -= 0.006
            if c.x > W + 200 or c.y > H + 200 or c.alpha <= 0:
                c.active = False
        self._comets = [c for c in self._comets if c.active]

        # Generar nuevo cometa cada ~3s con prob
        if self._tick % 150 == 0 and random.random() < 0.7:
            self._spawn_comet(W, H)

    def _spawn_comet(self, W, H):
        angle = random.uniform(20, 50)   # grados desde horizontal
        rad   = math.radians(angle)
        speed = random.uniform(5, 11)
        vx    = math.cos(rad) * speed
        vy    = math.sin(rad) * speed
        # Empieza fuera del canvas arriba-izquierda
        sx = random.uniform(-100, W * 0.6)
        sy = random.uniform(-80,  H * 0.3)
        length = random.randint(80, 180)
        colors = [
            QColor(200, 180, 255),
            QColor(180, 200, 255),
            QColor(220, 200, 255),
            QColor(160, 220, 255),
        ]
        self._comets.append(Comet(
            x=sx, y=sy, vx=vx, vy=vy,
            length=length,
            alpha=random.uniform(0.7, 1.0),
            width=random.uniform(1.5, 3.0),
            color=random.choice(colors),
        ))

    def _tick_city(self, W, H):
        # Parpadeo de ventanas
        if self._tick % 3 == 0:
            for b in self._buildings:
                for win in b.windows:
                    win[3] -= 3
                    if win[3] <= 0:
                        win[2] = not win[2]
                        win[3] = random.randint(60, 500)

        # Partículas flotantes
        for p in self._city_particles:
            p.x += p.drift
            p.alpha += random.uniform(-0.008, 0.008)
            p.alpha = max(0.05, min(0.6, p.alpha))
            if p.x < -10:  p.x = W + 10
            if p.x > W+10: p.x = -10

    # ── Pintado ───────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()

        if self._mode == "space":
            self._paint_space(p, W, H)
        elif self._mode == "city":
            self._paint_city(p, W, H)
        else:
            # none — fondo oscuro puro
            p.fillRect(0, 0, W, H, QColor("#0D0C15"))

        p.end()

    def _paint_space(self, p: QPainter, W: int, H: int):
        # ── Fondo base degradado ─────────────────────────────────
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, QColor("#060412"))
        bg.setColorAt(0.4, QColor("#0a0720"))
        bg.setColorAt(1.0, QColor("#0d0a28"))
        p.fillRect(0, 0, W, H, QBrush(bg))

        # ── Nebulosas ────────────────────────────────────────────
        for nx, ny, rx, ry, col in self._nebulae:
            rg = QRadialGradient(nx, ny, max(rx, ry))
            c2 = QColor(col)
            c2.setAlpha(0)
            rg.setColorAt(0.0, col)
            rg.setColorAt(1.0, c2)
            p.save()
            p.translate(nx, ny)
            p.scale(1.0, ry / max(rx, 1))
            p.translate(-nx, -ny)
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(nx - rx, ny - max(rx, ry), rx * 2, max(rx, ry) * 2))
            p.restore()

        # ── Estrellas ────────────────────────────────────────────
        for s in self._stars:
            c = QColor(255, 255, 255)
            c.setAlphaF(s.alpha)
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(s.x, s.y), s.r, s.r)

            # Halo suave en estrellas grandes
            if s.r > 1.5:
                halo = QRadialGradient(s.x, s.y, s.r * 4)
                hc = QColor(200, 180, 255)
                hc.setAlphaF(s.alpha * 0.15)
                hc2 = QColor(200, 180, 255)
                hc2.setAlpha(0)
                halo.setColorAt(0.0, hc)
                halo.setColorAt(1.0, hc2)
                p.setBrush(QBrush(halo))
                p.drawEllipse(QPointF(s.x, s.y), s.r * 4, s.r * 4)

        # ── Cometas ──────────────────────────────────────────────
        for c_obj in self._comets:
            # Cola como path degradado
            tail_x = c_obj.x - c_obj.vx / max(abs(c_obj.vx), 0.01) * c_obj.length
            tail_y = c_obj.y - c_obj.vy / max(abs(c_obj.vy), 0.01) * c_obj.length

            grad = QLinearGradient(c_obj.x, c_obj.y, tail_x, tail_y)
            head_c = QColor(c_obj.color)
            head_c.setAlphaF(c_obj.alpha)
            tail_c = QColor(c_obj.color)
            tail_c.setAlpha(0)
            grad.setColorAt(0.0, head_c)
            grad.setColorAt(1.0, tail_c)

            pen = QPen(QBrush(grad), c_obj.width,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(c_obj.x, c_obj.y), QPointF(tail_x, tail_y))

            # Punto cabeza brillante
            hc = QColor(255, 255, 255)
            hc.setAlphaF(c_obj.alpha)
            p.setBrush(QBrush(hc))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(c_obj.x, c_obj.y), c_obj.width, c_obj.width)

        # ── Glass overlay morado ─────────────────────────────────
        p.setBrush(QBrush(QColor(18, 10, 40, 140)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, W, H)

        # Tinte morado radial sutil desde el centro
        rg = QRadialGradient(W * 0.5, H * 0.4, max(W, H) * 0.7)
        rg.setColorAt(0.0, QColor(100, 40, 200, 22))
        rg.setColorAt(1.0, QColor(40, 10, 80, 0))
        p.setBrush(QBrush(rg))
        p.drawRect(0, 0, W, H)

    def _paint_city(self, p: QPainter, W: int, H: int):
        # ── Cielo nocturno ───────────────────────────────────────
        sky = QLinearGradient(0, 0, 0, H)
        sky.setColorAt(0.0, QColor("#04020e"))
        sky.setColorAt(0.5, QColor("#080520"))
        sky.setColorAt(1.0, QColor("#120830"))
        p.fillRect(0, 0, W, H, QBrush(sky))

        # Neblina de horizonte morada
        fog = QRadialGradient(W * 0.5, H * 0.58, W * 0.65)
        fog.setColorAt(0.0, QColor(120, 50, 220, 35))
        fog.setColorAt(0.6, QColor(80, 20, 160, 15))
        fog.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(fog))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, W, H)

        # Neblina azul por encima
        fog2 = QRadialGradient(W * 0.2, H * 0.4, W * 0.4)
        fog2.setColorAt(0.0, QColor(40, 60, 180, 20))
        fog2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(fog2))
        p.drawRect(0, 0, W, H)

        # Estrellas escasas (ciudad = menos visibles)
        for s in self._stars[:60] if self._stars else []:
            c = QColor(255, 255, 255)
            c.setAlphaF(s.alpha * 0.4)
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(s.x, s.y * 0.5), s.r * 0.7, s.r * 0.7)

        # ── Edificios ────────────────────────────────────────────
        for b in self._buildings:
            top = b.y - b.h
            # Silueta del edificio
            bldg_grad = QLinearGradient(b.x, top, b.x + b.w, top)
            bldg_grad.setColorAt(0.0, QColor(20, 14, 38))
            bldg_grad.setColorAt(1.0, QColor(14, 10, 28))
            p.setBrush(QBrush(bldg_grad))
            p.setPen(QPen(QColor(60, 40, 100, 60), 0.5))
            p.drawRect(b.x, top, b.w, b.h)

            # Ventanas
            for win in b.windows:
                wx, wy, on, _ = win
                abs_x = b.x + wx
                abs_y = top + (b.h - wy)
                ww, wh = 6, 8
                if on:
                    # Ventana encendida con glow
                    warm = random.choice([
                        QColor(255, 220, 120, 180),
                        QColor(200, 220, 255, 160),
                        QColor(255, 240, 160, 170),
                    ])
                    p.setBrush(QBrush(warm))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawRect(abs_x, abs_y, ww, wh)
                    # Glow suave
                    glow = QRadialGradient(abs_x + ww/2, abs_y + wh/2, 12)
                    glow.setColorAt(0.0, QColor(warm.red(), warm.green(), warm.blue(), 30))
                    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                    p.setBrush(QBrush(glow))
                    p.drawEllipse(QPointF(abs_x + ww/2, abs_y + wh/2), 12, 12)
                else:
                    p.setBrush(QBrush(QColor(10, 8, 20, 200)))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawRect(abs_x, abs_y, ww, wh)

        # ── Partículas flotantes ─────────────────────────────────
        for pt in self._city_particles:
            pc = QColor(180, 140, 255)
            pc.setAlphaF(pt.alpha)
            p.setBrush(QBrush(pc))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(pt.x, pt.y), pt.r, pt.r)

        # ── Reflejo en el suelo ──────────────────────────────────
        horizon = H * 0.55
        ref = QLinearGradient(0, horizon, 0, H)
        ref.setColorAt(0.0, QColor(80, 30, 160, 25))
        ref.setColorAt(1.0, QColor(40, 10, 80, 60))
        p.setBrush(QBrush(ref))
        p.drawRect(0, int(horizon), W, H - int(horizon))

        # ── Glass overlay morado ─────────────────────────────────
        p.setBrush(QBrush(QColor(12, 6, 28, 150)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, W, H)

        rg = QRadialGradient(W * 0.5, H * 0.6, max(W, H) * 0.6)
        rg.setColorAt(0.0, QColor(100, 40, 200, 18))
        rg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(rg))
        p.drawRect(0, 0, W, H)

    # ── Resize ───────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._initialized = False   # reinicializar con nuevo tamaño

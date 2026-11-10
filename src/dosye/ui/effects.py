"""Neon effects and animations, designed to stay cheap:

* ONE shared AnimationClock (~20 fps) drives every continuous animation (twinkling
  stars, breathing glows). It stops completely when animations are disabled, when
  the window is minimized/hidden or the app is in the background.
* Hover glows are created on demand and removed when the hover fades out, so idle
  widgets carry no QGraphicsEffect at all.
* "Reduce effects" turns glows off too (static, flat UI).
"""
import math
import random

from PySide6.QtCore import QObject, QTimer, Signal, QVariantAnimation, QEasingCurve, QEvent, QPointF, QRectF, Qt, QAbstractAnimation
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QRadialGradient, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect


class FX:
    """Global effect switches (set from Settings)."""
    animations = True
    glow = True
    intensity = 0.7


class AnimationClock(QObject):
    tick = Signal(float)                 # seconds since start

    def __init__(self, fps=10):
        super().__init__()
        self._t = QTimer(self); self._t.setInterval(int(1000 / fps)); self._t.setTimerType(Qt.CoarseTimer)
        self._t.timeout.connect(self._on)
        self._elapsed = 0.0; self._dt = 1.0 / fps
        self._want = True; self._visible = True; self._active = True

    def _on(self):
        self._elapsed += self._dt
        self.tick.emit(self._elapsed)

    @property
    def time(self):
        return self._elapsed

    def _update(self):
        run = self._want and self._visible and self._active and FX.animations
        if run and not self._t.isActive():
            self._t.start()
        elif not run and self._t.isActive():
            self._t.stop()

    def set_enabled(self, on):
        self._want = on; self._update()

    def set_visible(self, on):
        self._visible = on; self._update()

    def set_app_active(self, on):
        self._active = on; self._update()

    def is_running(self):
        return self._t.isActive()


CLOCK = None


def clock():
    global CLOCK
    if CLOCK is None:
        CLOCK = AnimationClock()
    return CLOCK


class HoverGlow(QObject):
    """Neon glow that fades in on hover/focus (and stays while a checkable is checked)."""

    def __init__(self, widget, color="#8B5CFF", radius=22, sticky_checked=True, always=False, pulse=False):
        super().__init__(widget)
        self.w = widget; self.color = QColor(color); self.radius = radius
        self.sticky = sticky_checked; self.always = always; self.pulse = pulse
        self.level = 0.0; self.eff = None
        self.anim = QVariantAnimation(self); self.anim.setDuration(180); self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._set_level); self.anim.finished.connect(self._done)
        widget.installEventFilter(self)
        if hasattr(widget, "toggled"):
            widget.toggled.connect(lambda _c: self._target())
        if pulse:
            clock().tick.connect(self._pulse)
        self.refresh()

    def refresh(self):
        self._target(immediate=True)

    def _want(self):
        if not FX.glow:
            return 0.0
        if self.always:
            return 1.0
        hov = self.w.underMouse() or self.w.hasFocus()
        chk = self.sticky and getattr(self.w, "isCheckable", lambda: False)() and self.w.isChecked()
        return 1.0 if (hov or chk) else 0.0

    def _target(self, immediate=False):
        tgt = self._want()
        if immediate or not FX.animations:
            self.anim.stop(); self._set_level(tgt); self._done(); return
        if abs(tgt - self.level) < 1e-3:
            return
        self.anim.stop(); self.anim.setStartValue(self.level); self.anim.setEndValue(tgt); self.anim.start()

    def _ensure(self):
        if self.eff is None:
            self.eff = QGraphicsDropShadowEffect(self.w); self.eff.setOffset(0, 0)
            self.w.setGraphicsEffect(self.eff)
        return self.eff

    def _set_level(self, v, extra=0.0):
        self.level = float(v)
        if self.level <= 0.001:
            return
        e = self._ensure()
        k = FX.intensity
        e.setBlurRadius(self.radius * (0.55 + 0.6 * k) * (0.6 + 0.4 * self.level) + extra)
        c = QColor(self.color); c.setAlphaF(min(1.0, (0.35 + 0.55 * k) * self.level)); e.setColor(c)

    def _pulse(self, t):
        # Re-blurring a drop shadow is the costliest thing we animate: do it at ~5 fps only.
        self._n = getattr(self, "_n", 0) + 1
        if self._n % 3 == 0 and self.level > 0.5 and self.eff is not None and FX.animations and self.w.isVisible():
            self._set_level(self.level, extra=5 * (0.5 + 0.5 * math.sin(t * 1.6)))

    def _done(self):
        if self.level <= 0.001 and self.eff is not None:
            self.w.setGraphicsEffect(None); self.eff = None

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Enter, QEvent.Leave, QEvent.FocusIn, QEvent.FocusOut):
            QTimer.singleShot(0, self._target)
        return False


def fade_in(widget, ms=220):
    """Opacity 0 -> 1 (effect removed afterwards)."""
    if not FX.animations:
        return
    prev = getattr(widget, "_dosye_fade", None)
    if prev is not None:
        try:
            prev.stop()
        except RuntimeError:
            pass
    eff = QGraphicsOpacityEffect(widget); eff.setOpacity(0.0); widget.setGraphicsEffect(eff)
    a = QVariantAnimation(widget); a.setDuration(ms); a.setStartValue(0.0); a.setEndValue(1.0)
    a.setEasingCurve(QEasingCurve.OutCubic)

    def step(v):
        try:
            eff.setOpacity(float(v))
        except RuntimeError:
            pass

    def done():
        try:
            if widget.graphicsEffect() is eff:
                widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
    a.valueChanged.connect(step); a.finished.connect(done)
    widget._dosye_fade = a
    a.start(QAbstractAnimation.DeleteWhenStopped)


class StarField:
    """Deterministic set of stars, painted static or twinkling.

    Big stars are pre-rendered sprites (glow + four-point sparkle), so a twinkle frame
    is just a few small drawPixmap calls; dirty_rects() lets widgets repaint only the
    stars instead of the whole area.
    """

    def __init__(self, n=70, seed=11, gold_ratio=0.12):
        r = random.Random(seed)
        self.stars = []
        for _ in range(n):
            self.stars.append((r.random(), r.random(), r.uniform(0.6, 1.9), r.uniform(0, math.tau),
                               r.uniform(0.6, 1.8), r.random() < gold_ratio))
        self._sprites = {}

    def _sprite(self, size, gold, dpr):
        key = (round(size, 1), gold, dpr)
        pm = self._sprites.get(key)
        if pm is None:
            from PySide6.QtGui import QPixmap
            ext = size * 3.4
            px = int(math.ceil(ext * 2 * dpr)) + 2
            pm = QPixmap(px, px); pm.fill(Qt.transparent); pm.setDevicePixelRatio(dpr)
            p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
            c = QColor(255, 222, 140) if gold else QColor(225, 230, 255)
            cx = cy = px / dpr / 2
            g = QRadialGradient(QPointF(cx, cy), size * 3.2)
            g.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 110)); g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(g); p.drawEllipse(QPointF(cx, cy), size * 3.2, size * 3.2)
            p.setBrush(c); s = size * 2.6
            path = QPainterPath(); path.moveTo(cx, cy - s); path.quadTo(cx, cy, cx + s, cy)
            path.quadTo(cx, cy, cx, cy + s); path.quadTo(cx, cy, cx - s, cy); path.quadTo(cx, cy, cx, cy - s)
            p.drawPath(path); p.end()
            self._sprites[key] = pm
        return pm

    def _pos(self, rect, x, y):
        return rect.left() + x * rect.width(), rect.top() + y * rect.height()

    def paint(self, p, rect, t=None, alpha=1.0, only_twinkling=False):
        p.save(); p.setPen(Qt.NoPen)
        dpr = p.device().devicePixelRatioF() if p.device() else 1.0
        for x, y, size, ph, sp, gold in self.stars:
            if only_twinkling and size <= 1.0:
                continue
            tw = 0.65 + 0.35 * math.sin(ph + (t or 0) * sp) if t is not None else 0.8
            cx, cy = self._pos(rect, x, y)
            if size > 1.5:
                pm = self._sprite(size, gold, dpr)
                w = pm.width() / dpr
                p.setOpacity(alpha * tw)
                p.drawPixmap(QPointF(cx - w / 2, cy - w / 2), pm)
            else:
                a = int(255 * alpha * tw * (0.55 if size < 1.0 else 0.9))
                p.setOpacity(1.0)
                p.setBrush(QColor(255, 222, 140, a) if gold else QColor(225, 230, 255, a))
                p.drawEllipse(QPointF(cx, cy), size * 0.6, size * 0.6)
        p.restore()

    def dirty_rects(self, rect, avoid=()):
        """Areas that change when the stars twinkle (small stars and stars hidden behind
        the rectangles in `avoid` — e.g. child buttons — are left static)."""
        from PySide6.QtCore import QRect
        out = []
        for x, y, size, ph, sp, gold in self.stars:
            if size <= 1.0:
                continue
            cx, cy = self._pos(rect, x, y); e = int(size * 3.6) + 2
            r = QRect(int(cx) - e, int(cy) - e, 2 * e, 2 * e)
            if any(r.intersects(a) for a in avoid):
                continue
            out.append(r)
        return out


def night_gradient(rect, shift=0.0):
    """The night-sky gradient of the Dosye folder (indigo -> violet), optionally drifting."""
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    s = 0.08 * math.sin(shift)
    g.setColorAt(0.0, QColor("#141A6E"))
    g.setColorAt(max(0.05, min(0.95, 0.45 + s)), QColor("#2A2398"))
    g.setColorAt(1.0, QColor("#4A2AA8"))
    return g


def paint_glow_rect(p, rect, radius, color, strength=1.0, layers=4, spread=7.0):
    """Soft neon halo around a rounded rect (cheap: a few translucent strokes)."""
    p.save(); p.setBrush(Qt.NoBrush)
    for i in range(layers, 0, -1):
        c = QColor(color); c.setAlphaF(max(0.0, min(1.0, strength * 0.16 * (layers - i + 1) / layers)))
        w = spread * i / layers
        p.setPen(QPen(c, w)); p.drawRoundedRect(rect.adjusted(-w / 2, -w / 2, w / 2, w / 2), radius + w / 2, radius + w / 2)
    p.restore()

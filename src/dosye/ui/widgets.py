"""Reusable widgets: labels, sliders, colour buttons, shape tiles, preview, header, toast."""
import math
import os

from PySide6.QtCore import (Qt, QSize, QRectF, QPointF, Signal, QTimer, QVariantAnimation, QEasingCurve,
                            QUrl, QAbstractAnimation)
from PySide6.QtGui import (QPixmap, QPainter, QColor, QFont, QPen, QLinearGradient, QRadialGradient,
                           QPainterPath, QFontMetricsF, QDesktopServices, QIcon)
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider, QComboBox,
                               QScrollArea, QFrame, QColorDialog, QSizePolicy, QAbstractButton,
                               QGraphicsOpacityEffect)

from ..core import render as fc
from ..i18n import tr
from . import theme
from .effects import FX, clock, StarField, night_gradient, paint_glow_rect


class ElidedLabel(QLabel):
    """Label that elides long text with "…" and never forces its panel to grow."""

    def __init__(self, text="", mode=Qt.ElideMiddle):
        super().__init__()
        self._full = ""; self._mode = mode
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(10)
        self.setText(text)

    def setText(self, t):
        self._full = t or ""; self.setToolTip(self._full); self._apply()

    def fullText(self):
        return self._full

    def _apply(self):
        super().setText(self.fontMetrics().elidedText(self._full, self._mode, max(10, self.width() - 2)))

    def resizeEvent(self, e):
        super().resizeEvent(e); self._apply()

    def minimumSizeHint(self):
        return QSize(10, super().minimumSizeHint().height())

    def sizeHint(self):
        return QSize(40, super().sizeHint().height())


class Thumb(QLabel):
    """Fixed-size thumbnail (the image is always scaled down to fit)."""

    def __init__(self, w=56, h=40):
        super().__init__()
        self.setFixedSize(w, h); self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"background: #0B0E30; border: 1px solid {theme.LINE2}; border-radius: 8px;")

    def set_image(self, img):
        if img is None or img.isNull():
            self.clear(); return
        dpr = self.devicePixelRatioF()
        w, h = int((self.width() - 6) * dpr), int((self.height() - 6) * dpr)
        small = fc.mip(img, w * 2)
        pm = QPixmap.fromImage(small.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)); pm.setDevicePixelRatio(dpr)
        self.setPixmap(pm)


class VScroll(QScrollArea):
    """Vertical-only scroll area: the content is always exactly as wide as the viewport."""

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True); self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)

    def resizeEvent(self, e):
        super().resizeEvent(e); self._fit()

    def _fit(self):
        w = self.widget()
        if w is not None:
            w.setMinimumWidth(0); w.setMaximumWidth(self.viewport().width())

    def setWidget(self, w):
        super().setWidget(w); self._fit()


def combo(items):
    c = QComboBox()
    c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon); c.setMinimumContentsLength(8)
    c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    for key, name in items:
        c.addItem(name, key)
    return c


def set_combo_data(c, value):
    c.blockSignals(True); c.setCurrentIndex(max(0, c.findData(value))); c.blockSignals(False)


class SliderRow(QWidget):
    changed = Signal(int)

    def __init__(self, label, lo, hi, val, suffix="", tip=""):
        super().__init__()
        self.suffix = suffix
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 2, 0, 2); lay.setSpacing(3)
        top = QHBoxLayout(); top.setSpacing(4)
        self.lbl = ElidedLabel(label, Qt.ElideRight); self.lbl.setObjectName("rowLabel"); self.lbl.setToolTip(tip or label)
        self.val = QLabel(); self.val.setObjectName("valueLabel")
        top.addWidget(self.lbl, 1); top.addWidget(self.val)
        self.s = QSlider(Qt.Horizontal); self.s.setRange(lo, hi); self.s.setValue(val)
        self.s.setCursor(Qt.PointingHandCursor)
        lay.addLayout(top); lay.addWidget(self.s)
        self.s.valueChanged.connect(self._on)
        self._upd(val)
        if tip:
            self.setToolTip(tip)

    def _upd(self, v):
        self.val.setText(f"{v}{self.suffix}")

    def _on(self, v):
        self._upd(v); self.changed.emit(v)

    def set(self, v):
        self.s.blockSignals(True); self.s.setValue(int(v)); self.s.blockSignals(False); self._upd(int(v))

    def setEnabled(self, e):
        super().setEnabled(e); self.lbl.setEnabled(e)


class ColorButton(QPushButton):
    changed = Signal(str)

    def __init__(self, color, title=""):
        super().__init__()
        self.title = title
        self.setCursor(Qt.PointingHandCursor); self.setMinimumHeight(34)
        self.set(color)
        self.clicked.connect(self.pick)

    def set(self, c):
        self.color = c
        q = QColor(c)
        auto = q.alpha() == 0
        txt = tr("color.auto") if auto else q.name().upper()
        fg = "#ECEBFF" if auto or q.lightnessF() < 0.62 else "#120F2A"
        bg = theme.BG3 if auto else q.name()
        self.setText(txt)
        self.setStyleSheet(f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid rgba(255,255,255,0.16); border-radius: 10px; font-weight: 600; }}"
                           f"QPushButton:hover {{ border: 1px solid {theme.GOLD_LIGHT}; }}")

    def setEnabled(self, e):
        super().setEnabled(e)
        if e:
            self.setGraphicsEffect(None)
        else:
            eff = QGraphicsOpacityEffect(self); eff.setOpacity(0.3); self.setGraphicsEffect(eff)

    def pick(self):
        start = QColor(self.color)
        if start.alpha() == 0:
            start = QColor("#333333")
        c = QColorDialog.getColor(start, self.window(), self.title or tr("color.pick"))
        if c.isValid():
            self.set(c.name()); self.changed.emit(c.name())


class Section(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("sectionCard")
        self.lay = QVBoxLayout(self); self.lay.setContentsMargins(14, 12, 14, 14); self.lay.setSpacing(8)
        h = QHBoxLayout(); h.setSpacing(8)
        bar = QFrame(); bar.setFixedSize(4, 16)
        bar.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme.GOLD}, stop:1 {theme.VIOLET}); border-radius: 2px;")
        t = ElidedLabel(title, Qt.ElideRight); t.setObjectName("sectionTitle")
        h.addWidget(bar); h.addWidget(t, 1)
        self.lay.addLayout(h)

    def add(self, w):
        self.lay.addWidget(w); return w

    def addLayout(self, l):
        self.lay.addLayout(l); return l


def row(label, widget):
    h = QHBoxLayout(); h.setSpacing(10)
    l = ElidedLabel(label, Qt.ElideRight); l.setObjectName("rowLabel")
    h.addWidget(l, 1); h.addWidget(widget, 1)
    return h


def two_line_elide(fm, text, width):
    """Wraps text on at most two lines, eliding the second one."""
    words = text.split()
    if not words:
        return [""]
    if fm.horizontalAdvance(text) <= width:
        return [text]
    line1 = ""
    i = 0
    while i < len(words):
        cand = (line1 + " " + words[i]).strip()
        if fm.horizontalAdvance(cand) > width and line1:
            break
        line1 = cand; i += 1
    if fm.horizontalAdvance(line1) > width:          # one very long word
        return [fm.elidedText(text, Qt.ElideRight, width)]
    rest = " ".join(words[i:])
    return [line1] + ([fm.elidedText(rest, Qt.ElideRight, width)] if rest else [])


class ShapeTile(QAbstractButton):
    """A shape in the Shapes grid: live thumbnail + name, neon border when selected."""
    W, H = 102, 112

    def __init__(self, sid, name, tip=""):
        super().__init__()
        self.sid = sid; self.name = name
        self.setCheckable(True); self.setFixedSize(self.W, self.H); self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tip or name); self.setFocusPolicy(Qt.TabFocus)
        self.pm = None; self.hover = 0.0; self.pop = 1.0
        self._ha = QVariantAnimation(self); self._ha.setDuration(160); self._ha.valueChanged.connect(self._set_hover)
        self._pa = QVariantAnimation(self); self._pa.setDuration(320); self._pa.setEasingCurve(QEasingCurve.OutBack)
        self._pa.valueChanged.connect(self._set_pop)
        self.toggled.connect(self._on_toggle)
        clock().tick.connect(self._tick)

    def set_pixmap(self, pm):
        self.pm = pm; self.update()

    def _set_hover(self, v):
        self.hover = float(v); self.update()

    def _set_pop(self, v):
        self.pop = float(v); self.update()

    def _tick(self, _t):
        if self.isChecked() and FX.glow and self.isVisible():
            self.update()

    def _on_toggle(self, on):
        if on and FX.animations and self.isVisible():
            self._pa.stop(); self._pa.setStartValue(0.86); self._pa.setEndValue(1.0); self._pa.start()
        self.update()

    def _anim_hover(self, tgt):
        if not FX.animations:
            self._set_hover(tgt); return
        self._ha.stop(); self._ha.setStartValue(self.hover); self._ha.setEndValue(tgt); self._ha.start()

    def enterEvent(self, e):
        self._anim_hover(1.0); super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim_hover(0.0); super().leaveEvent(e)

    def sizeHint(self):
        return QSize(self.W, self.H)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        chk = self.isChecked(); h = self.hover
        if chk:
            g = QLinearGradient(r.topLeft(), r.bottomRight()); g.setColorAt(0, QColor("#2B2794")); g.setColorAt(1, QColor("#3F2A9E"))
            p.setBrush(g)
        else:
            c0, c1 = QColor("#12164A"), QColor("#1D2268")
            p.setBrush(QColor(int(c0.red() + (c1.red() - c0.red()) * h), int(c0.green() + (c1.green() - c0.green()) * h),
                              int(c0.blue() + (c1.blue() - c0.blue()) * h)))
        if chk and FX.glow:
            pulse = 0.75 + 0.25 * math.sin(clock().time * 2.4) if FX.animations else 0.9
            paint_glow_rect(p, r, 12, QColor(theme.VIOLET), strength=(0.6 + 0.5 * FX.intensity) * pulse, spread=7)
        elif h > 0.01 and FX.glow:
            paint_glow_rect(p, r, 12, QColor(theme.INDIGO), strength=0.6 * h * (0.5 + FX.intensity), spread=5)
        if chk:
            pg = QLinearGradient(r.topLeft(), r.bottomRight()); pg.setColorAt(0, QColor("#A98BFF")); pg.setColorAt(1, QColor(theme.GOLD))
            p.setPen(QPen(pg, 1.6))
        else:
            p.setPen(QPen(QColor(theme.LINE2 if h > 0.5 else theme.LINE), 1))
        p.drawRoundedRect(r, 12, 12)
        if self.pm is not None:
            side = 70 * self.pop
            ir = QRectF((self.width() - side) / 2, 8 + (70 - side) / 2, side, side)
            p.drawPixmap(ir, self.pm, QRectF(0, 0, self.pm.width(), self.pm.height()))
        f = QFont(self.font()); f.setPointSizeF(8.2); f.setBold(chk); p.setFont(f)
        fm = QFontMetricsF(f)
        lines = two_line_elide(fm, self.name, r.width() - 8)
        p.setPen(QColor("#FFFFFF") if chk else QColor(theme.MUTED if h < 0.5 else theme.TEXT))
        y = 80
        for ln in lines:
            p.drawText(QRectF(r.left() + 2, y, r.width() - 4, fm.height()), Qt.AlignHCenter | Qt.AlignVCenter, ln)
            y += fm.height() - 1
        if self.hasFocus():
            p.setPen(QPen(QColor(theme.GOLD_LIGHT), 1, Qt.DotLine)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 10, 10)
        p.end()


# ------------------------------------------------------------------ preview

BACKGROUNDS = ["parede", "escuro", "claro", "xadrez"]     # parede = starry night (default)


class Preview(QWidget):
    moved = Signal(float, float, bool)  # delta in slider units, shift held
    scaled = Signal(int, bool)
    dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.img = None; self.old = None; self.fade = 1.0; self.bg = "parede"; self.interactive = False
        self.setMinimumSize(220, 220); self.setAcceptDrops(True)
        self._drag = None; self._bgcache = None
        self.stars = StarField(90, seed=5)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._fa = QVariantAnimation(self); self._fa.setDuration(240); self._fa.setStartValue(0.0); self._fa.setEndValue(1.0)
        self._fa.setEasingCurve(QEasingCurve.OutCubic)
        self._fa.valueChanged.connect(self._set_fade); self._fa.finished.connect(self._fade_done)

    def _set_fade(self, v):
        self.fade = float(v); self.update()

    def _fade_done(self):
        self.old = None; self.update()

    def set_image(self, img, crossfade=False):
        if crossfade and FX.animations and self.img is not None and self.isVisible():
            self.old = self.img; self.img = img; self._fa.stop(); self._fa.start()
        else:
            self.img = img; self.update()

    def set_bg(self, k):
        self.bg = k if k in BACKGROUNDS else "parede"; self._bgcache = None; self.update()

    def icon_rect(self):
        side = min(self.width(), self.height()) - 40
        side = max(64, min(side, 640))
        return QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

    def _background(self):
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr, self.bg)
        if self._bgcache and self._bgcache[0] == key:
            return self._bgcache[1]
        pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr)); pm.setDevicePixelRatio(dpr); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHints(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height()).adjusted(1, 1, -1, -1)
        path = QPainterPath(); path.addRoundedRect(r, 16, 16); p.setClipPath(path)
        if self.bg == "escuro":
            g = QRadialGradient(r.center(), r.width() * 0.7); g.setColorAt(0, QColor("#1A1E3E")); g.setColorAt(1, QColor("#0A0C22")); p.fillRect(r, g)
        elif self.bg == "claro":
            g = QRadialGradient(r.center(), r.width() * 0.7); g.setColorAt(0, QColor("#FFFFFF")); g.setColorAt(1, QColor("#E3E4F3")); p.fillRect(r, g)
        elif self.bg == "xadrez":
            s = 14
            p.fillRect(r, QColor("#23264A"))
            for y in range(0, self.height(), s):
                for x in range(0, self.width(), s):
                    if (x // s + y // s) % 2 == 0:
                        p.fillRect(x, y, s, s, QColor("#2E3260"))
        else:
            p.fillRect(r, night_gradient(r))
            for cx, cy, rad, col in ((0.18, 0.2, 0.6, QColor(110, 80, 255, 80)), (0.88, 0.85, 0.6, QColor(60, 120, 255, 70)),
                                     (0.82, 0.12, 0.32, QColor(255, 201, 60, 40))):
                rg = QRadialGradient(QPointF(r.width() * cx, r.height() * cy), r.width() * rad)
                rg.setColorAt(0, col); rg.setColorAt(1, QColor(0, 0, 0, 0)); p.fillRect(r, rg)
            self.stars.paint(p, r, None, 0.9)
        p.end()
        self._bgcache = (key, pm)
        return pm

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        p.drawPixmap(0, 0, self._background())
        ir = self.icon_rect()
        if self.old is not None and self.fade < 1.0:
            p.setOpacity(1.0 - self.fade); p.drawImage(ir, self.old); p.setOpacity(self.fade)
            s = 0.94 + 0.06 * self.fade
            p.drawImage(QRectF(ir.center().x() - ir.width() * s / 2, ir.center().y() - ir.height() * s / 2, ir.width() * s, ir.height() * s), self.img)
            p.setOpacity(1.0)
        elif self.img is not None:
            p.drawImage(ir, self.img)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(160, 150, 255, 40), 1)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(r, 16, 16)

    def resizeEvent(self, e):
        self._bgcache = None; super().resizeEvent(e)

    # interaction
    def mousePressEvent(self, e):
        if self.interactive and e.button() == Qt.LeftButton:
            self._drag = e.position(); self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            side = self.icon_rect().width()
            d = e.position() - self._drag; self._drag = e.position()
            self.moved.emit(d.x() / side * 250.0, d.y() / side * 250.0, bool(e.modifiers() & Qt.ShiftModifier))
        else:
            self.setCursor(Qt.OpenHandCursor if self.interactive else Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(Qt.OpenHandCursor if self.interactive else Qt.ArrowCursor)

    def wheelEvent(self, e):
        if self.interactive:
            self.scaled.emit(5 if e.angleDelta().y() > 0 else -5, bool(e.modifiers() & Qt.ShiftModifier))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            f = u.toLocalFile()
            if f.lower().endswith((".png", ".webp", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff")):
                self.dropped.emit(f); break
            if f.lower().endswith(".json"):
                self.dropped.emit(f); break


class SizeStrip(QWidget):
    """Shows the icon at the real .ico pixel sizes."""
    SIZES = [16, 24, 32, 48, 64, 128]

    def __init__(self):
        super().__init__(); self.ims = []; self.setFixedHeight(166)

    def set_images(self, ims):
        self.ims = ims; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = QLinearGradient(r.topLeft(), r.bottomLeft()); g.setColorAt(0, QColor("#11154A")); g.setColorAt(1, QColor("#0C0F36"))
        p.setPen(QPen(QColor(theme.LINE), 1)); p.setBrush(g); p.drawRoundedRect(r, 14, 14)
        if not self.ims:
            return
        total = sum(self.SIZES) + 28 * (len(self.SIZES) - 1)
        x = (self.width() - total) / 2; base = 128 + 16
        f = QFont(self.font()); f.setPointSizeF(8.5); p.setFont(f)
        for s, pm in zip(self.SIZES, self.ims):
            p.drawPixmap(QRectF(x, base - s, s, s), pm, QRectF(0, 0, pm.width(), pm.height()))
            p.setPen(QColor(theme.DIM)); p.drawText(QRectF(x - 20, base + 6, s + 40, 18), Qt.AlignHCenter, f"{s}px")
            x += s + 28


# ------------------------------------------------------------------ header

class StarHeader(QFrame):
    """Header band: night gradient with twinkling stars and soft moon/violet glows.

    The gradient is cached in a pixmap; each animation frame only repaints the small
    rectangles around the twinkling stars.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("header")
        self.stars = StarField(55, seed=3, gold_ratio=0.18)
        self._cache = None; self._dirty = None
        clock().tick.connect(self._tick)

    def _tick(self, _t):
        if not self.isVisible():
            return
        if self._dirty is None:
            from PySide6.QtGui import QRegion
            kids = [c.geometry().adjusted(-4, -4, 4, 4) for c in self.findChildren(QWidget) if c.parentWidget() is self and c.isVisible()]
            self._dirty = QRegion()
            for r in self.stars.dirty_rects(QRectF(self.rect()).adjusted(12, 8, -12, -8), kids):
                self._dirty = self._dirty.united(r)
        self.update(self._dirty)

    def resizeEvent(self, e):
        self._cache = None; self._dirty = None; super().resizeEvent(e)

    def _background(self):
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr, round(FX.intensity, 2), FX.glow)
        if self._cache and self._cache[0] == key:
            return self._cache[1]
        pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr)); pm.setDevicePixelRatio(dpr); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath(); path.addRoundedRect(r, 18, 18); p.setClipPath(path)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0.0, QColor("#16195E")); g.setColorAt(0.35, QColor("#26208E")); g.setColorAt(1.0, QColor("#3A2296"))
        p.fillRect(r, g)
        k = 0.4 + 0.6 * FX.intensity
        for cx, col, rad in ((0.05, QColor(255, 201, 60, int(70 * k)), 0.12), (0.55, QColor(139, 92, 255, int(80 * k)), 0.35)):
            rg = QRadialGradient(QPointF(r.width() * cx, r.height() * 0.5), r.width() * rad)
            rg.setColorAt(0, col); rg.setColorAt(1, QColor(0, 0, 0, 0)); p.fillRect(r, rg)
        p.setClipping(False)
        bg = QLinearGradient(r.topLeft(), r.topRight())
        bg.setColorAt(0, QColor(255, 201, 60, int(120 * k))); bg.setColorAt(0.5, QColor(139, 92, 255, int(160 * k))); bg.setColorAt(1, QColor(61, 107, 255, int(120 * k)))
        p.setPen(QPen(bg, 1.2)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(r, 18, 18)
        p.end()
        self._cache = (key, pm)
        return pm

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap(0, 0, self._background())
        r = QRectF(self.rect()).adjusted(12, 8, -12, -8)
        self.stars.paint(p, r, clock().time if FX.animations else None, 0.85)


class GradientTitle(QWidget):
    """"Dosye" wordmark: white -> moon-gold gradient text with a soft violet neon halo."""

    def __init__(self, text, pt=20):
        super().__init__()
        self.text = text; self.f = QFont(self.font()); self.f.setPointSizeF(pt); self.f.setWeight(QFont.Black)
        fm = QFontMetricsF(self.f)
        self.setFixedSize(int(fm.horizontalAdvance(text) + 16), int(fm.height() + 6))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        fm = QFontMetricsF(self.f)
        path = QPainterPath(); path.addText(QPointF(6, fm.ascent() + 2), self.f, self.text)
        if FX.glow:
            for w, a in ((9, 26), (5, 50), (2.5, 90)):
                c = QColor(theme.VIOLET); c.setAlpha(int(a * (0.5 + FX.intensity)))
                p.setPen(QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(Qt.NoBrush); p.drawPath(path)
        g = QLinearGradient(0, 0, 0, self.height()); g.setColorAt(0, QColor("#FFFFFF")); g.setColorAt(0.55, QColor("#FFF1C2")); g.setColorAt(1, QColor(theme.GOLD))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(path)


class Toast(QFrame):
    """Non-modal notification that slides/fades in over the preview."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast"); self.hide()
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 10, 10, 10); lay.setSpacing(10)
        col = QVBoxLayout(); col.setSpacing(1)
        self.text = QLabel(); self.text.setObjectName("toastText"); self.text.setWordWrap(True)
        self.path = ElidedLabel("", Qt.ElideMiddle); self.path.setObjectName("toastPath")
        col.addWidget(self.text); col.addWidget(self.path); lay.addLayout(col, 1)
        self.open_btn = QPushButton(); self.open_btn.setObjectName("ghost"); self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(self._open); lay.addWidget(self.open_btn)
        self._target = None
        self.eff = QGraphicsOpacityEffect(self); self.eff.setOpacity(0.0); self.setGraphicsEffect(self.eff)
        self.anim = QVariantAnimation(self); self.anim.setDuration(260); self.anim.valueChanged.connect(self._step)
        self.anim.finished.connect(self._anim_done)
        self.timer = QTimer(self, singleShot=True, timeout=self.dismiss)
        self._base_y = 0

    def show_message(self, msg, path=None):
        self.text.setText(msg)
        self._target = path
        self.path.setVisible(bool(path)); self.path.setText(path or "")
        self.open_btn.setVisible(bool(path) and os.path.exists(path or ""))
        self.open_btn.setText(tr("toast.show_folder"))
        par = self.parentWidget()
        w = min(560, par.width() - 40)
        self.setFixedWidth(w); self.adjustSize()
        self._base_y = par.height() - self.height() - 26
        self.move((par.width() - w) // 2, self._base_y)
        self.show(); self.raise_()
        self.anim.stop(); self.anim.setStartValue(self.eff.opacity()); self.anim.setEndValue(1.0)
        self.anim.setDuration(260 if FX.animations else 1); self.anim.start()
        self.timer.start(4200 if path else 2800)

    def dismiss(self):
        self.anim.stop(); self.anim.setStartValue(self.eff.opacity()); self.anim.setEndValue(0.0)
        self.anim.setDuration(320 if FX.animations else 1); self.anim.start()

    def _step(self, v):
        v = float(v); self.eff.setOpacity(v)
        self.move(self.x(), int(self._base_y + 14 * (1 - v)))

    def _anim_done(self):
        if self.eff.opacity() <= 0.01:
            self.hide()

    def _open(self):
        if self._target:
            d = self._target if os.path.isdir(self._target) else os.path.dirname(self._target)
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))


def app_pixmap(path, size, dpr):
    pm = QPixmap(path)
    if pm.isNull():
        return pm
    pm = pm.scaled(int(size * dpr), int(size * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


def bg_swatch(key, size, dpr=1.0):
    """Small rounded swatch that previews one of the preview BACKGROUNDS (used as a button icon)."""
    px = int(round(size * dpr))
    pm = QPixmap(px, px); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(0.5, 0.5, px - 1, px - 1)
    path = QPainterPath(); path.addRoundedRect(r, px * 0.28, px * 0.28)
    p.setClipPath(path)
    if key == "parede":
        g = QLinearGradient(0, 0, px, px)
        g.setColorAt(0, QColor("#1B2060")); g.setColorAt(1, QColor("#070920"))
        p.fillRect(r, g)
        p.setPen(Qt.NoPen)
        for fx, fy, rr, c in ((0.28, 0.30, 0.07, "#FFE38A"), (0.70, 0.22, 0.05, "#ECEBFF"),
                              (0.58, 0.66, 0.06, "#ECEBFF"), (0.24, 0.74, 0.04, "#A3A7DA")):
            p.setBrush(QColor(c)); p.drawEllipse(QPointF(fx * px, fy * px), rr * px, rr * px)
    elif key == "escuro":
        p.fillRect(r, QColor("#16182A"))
    elif key == "claro":
        p.fillRect(r, QColor("#ECEEF6"))
    else:
        n = 4; cs = px / n
        for i in range(n):
            for j in range(n):
                p.fillRect(QRectF(i * cs, j * cs, cs + 0.5, cs + 0.5), QColor("#FFFFFF" if (i + j) % 2 else "#C9CBD6"))
    p.setClipping(False)
    p.setPen(QPen(QColor(255, 255, 255, 70), max(1.0, dpr))); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r, px * 0.28, px * 0.28)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return QIcon(pm)

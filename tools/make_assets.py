"""Regenerates every bundled asset of Dosye.

    python tools/make_assets.py            # stickers + UI toggles (Qt only)
    python tools/make_assets.py --covers   # also the sample cover textures (needs numpy)

The app icons (assets/icons/dosye_icon.* and dosye_favicon.*) are hand-made and
are NOT generated here.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "src", "dosye", "assets")
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QLinearGradient, QRadialGradient
from PySide6.QtCore import Qt, QRectF, QPointF
app = QGuiApplication(sys.argv)

import stickers
stickers.generate(os.path.join(ASSETS, "stickers"))
if "--covers" in sys.argv:
    import textures
    textures.generate(os.path.join(ASSETS, "covers"))

# Toggle switch images for QCheckBox (themed after the Dosye icon: indigo -> violet, golden knob glow)
UI = os.path.join(ASSETS, "ui"); os.makedirs(UI, exist_ok=True)
def toggle(name, on, enabled=True):
    W, H = 76, 40
    im = QImage(W, H, QImage.Format_ARGB32_Premultiplied); im.fill(Qt.transparent)
    p = QPainter(im); p.setRenderHint(QPainter.Antialiasing)
    p.setOpacity(1.0 if enabled else 0.45)
    r = QRectF(4, 3, 68, 34)
    if on:
        glow = QRadialGradient(QPointF(38, 20), 40); glow.setColorAt(0, QColor(140, 110, 255, 90)); glow.setColorAt(1, QColor(140, 110, 255, 0))
        p.setPen(Qt.NoPen); p.setBrush(glow); p.drawRoundedRect(QRectF(0, 0, W, H), 20, 20)
        g = QLinearGradient(r.left(), 0, r.right(), 0); g.setColorAt(0, QColor("#4C46F0")); g.setColorAt(1, QColor("#9D5CFF"))
        p.setBrush(g); p.setPen(Qt.NoPen)
    else:
        p.setBrush(QColor("#1C2050")); p.setPen(QColor("#2E3473"))
    p.drawRoundedRect(r, 17, 17)
    cx = 55 if on else 21
    p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 60)); p.drawEllipse(QPointF(cx, 21.5), 13, 13)
    if on:
        kg = QLinearGradient(0, 7, 0, 33); kg.setColorAt(0, QColor("#FFF1B0")); kg.setColorAt(1, QColor("#FFC53D")); p.setBrush(kg)
    else:
        p.setBrush(QColor("#8C93C8"))
    p.drawEllipse(QPointF(cx, 20), 13, 13)
    p.end(); im.save(os.path.join(UI, name))
toggle("toggle_on.png", True); toggle("toggle_off.png", False)
toggle("toggle_on_dis.png", True, False); toggle("toggle_off_dis.png", False, False)

# Small chevron for combo boxes
im = QImage(24, 24, QImage.Format_ARGB32_Premultiplied); im.fill(Qt.transparent)
p = QPainter(im); p.setRenderHint(QPainter.Antialiasing)
from PySide6.QtGui import QPen
p.setPen(QPen(QColor("#B9B4FF"), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
p.drawPolyline([QPointF(7, 10), QPointF(12, 15), QPointF(17, 10)]); p.end()
im.save(os.path.join(UI, "chevron.png"))
print("assets ok ->", ASSETS)

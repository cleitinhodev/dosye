# -*- coding: utf-8 -*-
"""Generates the sample PNG stickers (vector-drawn) bundled with Dosye.

Run:  python tools/stickers.py src/dosye/assets/stickers
"""
import math, os, sys
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QImage, QPainter, QPainterPath, QColor, QLinearGradient,
                           QRadialGradient, QPen, QBrush)

N = 512
STICKERS = [("fotos", "Fotos"), ("musica", "Música"), ("codigo", "Código"), ("coracao", "Coração"),
            ("estrela", "Estrela"), ("nuvem", "Nuvem"), ("jogo", "Jogos"), ("download", "Downloads"),
            ("lua", "Lua")]

def _img():
    im = QImage(N, N, QImage.Format_ARGB32_Premultiplied); im.fill(Qt.transparent)
    p = QPainter(im); p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    return im, p

def lg(x1, y1, x2, y2, *stops):
    g = QLinearGradient(x1, y1, x2, y2)
    for i, c in enumerate(stops): g.setColorAt(i/(len(stops)-1), QColor(c))
    return g

def fotos():
    im, p = _img()
    def polaroid(angle, sky, ground, sun=True):
        p.save(); p.translate(256, 270); p.rotate(angle)
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 40)); p.drawRoundedRect(QRectF(-160, -186, 330, 380), 14, 14)
        p.setBrush(lg(0, -190, 0, 190, "#FFFFFF", "#EEF1F4")); p.drawRoundedRect(QRectF(-165, -195, 330, 380), 14, 14)
        r = QRectF(-140, -170, 280, 260)
        p.save(); path = QPainterPath(); path.addRoundedRect(r, 6, 6); p.setClipPath(path)
        p.fillRect(r, lg(0, -170, 0, 90, *sky))
        if sun:
            g = QRadialGradient(70, -95, 60); g.setColorAt(0, QColor("#FFF6C8")); g.setColorAt(0.45, QColor("#FFD25E")); g.setColorAt(1, QColor(255, 210, 94, 0))
            p.setBrush(g); p.drawEllipse(QPointF(70, -95), 60, 60)
        m = QPainterPath(); m.moveTo(-150, 90); m.lineTo(-150, 10); m.lineTo(-70, -60); m.lineTo(0, 10); m.lineTo(40, -20); m.lineTo(150, 50); m.lineTo(150, 90)
        p.setBrush(lg(0, -60, 0, 90, *ground)); p.drawPath(m)
        m2 = QPainterPath(); m2.moveTo(-150, 90); m2.lineTo(-150, 50); m2.cubicTo(-60, 20, 40, 60, 150, 30); m2.lineTo(150, 90)
        p.setBrush(QColor(ground[-1]).darker(125)); p.drawPath(m2)
        p.restore(); p.restore()
    polaroid(-12, ("#9AD3FF", "#E7F5FF"), ("#7C9CC6", "#3F5F8F"), sun=False)
    polaroid(7, ("#FF9A8B", "#FFD6A5"), ("#6BBF7A", "#2E7D4F"))
    p.end(); return im

def musica():
    im, p = _img(); p.setPen(Qt.NoPen)
    g = lg(100, 60, 420, 470, "#B57CFF", "#6A3DF0")
    path = QPainterPath()
    path.addEllipse(QPointF(160, 390), 78, 60); path.addEllipse(QPointF(370, 340), 78, 60)
    path.addRect(QRectF(212, 120, 34, 270)); path.addRect(QRectF(422, 70, 34, 270))
    beam = QPainterPath(); beam.moveTo(212, 120); beam.lineTo(456, 70); beam.lineTo(456, 150); beam.lineTo(212, 200); beam.closeSubpath()
    path = path.united(beam)
    p.setBrush(QColor(0, 0, 0, 50)); p.translate(6, 10); p.drawPath(path); p.translate(-6, -10)
    p.setBrush(g); p.drawPath(path)
    p.setBrush(QColor(255, 255, 255, 90)); p.drawEllipse(QPointF(138, 370), 26, 14); p.drawEllipse(QPointF(348, 320), 26, 14)
    p.end(); return im

def codigo():
    im, p = _img(); p.setPen(Qt.NoPen)
    r = QRectF(56, 96, 400, 320)
    p.setBrush(QColor(0, 0, 0, 60)); p.drawRoundedRect(r.translated(6, 12), 40, 40)
    p.setBrush(lg(0, 96, 0, 416, "#2B3245", "#151926")); p.drawRoundedRect(r, 40, 40)
    p.setBrush(QColor("#3A4258")); p.drawRoundedRect(QRectF(56, 96, 400, 60), 40, 40); p.drawRect(QRectF(56, 126, 400, 30))
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        p.setBrush(QColor(c)); p.drawEllipse(QPointF(96+i*34, 126), 11, 11)
    pen = QPen(QColor("#5CE1E6"), 30, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin); p.setPen(pen)
    p.drawPolyline([QPointF(180, 220), QPointF(130, 285), QPointF(180, 350)])
    p.drawPolyline([QPointF(332, 220), QPointF(382, 285), QPointF(332, 350)])
    p.setPen(QPen(QColor("#FF7AC6"), 30, Qt.SolidLine, Qt.RoundCap)); p.drawLine(QPointF(282, 205), QPointF(232, 365))
    p.end(); return im

def coracao():
    im, p = _img(); p.setPen(Qt.NoPen)
    h = QPainterPath(); h.moveTo(256, 450)
    h.cubicTo(60, 320, 30, 200, 90, 130); h.cubicTo(150, 60, 240, 80, 256, 160)
    h.cubicTo(272, 80, 362, 60, 422, 130); h.cubicTo(482, 200, 452, 320, 256, 450)
    p.setBrush(QColor(0, 0, 0, 55)); p.translate(4, 12); p.drawPath(h); p.translate(-4, -12)
    p.setBrush(lg(100, 80, 400, 450, "#FF6B8B", "#E5194E")); p.drawPath(h)
    p.setBrush(QColor(255, 255, 255, 110)); p.save(); p.translate(150, 170); p.rotate(-35); p.drawEllipse(QPointF(0, 0), 46, 24); p.restore()
    p.end(); return im

def estrela():
    im, p = _img(); p.setPen(Qt.NoPen)
    pts = []
    for i in range(10):
        a = -math.pi/2 + i*math.pi/5; r = 220 if i % 2 == 0 else 98
        pts.append(QPointF(256+math.cos(a)*r, 270+math.sin(a)*r))
    s = QPainterPath(); s.addPolygon(pts); s.closeSubpath()
    p.setBrush(QColor(0, 0, 0, 55)); p.translate(4, 12); p.drawPath(s); p.translate(-4, -12)
    p.setPen(QPen(QColor("#F59E0B"), 26, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(lg(0, 50, 0, 480, "#FFE58A", "#FFB21A")); p.drawPath(s)
    p.end(); return im

def nuvem():
    im, p = _img(); p.setPen(Qt.NoPen)
    c = QPainterPath()
    c.addEllipse(QPointF(180, 290), 110, 100); c.addEllipse(QPointF(300, 230), 130, 125)
    c.addEllipse(QPointF(390, 310), 85, 80); c.addRoundedRect(QRectF(80, 290, 380, 100), 50, 50)
    c.setFillRule(Qt.WindingFill); c = c.simplified()
    p.setBrush(QColor(0, 0, 0, 45)); p.translate(4, 12); p.drawPath(c); p.translate(-4, -12)
    p.setBrush(lg(0, 100, 0, 390, "#FFFFFF", "#D6E6F7")); p.drawPath(c)
    p.setPen(QPen(QColor("#3B82F6"), 30, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(270, 340), QPointF(270, 220)); p.drawPolyline([QPointF(220, 270), QPointF(270, 215), QPointF(320, 270)])
    p.end(); return im

def jogo():
    im, p = _img(); p.setPen(Qt.NoPen)
    b = QPainterPath()
    b.moveTo(150, 170); b.lineTo(362, 170)
    b.cubicTo(440, 170, 470, 260, 480, 340); b.cubicTo(492, 420, 430, 440, 395, 395)
    b.lineTo(360, 350); b.lineTo(152, 350); b.lineTo(117, 395)
    b.cubicTo(82, 440, 20, 420, 32, 340); b.cubicTo(42, 260, 72, 170, 150, 170); b.closeSubpath()
    p.setBrush(QColor(0, 0, 0, 55)); p.translate(4, 12); p.drawPath(b); p.translate(-4, -12)
    p.setBrush(lg(0, 170, 0, 440, "#4A5068", "#23273A")); p.drawPath(b)
    p.setBrush(QColor("#C7CCDD"))
    p.drawRoundedRect(QRectF(118, 236, 26, 80), 6, 6); p.drawRoundedRect(QRectF(91, 263, 80, 26), 6, 6)
    for (x, y, col) in ((380, 240, "#FFD43B"), (414, 274, "#FF6B6B"), (346, 274, "#4DABF7"), (380, 308, "#51CF66")):
        p.setBrush(QColor(col)); p.drawEllipse(QPointF(x, y), 17, 17)
    p.setBrush(QColor(255, 255, 255, 40)); p.drawRoundedRect(QRectF(150, 182, 212, 30), 15, 15)
    p.end(); return im

def download():
    im, p = _img(); p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 50)); p.drawEllipse(QPointF(260, 268), 205, 205)
    p.setBrush(lg(0, 50, 0, 470, "#34D399", "#059669")); p.drawEllipse(QPointF(256, 256), 205, 205)
    p.setBrush(QColor(255, 255, 255, 50)); p.drawEllipse(QPointF(256, 150), 150, 80)
    p.setPen(QPen(QColor("white"), 44, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(256, 140), QPointF(256, 320)); p.drawPolyline([QPointF(180, 255), QPointF(256, 330), QPointF(332, 255)])
    p.drawLine(QPointF(170, 380), QPointF(342, 380))
    p.end(); return im

def lua():
    """Golden crescent moon with sparkles (the Dosye mascot's night sky)."""
    im, p = _img(); p.setPen(Qt.NoPen)
    rg = QRadialGradient(QPointF(240, 262), 235); rg.setColorAt(0, QColor(255, 210, 80, 70)); rg.setColorAt(1, QColor(255, 200, 60, 0))
    p.setBrush(rg); p.drawEllipse(QPointF(250, 260), 250, 250)
    moon = QPainterPath(); moon.addEllipse(QPointF(240, 262), 190, 190)
    cut = QPainterPath(); cut.addEllipse(QPointF(330, 200), 165, 165)
    moon = moon.subtracted(cut)
    p.setBrush(QColor(90, 50, 0, 55)); p.translate(6, 10); p.drawPath(moon); p.translate(-8, -14)
    p.setBrush(lg(80, 80, 380, 460, "#FFF3A6", "#FFC93C", "#F29E1F")); p.drawPath(moon)
    p.setPen(QPen(QColor(150, 80, 0, 150), 7)); p.setBrush(Qt.NoBrush); p.drawPath(moon); p.setPen(Qt.NoPen)
    hl = QPainterPath(); hl.addEllipse(QPointF(150, 240), 40, 95)
    p.setBrush(QColor(255, 255, 255, 90)); p.drawPath(hl.intersected(moon))
    def star(cx, cy, r, a=255):
        path = QPainterPath()
        for i in range(8):
            ang = math.pi/4*i - math.pi/2; rad = r if i % 2 == 0 else r*0.28
            pt = QPointF(cx + rad*math.cos(ang), cy + rad*math.sin(ang))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath(); p.setBrush(QColor(255, 245, 200, a)); p.drawPath(path)
    star(392, 330, 46); star(430, 170, 30, 230); star(345, 440, 22, 210)
    p.end(); return im

FUNCS = dict(lua=lua, fotos=fotos, musica=musica, codigo=codigo, coracao=coracao, estrela=estrela, nuvem=nuvem, jogo=jogo, download=download)

def generate(outdir):
    os.makedirs(outdir, exist_ok=True)
    for key, _ in STICKERS:
        FUNCS[key]().save(os.path.join(outdir, key + ".png"))

if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication(sys.argv)
    generate(sys.argv[1] if len(sys.argv) > 1 else "assets")

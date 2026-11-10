# -*- coding: utf-8 -*-
"""Formatos extras de pasta (v3). Tudo desenhado com caminhos vetoriais no espaço 1000x1000.

Cada formato devolve um Geo com:
  back / front        -> caminhos do painel traseiro e da frente
  front_top, body_top -> alturas usadas pelos papéis e pela imagem "saindo"
  behind              -> painéis extras atrás de tudo: (caminho, escurecer) ou (caminho, QColor)
  back_deco/front_deco-> funções que desenham detalhes (zíper, clipe, elástico...)
  fill                -> None | "dark" (neon) | "pale" (ícone de linha)
"""
import math, random
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QPainterPath, QColor, QLinearGradient, QRadialGradient, QPen, QBrush, QTransform,
                           QPolygonF)
from . import render as fc
from .render import rpoly, Geo, hsl_adj, with_alpha, mix, qc

# ------------------------------------------------------------------ helpers

def rr(x, y, w, h, r):
    p = QPainterPath(); p.addRoundedRect(QRectF(x, y, w, h), r, r); return p

def circle(cx, cy, r):
    p = QPainterPath(); p.addEllipse(QPointF(cx, cy), r, r); return p

def std_back(L, R, tab_top, body_top, tab_end, slope, bottom, r=24, rt=26):
    return rpoly([(L, tab_top), (tab_end, tab_top), (tab_end+slope, body_top), (R, body_top), (R, bottom), (L, bottom)],
                 [r, rt, rt, r, r, r])

def std_front(L, R, top, bottom, r=22, rb=None):
    rb = r if rb is None else rb
    return rpoly([(L, top), (R, top), (R, bottom), (L, bottom)], [r, r, rb, rb])

def union(*paths):
    out = QPainterPath(); out.setFillRule(Qt.WindingFill)
    for p in paths:
        out = out.united(p)
    return out.simplified()

def below(path, y):
    """Parte do caminho abaixo da linha y."""
    r = QPainterPath(); r.addRect(QRectF(-100, y, 1200, 1200)); return path.intersected(r)

def bezier_pts(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n+1):
        t = i/n; u = 1-t
        out.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0], u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return out

def metal(rect, gold=False):
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    cols = ("#FFF4C8", "#E9C46A", "#B8862B", "#F3D98B") if gold else ("#FFFFFF", "#D5DAE1", "#8E96A3", "#E8ECF1")
    for i, c in enumerate(cols): g.setColorAt(i/3, QColor(c))
    return g

def accent(c, deg, s=0.72, l=0.56):
    h, _, _, _ = c.getHslF()
    if h < 0: h = 0.08
    return QColor.fromHslF((h + deg/360.0) % 1.0, s, l)

def soft_shadow(p, path, dx=0, dy=8, alpha=60, steps=4, spread=10):
    """Sombra suave falsa (sem blur) para detalhes."""
    p.save(); p.setPen(Qt.NoPen)
    for i in range(steps, 0, -1):
        p.setBrush(QColor(0, 0, 0, int(alpha/steps)))
        t = QTransform().translate(dx, dy)
        p.setPen(QPen(QColor(0, 0, 0, int(alpha/steps)), spread*i/steps*2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(t.map(path))
    p.restore()

class Ctx:
    def __init__(self, P, geo, ftop, fbot, k):
        self.P, self.geo, self.ftop, self.fbot, self.k = P, geo, ftop, fbot, k
        self.base = qc(P["color1"])
        self.mid = mix(ftop, fbot, 0.5)
        self.dark = hsl_adj(self.mid, -0.24)
        self.darker = hsl_adj(self.mid, -0.38)
        self.light = hsl_adj(self.mid, +0.20)

def G(back, front, front_top, body_top, left, right, bottom, **kw):
    g = Geo(back, front, front_top, body_top, left, right, bottom)
    for k_, v in kw.items(): setattr(g, k_, v)
    return g

# ================================================================= RETRÔ

def s_xp():
    back = std_back(80, 862, 212, 262, 338, 46, 832, r=16, rt=20)
    front = rpoly([(150, 372), (936, 372), (866, 838), (80, 838)], [16, 16, 18, 18])
    return G(back, front, 372, 262, 80, 862, 838, rim=1.4, back_dark=0.16)

def s_vista():
    back = std_back(110, 890, 198, 250, 360, 50, 842, r=22, rt=24)
    front = rpoly([(160, 405), (840, 405), (915, 848), (85, 848)], [18, 18, 24, 24])
    def fd(p, c):
        fr = c.geo.front.boundingRect()
        p.save(); p.setClipPath(c.geo.front); p.setPen(Qt.NoPen)
        sheen = QPainterPath(); sheen.moveTo(fr.left()-20, fr.top()); sheen.lineTo(fr.left()+fr.width()*0.62, fr.top())
        sheen.lineTo(fr.left()+fr.width()*0.38, fr.bottom()); sheen.lineTo(fr.left()-20, fr.bottom()); sheen.closeSubpath()
        g = QLinearGradient(fr.left(), fr.top(), fr.left()+fr.width()*0.5, fr.bottom())
        g.setColorAt(0, QColor(255, 255, 255, 70)); g.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(g); p.drawPath(sheen); p.restore()
    return G(back, front, 405, 250, 110, 890, 848, rim=1.7, back_dark=0.14, front_deco=fd)

def s_pautada():
    back = rpoly([(90, 262), (330, 262), (372, 206), (628, 206), (670, 262), (910, 262), (910, 846), (90, 846)],
                 [12, 10, 12, 12, 10, 12, 12, 12])
    front = std_front(90, 910, 362, 846, r=12)
    def bd(p, c):   # folha pautada sempre visível
        p.save(); p.setClipRect(QRectF(0, 0, 1000, 420))
        r = QRectF(150, 232, 700, 300)
        p.setPen(QPen(QColor(0, 0, 0, 30), 2)); p.setBrush(QColor("#FFFDF5")); p.drawRect(r)
        p.setPen(QPen(QColor(90, 140, 220, 120), 4))
        for y in range(270, 420, 30): p.drawLine(QPointF(150, y), QPointF(850, y))
        p.setPen(QPen(QColor(230, 80, 80, 150), 4)); p.drawLine(QPointF(220, 232), QPointF(220, 420))
        p.restore()
    def fd(p, c):
        p.setPen(QPen(with_alpha(c.dark, 0.55), 5)); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(140, 410, 300, 120), 8, 8)
        p.setPen(QPen(with_alpha(c.dark, 0.45), 6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(170, 455), QPointF(400, 455)); p.drawLine(QPointF(170, 490), QPointF(330, 490))
    return G(back, front, 362, 206, 90, 910, 846, back_deco=bd, front_deco=fd, rim=0.8, back_dark=0.10, back_deco_late=True)

PX = 1000/16.0
def _px(pts): return [(x*PX, y*PX) for x, y in pts]

def s_pixel():
    back = rpoly(_px([(1, 2), (6, 2), (6, 3), (7, 3), (7, 4), (15, 4), (15, 13), (14, 13), (14, 14), (2, 14), (2, 13), (1, 13)]), 0.01)
    front = rpoly(_px([(1, 6), (15, 6), (15, 13), (14, 13), (14, 14), (2, 14), (2, 13), (1, 13)]), 0.01)
    def outline(p, path, col):
        p.save(); p.setClipPath(path); p.setPen(QPen(col, PX*2, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)); p.setBrush(Qt.NoBrush)
        p.drawPath(path); p.restore()
    def bd(p, c):
        p.setPen(Qt.NoPen); p.setBrush(with_alpha(QColor("white"), 0.35))
        p.drawRect(QRectF(2*PX, 3*PX, 4*PX, PX*0.999))
        outline(p, c.geo.back, with_alpha(hsl_adj(c.mid, -0.30), 0.95))
    def fd(p, c):
        p.setPen(Qt.NoPen)
        p.setBrush(with_alpha(QColor("white"), 0.45)); p.drawRect(QRectF(2*PX, 7*PX, 12*PX, PX))
        p.setBrush(with_alpha(QColor("white"), 0.22)); p.drawRect(QRectF(2*PX, 8*PX, PX, 4*PX))
        p.setBrush(with_alpha(QColor("black"), 0.16)); p.drawRect(QRectF(3*PX, 12*PX, 11*PX, PX)); p.drawRect(QRectF(13*PX, 8*PX, PX, 4*PX))
        outline(p, c.geo.front, with_alpha(hsl_adj(c.mid, -0.30), 0.95))
    return G(back, front, 6*PX, 4*PX, PX, 15*PX, 14*PX, back_deco=bd, front_deco=fd, rim=0.0, back_dark=0.14, no_gloss=True)

def s_kraft():
    back = std_back(90, 910, 205, 258, 380, 52, 846, r=14, rt=16)
    rnd = random.Random(42)
    top = []
    x = 90.0
    while x < 910:
        top.append((x, 356 + rnd.uniform(-11, 11))); x += rnd.uniform(16, 30)
    top.append((910, 356))
    pts = [(90, 356)] + top[1:] + [(910, 846), (90, 846)]
    radii = [10] + [1.5]*(len(top)-1) + [14, 14]
    front = rpoly(pts, radii)
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front)
        edge = QPainterPath(); edge.moveTo(*top[0])
        for pt in top[1:]: edge.lineTo(*pt)
        p.setPen(QPen(with_alpha(hsl_adj(c.mid, +0.28), 0.85), 11, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(Qt.NoBrush)
        p.drawPath(edge)
        r2 = random.Random(7); p.setPen(Qt.NoPen)
        for _ in range(260):
            xx, yy = r2.uniform(90, 910), r2.uniform(360, 846)
            p.setBrush(with_alpha(QColor("black") if r2.random() < 0.6 else QColor("white"), r2.uniform(0.04, 0.10)))
            p.drawEllipse(QPointF(xx, yy), r2.uniform(2, 6), r2.uniform(1, 3))
        p.restore()
    return G(back, front, 356, 258, 90, 910, 846, front_deco=fd, rim=0.5, back_dark=0.13)

def s_origami():
    back = rpoly([(100, 215), (360, 215), (420, 268), (900, 268), (900, 840), (100, 840)], 5)
    front = rpoly([(100, 372), (770, 372), (900, 480), (900, 840), (100, 840)], 5)
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front); p.setPen(Qt.NoPen)
        facets = [([(100, 372), (430, 372), (300, 840), (100, 840)], QColor(255, 255, 255, 34)),
                  ([(430, 372), (770, 372), (650, 840), (300, 840)], QColor(0, 0, 0, 0)),
                  ([(770, 372), (900, 480), (900, 840), (650, 840)], QColor(0, 0, 0, 40))]
        for pts, col in facets:
            p.setBrush(col); p.drawPolygon(QPolygonF([QPointF(*q) for q in pts]))
        p.setPen(QPen(QColor(255, 255, 255, 60), 3)); p.drawLine(QPointF(430, 372), QPointF(300, 840))
        p.setPen(QPen(QColor(0, 0, 0, 45), 3)); p.drawLine(QPointF(770, 372), QPointF(650, 840))
        p.restore()
        flap = QPainterPath(); flap.moveTo(770, 372); flap.lineTo(900, 480); flap.lineTo(785, 500); flap.closeSubpath()
        soft_shadow(p, flap, 6, 8, 70, 3, 6)
        p.setPen(Qt.NoPen); g = QLinearGradient(770, 372, 860, 500); g.setColorAt(0, c.light); g.setColorAt(1, hsl_adj(c.mid, +0.08))
        p.setBrush(g); p.drawPath(flap)
    return G(back, front, 372, 268, 100, 900, 840, front_deco=fd, rim=0.6, back_dark=0.15)

def s_envelope():
    back = rpoly([(110, 330), (500, 140), (890, 330), (890, 846), (110, 846)], [14, 44, 14, 16, 16])
    front = rpoly([(110, 420), (500, 610), (890, 420), (890, 846), (110, 846)], [12, 50, 12, 16, 16])
    def bd(p, c):
        p.setPen(QPen(with_alpha(c.darker, 0.35), 4)); p.setBrush(Qt.NoBrush)
        p.drawLine(QPointF(140, 330), QPointF(860, 330))
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front)
        p.setPen(QPen(with_alpha(c.darker, 0.28), 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(110, 846), QPointF(420, 640)); p.drawLine(QPointF(890, 846), QPointF(580, 640))
        p.setPen(QPen(with_alpha(QColor("white"), 0.25), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(112, 840), QPointF(422, 634)); p.drawLine(QPointF(888, 840), QPointF(578, 634))
        p.restore()
    return G(back, front, 420, 280, 110, 890, 846, back_deco=bd, front_deco=fd, rim=0.7, back_dark=0.16, emblem_c=(500, 735))

def s_cordao():
    back = rr(120, 250, 760, 600, 18)
    front = std_front(120, 880, 330, 850, r=16, rb=18)
    def fd(p, c):
        flap = QPainterPath(); flap.moveTo(120, 330); flap.lineTo(880, 330); flap.lineTo(520, 560); flap.quadTo(500, 572, 480, 560); flap.closeSubpath()
        soft_shadow(p, flap, 0, 10, 70, 4, 8)
        g = QLinearGradient(0, 330, 0, 570); g.setColorAt(0, hsl_adj(c.mid, +0.06)); g.setColorAt(1, hsl_adj(c.mid, -0.06))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(flap)
        for (x, y) in ((500, 520), (500, 700)):
            p.setBrush(QColor(0, 0, 0, 60)); p.drawEllipse(QPointF(x+3, y+6), 34, 34)
            rg = QRadialGradient(x-10, y-10, 40); rg.setColorAt(0, hsl_adj(c.base, -0.05, a=1)); rg.setColorAt(1, c.darker)
            p.setBrush(QColor("#E8DCC8")); p.drawEllipse(QPointF(x, y), 32, 32)
            p.setBrush(QColor(120, 90, 60, 90)); p.drawEllipse(QPointF(x, y), 8, 8)
        s = QPainterPath(); s.moveTo(500, 520); s.cubicTo(590, 560, 590, 660, 500, 700); s.cubicTo(410, 660, 410, 560, 500, 520)
        s.moveTo(500, 700); s.cubicTo(540, 760, 610, 760, 640, 820)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 50), 11, Qt.SolidLine, Qt.RoundCap)); p.drawPath(QTransform().translate(3, 5).map(s))
        p.setPen(QPen(QColor("#C9A876"), 8, Qt.SolidLine, Qt.RoundCap)); p.drawPath(s)
    return G(back, front, 330, 230, 120, 880, 850, front_deco=fd, rim=0.6, back_dark=0.14, emblem_c=(300, 700))

# ============================================================ ESCRITÓRIO

def s_elastico():
    back = std_back(95, 905, 198, 250, 380, 50, 846, r=22, rt=24)
    front = std_front(95, 905, 330, 846, r=22)
    def band(p, c, a, b):
        path = QPainterPath(); path.moveTo(*a); path.lineTo(*b)
        p.setPen(QPen(QColor(0, 0, 0, 70), 40, Qt.SolidLine, Qt.FlatCap)); p.drawPath(QTransform().translate(2, 7).map(path))
        p.setPen(QPen(hsl_adj(c.darker, -0.05, -0.1), 34, Qt.SolidLine, Qt.FlatCap)); p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 55), 6, Qt.SolidLine, Qt.FlatCap)); p.drawPath(QTransform().translate(-6, -6).map(path))
    def fd(p, c):
        from PySide6.QtGui import QPainterPathStroker
        st = QPainterPathStroker(); st.setWidth(22); st.setJoinStyle(Qt.RoundJoin)
        p.save(); p.setClipPath(c.geo.front.united(st.createStroke(c.geo.front)))
        band(p, c, (690, 318), (920, 548)); band(p, c, (920, 640), (712, 856))
        p.restore()
    return G(back, front, 330, 250, 95, 905, 846, front_deco=fd, rim=1.0, back_dark=0.13)

def s_caixa():
    back = rpoly([(175, 230), (825, 230), (905, 330), (905, 846), (95, 846), (95, 330)], [14, 14, 10, 14, 14, 10])
    hole = rr(420, 470, 160, 52, 26)
    front = std_front(95, 905, 330, 846, r=12).subtracted(hole)
    def bd(p, c):
        p.save(); p.setClipPath(c.geo.back)
        g = QLinearGradient(0, 230, 0, 330); g.setColorAt(0, QColor(0, 0, 0, 90)); g.setColorAt(1, QColor(0, 0, 0, 20))
        p.fillRect(QRectF(0, 230, 1000, 100), g); p.restore()
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front); p.setPen(Qt.NoPen)
        p.setBrush(with_alpha(QColor("white"), 0.16)); p.drawRect(QRectF(95, 330, 810, 70))
        p.setBrush(with_alpha(QColor("black"), 0.10)); p.drawRect(QRectF(95, 398, 810, 6))
        p.restore()
        lab = QRectF(330, 610, 340, 150)
        soft_shadow(p, rr(330, 610, 340, 150, 10), 0, 5, 40, 3, 4)
        p.setPen(Qt.NoPen); p.setBrush(QColor("#FBFAF6")); p.drawRoundedRect(lab, 10, 10)
        p.setPen(QPen(QColor(120, 130, 145, 120), 8, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(370, 655), QPointF(630, 655)); p.drawLine(QPointF(370, 700), QPointF(560, 700))
        p.setPen(QPen(with_alpha(c.darker, 0.6), 4)); p.setBrush(Qt.NoBrush); p.drawRoundedRect(QRectF(420, 470, 160, 52), 26, 26)
    return G(back, front, 330, 210, 95, 905, 846, back_deco=bd, front_deco=fd, rim=0.9, back_dark=0.20, emblem_c=(500, 560))

def s_sanfonada():
    back = rpoly([(80, 300), (190, 222), (810, 222), (920, 300), (920, 846), (80, 846)], [30, 60, 60, 30, 20, 20])
    front = std_front(128, 872, 380, 846, r=16, rb=18)
    def bd(p, c):
        p.save(); p.setClipPath(c.geo.back); p.setPen(Qt.NoPen)
        for (x0, x1) in ((80, 128), (872, 920)):
            n = 9; h = (846-380)/n
            for i in range(n):
                y = 380 + i*h
                tri = QPolygonF([QPointF(x0, y), QPointF(x1, y+h/2), QPointF(x0, y+h)]) if x0 < 500 else \
                      QPolygonF([QPointF(x1, y), QPointF(x0, y+h/2), QPointF(x1, y+h)])
                p.setBrush(QColor(0, 0, 0, 55)); p.drawPolygon(tri)
                p.setBrush(QColor(255, 255, 255, 30)); p.drawRect(QRectF(x0, y, x1-x0, 3))
        p.restore()
    def fd(p, c):
        p.setPen(QPen(with_alpha(c.darker, 0.45), 4)); p.setBrush(Qt.NoBrush)
        for i in range(1, 3):
            p.drawLine(QPointF(128+i*0, 380), QPointF(128, 846))
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 50)); p.drawEllipse(QPointF(503, 433), 24, 24)
        p.setBrush(metal(QRectF(480, 410, 46, 46), gold=True)); p.drawEllipse(QPointF(500, 430), 22, 22)
    return G(back, front, 380, 252, 128, 872, 846, back_deco=bd, front_deco=fd, rim=0.9, back_dark=0.16)

def s_suspensa():
    back = rpoly([(110, 275), (890, 275), (890, 846), (110, 846)], [10, 10, 14, 14])
    front = std_front(110, 890, 365, 846, r=14)
    def bd(p, c):
        # aba plástica transparente
        tab = rr(560, 178, 210, 110, 16)
        p.setPen(QPen(QColor(255, 255, 255, 140), 3)); p.setBrush(QColor(255, 255, 255, 70)); p.drawPath(tab)
        p.setPen(Qt.NoPen); p.setBrush(QColor("#FFFFFF")); p.drawRoundedRect(QRectF(580, 198, 170, 46), 6, 6)
        p.setBrush(accent(c.base, 180, 0.6, 0.55)); p.drawRoundedRect(QRectF(580, 198, 170, 12), 4, 4)
        # haste metálica com ganchos
        rod = QPainterPath(); rod.moveTo(70, 330); rod.cubicTo(30, 330, 30, 262, 80, 262); rod.lineTo(920, 262)
        rod.cubicTo(970, 262, 970, 330, 930, 330)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 60), 22, Qt.SolidLine, Qt.RoundCap)); p.drawPath(QTransform().translate(0, 6).map(rod))
        p.setPen(QPen(QColor("#8E96A3"), 18, Qt.SolidLine, Qt.RoundCap)); p.drawPath(rod)
        p.setPen(QPen(QColor("#F2F4F7"), 6, Qt.SolidLine, Qt.RoundCap)); p.drawPath(QTransform().translate(0, -4).map(rod))
    return G(back, front, 365, 262, 110, 890, 846, back_deco=bd, rim=0.8, back_dark=0.14)

def s_clipe():
    back = std_back(90, 910, 200, 256, 370, 52, 846, r=26, rt=28)
    front = std_front(90, 910, 352, 846, r=24, rb=28)
    def fd(p, c):
        clip = QPainterPath()
        x, y = 205, 262
        clip.moveTo(x+40, y+170); clip.lineTo(x+40, y+40); clip.arcTo(QRectF(x, y, 80, 80), 0, 180)
        clip.lineTo(x, y+200); clip.arcTo(QRectF(x, y+160, 120, 120), 180, 180); clip.lineTo(x+120, y+60)
        clip.arcTo(QRectF(x+120-50, y+60-25, 50, 50), 0, 180)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 70), 20, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(QTransform().translate(4, 8).map(clip))
        p.setPen(QPen(QColor("#7C8594"), 17, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(clip)
        p.setPen(QPen(QColor("#EEF1F5"), 7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(QTransform().translate(-2, -2).map(clip))
    return G(back, front, 352, 256, 90, 910, 846, front_deco=fd, rim=1.0, back_dark=0.12)

def s_ziper():
    back = rpoly([(90, 235), (910, 235), (910, 846), (90, 846)], [46, 46, 40, 40])
    front = std_front(90, 910, 338, 846, r=26, rb=40)
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front); p.setPen(Qt.NoPen)
        p.setBrush(hsl_adj(c.darker, -0.05)); p.drawRect(QRectF(90, 338, 820, 44))
        tg = metal(QRectF(0, 350, 10, 22))
        for i, x in enumerate(range(110, 900, 18)):
            p.setBrush(tg); p.drawRoundedRect(QRectF(x, 349 + (6 if i % 2 else 0), 12, 16), 3, 3)
        p.restore()
        # cursor + puxador
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 70)); p.drawRoundedRect(QRectF(704, 342, 64, 150), 20, 20)
        p.setBrush(metal(QRectF(696, 334, 60, 50))); p.drawRoundedRect(QRectF(696, 334, 60, 52), 14, 14)
        pull = QRectF(706, 374, 40, 112)
        p.setBrush(metal(pull)); p.drawRoundedRect(pull, 18, 18)
        p.setBrush(hsl_adj(c.darker, -0.08)); p.drawRoundedRect(QRectF(716, 420, 20, 46), 10, 10)
    return G(back, front, 338, 238, 90, 910, 846, front_deco=fd, rim=0.8, back_dark=0.12)

def s_couro():
    back = std_back(100, 900, 214, 262, 352, 44, 846, r=34, rt=30)
    front = std_front(100, 900, 352, 846, r=34, rb=36)
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front)
        r2 = random.Random(3); p.setPen(Qt.NoPen)
        for _ in range(500):
            p.setBrush(with_alpha(QColor("black"), r2.uniform(0.03, 0.07)))
            p.drawEllipse(QPointF(r2.uniform(100, 900), r2.uniform(352, 846)), r2.uniform(2, 5), r2.uniform(2, 5))
        p.restore()
        st = rpoly([(126, 378), (874, 378), (874, 820), (126, 820)], 22)
        pen = QPen(with_alpha(hsl_adj(c.mid, +0.25), 0.8), 5, Qt.CustomDashLine, Qt.RoundCap); pen.setDashPattern([3, 3])
        p.setBrush(Qt.NoBrush); p.setPen(pen); p.drawPath(st)
        strap = rpoly([(690, 330), (790, 330), (790, 600), (690, 600)], [6, 6, 50, 50])
        soft_shadow(p, strap, 0, 8, 80, 4, 8)
        g = QLinearGradient(690, 0, 790, 0); g.setColorAt(0, hsl_adj(c.dark, -0.04)); g.setColorAt(0.5, c.dark); g.setColorAt(1, hsl_adj(c.dark, -0.08))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(strap)
        pen2 = QPen(with_alpha(hsl_adj(c.mid, +0.2), 0.7), 4, Qt.CustomDashLine); pen2.setDashPattern([3, 3]); p.setPen(pen2); p.setBrush(Qt.NoBrush)
        p.drawPath(rpoly([(704, 330), (776, 330), (776, 586), (704, 586)], [4, 4, 36, 36]))
        p.setPen(Qt.NoPen); p.setBrush(metal(QRectF(714, 520, 52, 52), gold=True)); p.drawEllipse(QPointF(740, 546), 26, 26)
        p.setBrush(QColor(0, 0, 0, 50)); p.drawEllipse(QPointF(740, 546), 10, 10)
    return G(back, front, 352, 262, 100, 900, 846, front_deco=fd, rim=0.7, back_dark=0.16, emblem_c=(420, 610))

def s_maleta():
    body = rr(90, 272, 820, 576, 42)
    handle = rr(355, 158, 290, 160, 64).subtracted(rr(405, 205, 190, 120, 34))
    back = union(body, handle)
    front = std_front(90, 910, 352, 848, r=30, rb=42)
    def bd(p, c):
        p.save(); p.setClipPath(handle); p.fillRect(QRectF(300, 150, 400, 180), QColor(0, 0, 0, 70)); p.restore()
    def fd(p, c):
        p.setPen(QPen(with_alpha(c.darker, 0.5), 5)); p.drawLine(QPointF(110, 372), QPointF(890, 372))
        for x in (270, 730):
            r = QRectF(x-38, 330, 76, 74)
            p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 70)); p.drawRoundedRect(r.translated(0, 7), 14, 14)
            p.setBrush(metal(r, gold=True)); p.drawRoundedRect(r, 14, 14)
            p.setBrush(QColor(0, 0, 0, 60)); p.drawRoundedRect(QRectF(x-16, 362, 32, 18), 6, 6)
    return G(back, front, 352, 260, 90, 910, 848, back_deco=bd, front_deco=fd, rim=0.9, back_dark=0.18)

def s_abas():
    back = std_back(90, 880, 200, 256, 370, 50, 846, r=24, rt=26)
    front = std_front(90, 880, 352, 846, r=22, rb=26)
    beh = []
    for i, y in enumerate((392, 532, 672)):
        beh.append((rr(830, y, 118, 112, 22), ("accent", 60 + i*110)))
    def fd(p, c):
        p.setPen(QPen(with_alpha(QColor("white"), 0.35), 6, Qt.SolidLine, Qt.RoundCap))
        for y in (392, 532, 672): p.drawLine(QPointF(900, y+30), QPointF(925, y+30))
    return G(back, front, 352, 256, 90, 880, 846, behind=beh, rim=1.0, back_dark=0.12)

def s_indice():
    back = rpoly([(90, 282), (910, 282), (910, 846), (90, 846)], [22, 22, 24, 24])
    front = std_front(90, 910, 382, 846, r=22, rb=24)
    def bd(p, c):
        for i, (x, y) in enumerate(((160, 196), (390, 214), (620, 232))):
            col = accent(c.base, 40 + i*100)
            sheet = union(rr(x, y, 200, 110, 22), rr(110, y+70, 780, 300, 14))
            p.save(); p.setClipRect(QRectF(0, 0, 1000, 450))
            soft_shadow(p, sheet, 0, -2, 50, 3, 6)
            g = QLinearGradient(0, y, 0, y+200); g.setColorAt(0, hsl_adj(col, +0.08)); g.setColorAt(1, hsl_adj(col, -0.06))
            p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(sheet)
            p.setBrush(QColor(255, 255, 255, 170)); p.drawRoundedRect(QRectF(x+40, y+26, 120, 26), 8, 8)
            p.restore()
    return G(back, front, 382, 282, 90, 910, 846, back_deco=bd, rim=1.0, back_dark=0.12)

def s_etiqueta():
    back = std_back(95, 905, 200, 256, 380, 50, 846, r=24, rt=26)
    front = std_front(95, 905, 352, 846, r=22, rb=26)
    def fd(p, c):
        fr = QRectF(345, 430, 310, 130)
        soft_shadow(p, rr(345, 430, 310, 130, 14), 0, 6, 60, 3, 5)
        p.setPen(Qt.NoPen); p.setBrush(metal(fr)); p.drawRoundedRect(fr, 14, 14)
        p.setBrush(QColor("#FFFDF7")); p.drawRoundedRect(fr.adjusted(16, 16, -16, -16), 6, 6)
        p.setPen(QPen(QColor(110, 120, 140, 150), 8, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(385, 480), QPointF(615, 480)); p.drawLine(QPointF(385, 515), QPointF(540, 515))
        p.setPen(Qt.NoPen); p.setBrush(QColor("#6B7280"))
        for x in (360, 640): p.drawEllipse(QPointF(x, 495), 6, 6)
    return G(back, front, 352, 256, 95, 905, 846, front_deco=fd, rim=1.0, back_dark=0.12, emblem_c=(500, 700))

def s_cadeado():
    back = std_back(95, 905, 200, 256, 380, 50, 846, r=26, rt=28)
    front = std_front(95, 905, 352, 846, r=24, rb=28)
    def fd(p, c):
        cx, cy = 760, 400
        sh = QPainterPath(); sh.moveTo(cx-48, cy+10); sh.lineTo(cx-48, cy-40); sh.arcTo(QRectF(cx-48, cy-88, 96, 96), 180, -180); sh.lineTo(cx+48, cy+10)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 60), 26, Qt.SolidLine, Qt.FlatCap)); p.drawPath(QTransform().translate(3, 6).map(sh))
        p.setPen(QPen(QColor("#8E96A3"), 22, Qt.SolidLine, Qt.FlatCap)); p.drawPath(sh)
        p.setPen(QPen(QColor("#F1F3F6"), 7, Qt.SolidLine, Qt.FlatCap)); p.drawPath(QTransform().translate(-5, -3).map(sh))
        body = QRectF(cx-80, cy, 160, 130)
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 70)); p.drawRoundedRect(body.translated(3, 9), 24, 24)
        p.setBrush(metal(body, gold=True)); p.drawRoundedRect(body, 24, 24)
        p.setBrush(QColor(60, 45, 20, 200)); p.drawEllipse(QPointF(cx, cy+52), 15, 15)
        kp = QPolygonF([QPointF(cx-8, cy+56), QPointF(cx+8, cy+56), QPointF(cx+5, cy+95), QPointF(cx-5, cy+95)]); p.drawPolygon(kp)
    return G(back, front, 352, 256, 95, 905, 846, front_deco=fd, rim=1.0, back_dark=0.12, emblem_c=(440, 620))

def s_plastica():
    back = std_back(95, 905, 200, 256, 380, 50, 846, r=24, rt=26)
    win = rr(170, 420, 660, 260, 30)
    front = std_front(95, 905, 352, 846, r=22, rb=26).subtracted(win)
    def fd(p, c):
        p.save(); p.setClipPath(win); p.setPen(Qt.NoPen)
        p.fillRect(QRectF(170, 420, 660, 260), QColor(255, 255, 255, 40))
        for x0, w in ((260, 60), (360, 22), (600, 40)):
            sh = QPolygonF([QPointF(x0, 420), QPointF(x0+w, 420), QPointF(x0+w-140, 680), QPointF(x0-140, 680)])
            p.setBrush(QColor(255, 255, 255, 45)); p.drawPolygon(sh)
        p.restore()
        p.setBrush(Qt.NoBrush); p.setPen(QPen(QColor(255, 255, 255, 120), 4)); p.drawPath(win)
        p.setPen(QPen(QColor(0, 0, 0, 50), 3)); p.drawPath(QTransform().translate(0, 4).map(win))
    return G(back, front, 352, 256, 95, 905, 846, front_deco=fd, rim=1.0, back_dark=0.12, emblem_c=(500, 765))

# ============================================================== MODERNAS

def s_fluent():
    back = rpoly([(70, 190), (378, 190), (462, 252), (930, 252), (930, 852), (70, 852)], [60, 70, 70, 60, 60, 60])
    front = rpoly([(70, 392), (560, 392), (628, 344), (930, 344), (930, 852), (70, 852)], [46, 48, 48, 46, 60, 60])
    return G(back, front, 344, 252, 70, 930, 852, rim=1.0, back_dark=0.12)

def superellipse(cx, cy, a, b, n=4.5, steps=160):
    path = QPainterPath()
    for i in range(steps+1):
        t = 2*math.pi*i/steps; ct, st = math.cos(t), math.sin(t)
        x = cx + a*math.copysign(abs(ct)**(2/n), ct); y = cy + b*math.copysign(abs(st)**(2/n), st)
        path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
    path.closeSubpath(); return path

def s_squircle():
    tab = rr(140, 150, 270, 110, 46)
    back = union(superellipse(500, 520, 410, 340), tab)
    front = superellipse(500, 650, 410, 210, n=4.2)
    return G(back, front, 440, 230, 90, 910, 860, rim=1.1, back_dark=0.12)

def s_capsula():
    back = union(rr(90, 255, 820, 556, 278), rr(165, 190, 300, 150, 70))
    front = rr(90, 420, 820, 391, 195)
    return G(back, front, 420, 255, 120, 880, 811, rim=1.0, back_dark=0.13)

def s_linha():
    back = std_back(110, 890, 220, 272, 380, 48, 830, r=40, rt=34)
    front = std_front(110, 890, 372, 830, r=36, rb=40)
    def bd(p, c):
        p.setBrush(Qt.NoBrush); p.setPen(QPen(c.line, 30, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(c.geo.back)
    def fd(p, c):
        p.setBrush(Qt.NoBrush); p.setPen(QPen(c.line, 30, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(c.geo.front)
    return G(back, front, 372, 272, 110, 890, 830, back_deco=bd, front_deco=fd, fill="pale", rim=0.0, back_dark=0.04, no_gloss=True)

def _edge_front(top_pts, L, R, bottom, rc=26, rb=28):
    pts = list(top_pts) + [(R, bottom), (L, bottom)]
    radii = [rc] + [0.01]*(len(top_pts)-2) + [rc, rb, rb]
    return rpoly(pts, radii)

def s_onda():
    back = std_back(90, 910, 200, 255, 370, 52, 846, r=26, rt=28)
    top = [(90+i*820/80, 372 + 16*math.sin(i/80*2*math.pi*3)) for i in range(81)]
    front = _edge_front(top, 90, 910, 846)
    return G(back, front, 360, 255, 90, 910, 846, rim=1.1, back_dark=0.12)

def s_curva():
    back = std_back(90, 910, 198, 254, 370, 52, 846, r=28, rt=30)
    top = bezier_pts((90, 430), (360, 300), (640, 460), (910, 340), 60)
    front = _edge_front(top, 90, 910, 846, rc=30, rb=30)
    return G(back, front, 380, 254, 90, 910, 846, rim=1.2, back_dark=0.12)

def s_chanfrada():
    back = rpoly([(132, 204), (362, 204), (404, 246), (868, 246), (910, 288), (910, 804), (868, 846), (132, 846), (90, 804), (90, 246)], 5)
    front = rpoly([(132, 360), (868, 360), (910, 402), (910, 804), (868, 846), (132, 846), (90, 804), (90, 402)], 5)
    def fd(p, c):
        p.setBrush(Qt.NoBrush); p.setPen(QPen(with_alpha(QColor("white"), 0.35), 4))
        p.drawPath(rpoly([(146, 380), (854, 380), (890, 416), (890, 790), (854, 826), (146, 826), (110, 790), (110, 416)], 3))
        p.setPen(QPen(with_alpha(QColor("white"), 0.55), 10, Qt.SolidLine, Qt.FlatCap)); p.drawLine(QPointF(160, 400), QPointF(260, 400))
    return G(back, front, 360, 246, 90, 910, 846, front_deco=fd, rim=0.8, back_dark=0.14)

def s_dupla():
    back = std_back(95, 905, 200, 256, 380, 50, 846, r=30, rt=30)
    front = std_front(95, 905, 352, 846, r=28, rb=30)
    def fd(p, c):
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(with_alpha(QColor("white"), 0.55), 5)); p.drawPath(std_front(122, 878, 378, 820, r=18))
        p.setPen(QPen(with_alpha(c.darker, 0.45), 4)); p.drawPath(std_front(142, 858, 398, 800, r=12))
    return G(back, front, 352, 256, 95, 905, 846, front_deco=fd, rim=1.0, back_dark=0.12)

# ============================================================ DIVERTIDAS

def _cartoon(p, path, c):
    p.setBrush(Qt.NoBrush); p.setPen(QPen(c.darker, 22, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(path)

def s_bolha():
    back = rpoly([(88, 222), (430, 222), (506, 282), (912, 282), (912, 846), (88, 846)], [100, 70, 70, 110, 150, 150])
    front = rpoly([(62, 412), (938, 412), (938, 856), (62, 856)], [110, 110, 160, 160])
    def bd(p, c): _cartoon(p, c.geo.back, c)
    def fd(p, c):
        _cartoon(p, c.geo.front, c)
        p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 200))
        p.save(); p.translate(190, 500); p.rotate(-20); p.drawEllipse(QPointF(0, 0), 62, 30); p.restore()
        p.drawEllipse(QPointF(290, 470), 16, 16)
    return G(back, front, 412, 282, 88, 912, 856, back_deco=bd, front_deco=fd, rim=0.4, back_dark=0.10)

def s_nuvem():
    cloud = union(circle(185, 285, 68), circle(285, 232, 92), circle(392, 268, 70), rr(120, 260, 360, 90, 40))
    back = union(rr(86, 278, 828, 574, 42), cloud)
    front = std_front(86, 914, 388, 852, r=40, rb=44)
    return G(back, front, 388, 278, 86, 914, 852, rim=1.1, back_dark=0.12)

def s_laco():
    back = std_back(95, 905, 200, 256, 380, 50, 846, r=28, rt=28)
    front = std_front(95, 905, 352, 846, r=26, rb=28)
    def fd(p, c):
        h = c.base.getHslF()[0]
        rib = QColor("#F4B83A") if (h >= 0 and (h < 0.06 or h > 0.88)) else QColor("#E53E5A")
        p.save(); p.setClipPath(c.geo.front); p.setPen(Qt.NoPen)
        g = QLinearGradient(600, 0, 690, 0); g.setColorAt(0, hsl_adj(rib, -0.08)); g.setColorAt(0.5, hsl_adj(rib, +0.08)); g.setColorAt(1, hsl_adj(rib, -0.1))
        p.setBrush(QColor(0, 0, 0, 50)); p.drawRect(QRectF(606, 352, 90, 500))
        p.setBrush(g); p.drawRect(QRectF(600, 352, 90, 500)); p.restore()
        cx, cy = 645, 372
        loopL = QPainterPath(); loopL.moveTo(cx, cy); loopL.cubicTo(cx-170, cy-150, cx-200, cy+60, cx, cy); loopL.closeSubpath()
        loopR = QTransform().translate(2*cx, 0).scale(-1, 1).map(loopL)
        tails = QPainterPath(); tails.moveTo(cx-10, cy); tails.lineTo(cx-90, cy+150); tails.lineTo(cx-50, cy+140); tails.lineTo(cx-30, cy+170); tails.lineTo(cx+5, cy)
        tails.moveTo(cx+10, cy); tails.lineTo(cx+90, cy+140); tails.lineTo(cx+55, cy+138); tails.lineTo(cx+40, cy+165); tails.lineTo(cx-5, cy)
        bow = union(loopL, loopR, tails)
        soft_shadow(p, bow, 2, 8, 70, 4, 7)
        g2 = QLinearGradient(0, cy-120, 0, cy+160); g2.setColorAt(0, hsl_adj(rib, +0.12)); g2.setColorAt(1, hsl_adj(rib, -0.1))
        p.setPen(QPen(hsl_adj(rib, -0.2), 4)); p.setBrush(g2); p.drawPath(bow)
        p.setPen(Qt.NoPen); p.setBrush(hsl_adj(rib, -0.06)); p.drawRoundedRect(QRectF(cx-26, cy-30, 52, 60), 16, 16)
    return G(back, front, 352, 256, 95, 905, 846, front_deco=fd, rim=1.0, back_dark=0.12, emblem_c=(350, 620))

def s_tag():
    shape = rpoly([(205, 262), (912, 262), (912, 846), (205, 846), (78, 706), (78, 402)], [18, 32, 32, 18, 34, 34])
    tab = rr(600, 200, 260, 120, 26)
    hole = circle(160, 554, 30)
    back = union(shape, tab).subtracted(hole)
    front = below(shape, 392).subtracted(hole)
    def fd(p, c):
        p.setPen(QPen(with_alpha(c.darker, 0.6), 6)); p.setBrush(Qt.NoBrush); p.drawEllipse(QPointF(160, 554), 36, 36)
        s = QPainterPath(); s.moveTo(160, 520); s.cubicTo(60, 420, 20, 340, 70, 250)
        p.setPen(QPen(QColor(0, 0, 0, 50), 12, Qt.SolidLine, Qt.RoundCap)); p.drawPath(QTransform().translate(3, 6).map(s))
        p.setPen(QPen(QColor("#E8D5B0"), 9, Qt.SolidLine, Qt.RoundCap)); p.drawPath(s)
    return G(back, front, 392, 272, 205, 912, 846, front_deco=fd, rim=1.0, back_dark=0.12, emblem_c=(560, 620))

def heart(cx, cy, s):
    h = QPainterPath(); h.moveTo(cx, cy+0.9*s)
    h.cubicTo(cx-1.25*s, cy+0.1*s, cx-1.0*s, cy-0.95*s, cx-0.45*s, cy-0.9*s); h.cubicTo(cx-0.15*s, cy-0.88*s, cx, cy-0.6*s, cx, cy-0.45*s)
    h.cubicTo(cx, cy-0.6*s, cx+0.15*s, cy-0.88*s, cx+0.45*s, cy-0.9*s); h.cubicTo(cx+1.0*s, cy-0.95*s, cx+1.25*s, cy+0.1*s, cx, cy+0.9*s)
    h.closeSubpath(); return h

def s_coracao():
    back = union(rr(88, 282, 824, 570, 38), heart(272, 250, 116))
    front = std_front(88, 912, 392, 852, r=36, rb=40)
    return G(back, front, 392, 282, 88, 912, 852, rim=1.1, back_dark=0.12)

def s_gatinho():
    earL = rpoly([(130, 330), (190, 140), (370, 300)], [26, 30, 26])
    earR = QTransform().translate(1000, 0).scale(-1, 1).map(earL)
    back = union(rr(88, 270, 824, 582, 44), earL, earR)
    front = std_front(88, 912, 390, 852, r=40, rb=44)
    def bd(p, c):
        pink = mix(QColor("#FF9EC4"), c.mid, 0.25)
        inner = rpoly([(175, 300), (205, 200), (318, 300)], [14, 18, 14])
        p.setPen(Qt.NoPen); p.setBrush(pink); p.drawPath(inner)
        p.drawPath(QTransform().translate(1000, 0).scale(-1, 1).map(inner))
    return G(back, front, 390, 270, 88, 912, 852, back_deco=bd, rim=1.0, back_dark=0.12)

def s_empilhada():
    back = std_back(70, 840, 250, 300, 330, 46, 870, r=24, rt=26)
    front = std_front(70, 840, 400, 870, r=22, rb=26)
    sil = union(back, front)
    beh = [(QTransform().translate(90, -96).map(sil), 0.22), (QTransform().translate(45, -48).map(sil), 0.12)]
    def bd(p, c):
        p.setPen(QPen(with_alpha(QColor("white"), 0.25), 4)); p.setBrush(Qt.NoBrush)
    return G(back, front, 400, 300, 70, 840, 870, behind=beh, rim=1.0, back_dark=0.12)

# ============================================================= ESPECIAIS

def s_isometrica():
    T = QTransform(1, -0.12, 0, 1, 0, 60)   # cisalhamento: sobe para a direita
    backf = std_back(90, 740, 230, 280, 320, 44, 790, r=14, rt=16)
    frontf = std_front(90, 740, 400, 790, r=12)
    v = QTransform().translate(110, -50)
    back = T.map(v.map(backf))
    front = T.map(frontf)
    return G(back, front, 340, 220, 140, 880, 842, rim=1.2, back_dark=0.14,
             front_deco=_iso_deco(T), emblem_c=(420, 560))

def _iso_deco(T):
    def fd(p, c):
        p.save(); p.setTransform(T, True)
        side = rpoly([(740, 400), (850, 350), (850, 740), (740, 790)], 8)
        g = QLinearGradient(740, 0, 850, 0); g.setColorAt(0, hsl_adj(c.mid, -0.20)); g.setColorAt(1, hsl_adj(c.mid, -0.30))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(side)
        p.setPen(QPen(with_alpha(QColor("white"), 0.35), 4)); p.drawLine(QPointF(742, 404), QPointF(848, 354))
        p.restore()
    return fd

def s_inclinada():
    T = QTransform().translate(500, 520).rotate(-8).translate(-500, -520)
    back = T.map(std_back(110, 890, 214, 266, 375, 48, 820, r=34, rt=34))
    front = T.map(std_front(110, 890, 372, 820, r=32, rb=34))
    return G(back, front, 372, 266, 110, 890, 820, rim=1.0, back_dark=0.12, xform=T)

def s_neon():
    back = std_back(110, 890, 214, 266, 375, 48, 830, r=40, rt=36)
    front = std_front(110, 890, 372, 830, r=36, rb=40)
    def glow(p, path, col):
        p.setBrush(Qt.NoBrush)
        for w, a in ((46, 0.06), (32, 0.10), (20, 0.20), (11, 0.55)):
            p.setPen(QPen(with_alpha(col, a), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(path)
        p.setPen(QPen(with_alpha(mix(col, QColor("white"), 0.65), 0.95), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.drawPath(path)
    def bd(p, c): glow(p, c.geo.back, c.neon)
    def fd(p, c): glow(p, c.geo.front, c.neon)
    return G(back, front, 372, 266, 110, 890, 830, back_deco=bd, front_deco=fd, fill="dark", rim=0.15, back_dark=0.02, no_gloss=True)

def s_acrilico():
    back = std_back(100, 900, 210, 262, 370, 48, 840, r=36, rt=34)
    front = std_front(100, 900, 362, 840, r=34, rb=36)
    def fd(p, c):
        p.save(); p.setClipPath(c.geo.front); p.setBrush(Qt.NoBrush)
        g = QLinearGradient(100, 362, 900, 840); g.setColorAt(0, QColor(255, 255, 255, 220)); g.setColorAt(0.5, QColor(255, 255, 255, 40)); g.setColorAt(1, QColor(0, 0, 0, 90))
        p.setPen(QPen(QBrush(g), 30)); p.drawPath(c.geo.front)
        p.setPen(QPen(QColor(255, 255, 255, 150), 4)); p.drawPath(std_front(120, 880, 382, 820, r=20))
        p.restore()
    return G(back, front, 362, 262, 100, 900, 840, front_deco=fd, rim=1.6, back_dark=0.12, force_glass=True)

def s_circular():
    back = union(circle(500, 520, 332), rr(232, 160, 236, 140, 46))
    front = below(circle(500, 520, 332), 452)
    return G(back, front, 452, 250, 200, 800, 852, rim=1.1, back_dark=0.12, emblem_c=(500, 660))

def s_hexagonal():
    hexb = rpoly([(70, 520), (285, 222), (715, 222), (930, 520), (715, 820), (285, 820)], 34)
    back = union(hexb, rpoly([(305, 168), (520, 168), (560, 240), (300, 240)], [24, 24, 10, 10]))
    front = rpoly([(135, 430), (865, 430), (930, 520), (715, 820), (285, 820), (70, 520)], [14, 14, 34, 34, 34, 34])
    return G(back, front, 430, 222, 160, 840, 820, rim=1.1, back_dark=0.13, emblem_c=(500, 610))

def s_empe():
    back = std_back(232, 768, 118, 172, 420, 44, 872, r=28, rt=28)
    front = std_front(232, 768, 300, 872, r=26, rb=28)
    return G(back, front, 300, 172, 232, 768, 872, rim=1.0, back_dark=0.12, emblem_c=(500, 600))

def s_leque():
    back = std_back(150, 850, 222, 268, 372, 46, 840, r=24, rt=26)
    front = rpoly([(48, 472), (952, 472), (882, 852), (118, 852)], [26, 26, 30, 30])
    def bd(p, c):
        p.save(); p.setClipRect(QRectF(0, 0, 1000, 540))
        for ang, col in ((-16, "#E9EEF5"), (14, "#F3F6FA"), (0, "#FFFFFF")):
            p.save(); p.translate(500, 820); p.rotate(ang); p.translate(-500, -820)
            r = QRectF(300, 150, 400, 600)
            p.setPen(QPen(QColor(0, 0, 0, 35), 3)); p.setBrush(QColor(col)); p.drawRoundedRect(r, 10, 10)
            p.setPen(QPen(QColor(120, 140, 165, 90), 8, Qt.SolidLine, Qt.RoundCap))
            for i, fr in enumerate((0.7, 0.85, 0.6, 0.78)):
                p.drawLine(QPointF(340, 200+i*36), QPointF(340+320*fr, 200+i*36))
            p.restore()
        p.restore()
    return G(back, front, 472, 268, 150, 850, 852, back_deco=bd, rim=1.0, back_dark=0.18, back_deco_late=True)

# ------------------------------------------------------------- registro

CATEGORIES = ["Clássicas", "Modernas", "Retrô", "Escritório", "Divertidas", "Especiais"]

# (id, nome, categoria, função)   — os 7 originais ficam em folder_core.geometry
EXTRA = [
    ("xp", "Windows XP", "Retrô", s_xp),
    ("vista", "Vista / Aero", "Retrô", s_vista),
    ("pautada", "Retrô pautada", "Retrô", s_pautada),
    ("pixel", "Pixel art", "Retrô", s_pixel),
    ("kraft", "Kraft rasgada", "Retrô", s_kraft),
    ("origami", "Origami", "Retrô", s_origami),
    ("envelope", "Envelope pardo", "Retrô", s_envelope),
    ("cordao", "Com cordão", "Retrô", s_cordao),
    ("elastico", "Com elástico", "Escritório", s_elastico),
    ("caixa", "Caixa de arquivo", "Escritório", s_caixa),
    ("sanfonada", "Sanfonada", "Escritório", s_sanfonada),
    ("suspensa", "Suspensa", "Escritório", s_suspensa),
    ("clipe", "Com clipe", "Escritório", s_clipe),
    ("ziper", "Com zíper", "Escritório", s_ziper),
    ("couro", "Portfólio de couro", "Escritório", s_couro),
    ("maleta", "Maleta", "Escritório", s_maleta),
    ("abas", "Abas coloridas", "Escritório", s_abas),
    ("indice", "Índice (divisórias)", "Escritório", s_indice),
    ("etiqueta", "Com etiqueta", "Escritório", s_etiqueta),
    ("cadeado", "Com cadeado", "Escritório", s_cadeado),
    ("plastica", "Janela plástica", "Escritório", s_plastica),
    ("fluent", "Fluent", "Modernas", s_fluent),
    ("squircle", "Squircle", "Modernas", s_squircle),
    ("capsula", "Cápsula", "Modernas", s_capsula),
    ("linha", "Ícone de linha", "Modernas", s_linha),
    ("onda", "Ondulada", "Modernas", s_onda),
    ("curva", "Curva", "Modernas", s_curva),
    ("chanfrada", "Chanfrada", "Modernas", s_chanfrada),
    ("dupla", "Moldura dupla", "Modernas", s_dupla),
    ("bolha", "Bolha cartoon", "Divertidas", s_bolha),
    ("nuvem", "Nuvem", "Divertidas", s_nuvem),
    ("laco", "Com laço", "Divertidas", s_laco),
    ("tag", "Etiqueta de mala", "Divertidas", s_tag),
    ("coracao", "Coração", "Divertidas", s_coracao),
    ("gatinho", "Gatinho", "Divertidas", s_gatinho),
    ("empilhada", "Empilhada", "Divertidas", s_empilhada),
    ("isometrica", "Isométrica 3D", "Especiais", s_isometrica),
    ("inclinada", "Inclinada", "Especiais", s_inclinada),
    ("neon", "Neon", "Especiais", s_neon),
    ("acrilico", "Acrílico", "Especiais", s_acrilico),
    ("circular", "Circular", "Especiais", s_circular),
    ("hexagonal", "Hexagonal", "Especiais", s_hexagonal),
    ("empe", "Em pé (vertical)", "Especiais", s_empe),
    ("leque", "Em leque", "Especiais", s_leque),
]
EXTRA_FUNCS = {e[0]: e[3] for e in EXTRA}
ORIGINAL_CATS = {"classica": "Clássicas", "larga": "Clássicas", "aberta": "Clássicas", "moderna": "Modernas",
                 "mac": "Modernas", "minimal": "Modernas", "fofa": "Divertidas"}

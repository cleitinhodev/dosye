# -*- coding: utf-8 -*-
"""Dosye rendering core (folder icons).

Everything is vector-drawn (QPainterPath) in a 1000x1000 logical space and
composited in layers. Parameter keys/values are kept in Portuguese on purpose:
they are the on-disk preset format since Gerador de Pastas v1.

Núcleo de renderização. Todo o desenho é vetorial (QPainterPath) num espaço lógico de 1000x1000
unidades, renderizado com antialiasing num QImage e composto em camadas:

    brilho externo -> sombra projetada -> painel traseiro (+ papéis
    + imagem "saindo") -> sombra de contato -> frente -> emblema
"""
import math, struct, io, json, copy
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QImage, QPainter, QPainterPath, QColor, QLinearGradient,
                           QRadialGradient, QPen, QBrush, QTransform)
from PIL import Image, ImageFilter

U = 1000.0  # unidades lógicas

# --------------------------------------------------------------- estilos
STYLES = [
    ("classica",  "Clássica"),
    ("moderna",   "Moderna"),
    ("mac",       "Estilo Mac"),
    ("larga",     "Larga com Aba"),
    ("aberta",    "Aberta 3D"),
    ("minimal",   "Minimalista"),
    ("fofa",      "Fofa"),
]
STYLE_IDS = [s[0] for s in STYLES]

DEFAULTS = {
    "style": "moderna",
    "color1": "#F7B733",
    "color2": "#FC4A1A",
    "gradient": False,
    "grad_angle": 90,          # graus: 90 = vertical
    "light": 55,               # intensidade da luz 0..100
    "light_dir": -35,          # -100 (esq) .. 100 (dir)
    "glow": 0,                 # brilho externo 0..100
    "glow_color": "#FFD27A",
    "shadow": 45,              # intensidade sombra 0..100
    "shadow_dist": 30,         # distância 0..100
    "shadow_blur": 50,         # suavidade 0..100
    "gloss": 35,               # acabamento brilhante 0..100
    "inner": 45,               # sombreamento interno 0..100
    "border": False,
    "border_color": "#00000000",   # vazio = automático
    "border_width": 30,        # 0..100
    "papers": True,
    "mirror": False,
    "glass": False,
    "glass_amount": 55,
    "overlay_path": "",
    "overlay_mode": "nenhum",  # nenhum | dentro | frente
    "ov_x": 0, "ov_y": 0,       # -100..100
    "ov_scale": 100,           # 10..250 (%)
    "ov_rot": 0,               # -180..180
    "ov_shadow": True,
    "emblem_style": "original",  # original | gravado | branco
    # capa (imagem como superfície da pasta)
    "fill": "cor",             # cor | imagem
    "cover_path": "",
    "cover_area": "toda",      # toda | frente
    "cover_fit": "cobrir",     # cobrir | ajustar | lado
    "cover_x": 0, "cover_y": 0,  # -100..100
    "cover_zoom": 100,         # 10..400 (%)
    "cover_tint": 0,           # 0..100
    "cover_blend": "suave",    # suave | multiplicar | sobrepor | luz | tela
    "cover_back_dark": 35,     # 0..100
}
COVER_BLENDS = [("suave", "Normal"), ("multiplicar", "Multiplicar"), ("sobrepor", "Sobrepor"),
                ("luz", "Luz suave"), ("tela", "Clarear (tela)")]
COVER_FITS = [("cobrir", "Cobrir"), ("ajustar", "Ajustar"), ("lado", "Lado a lado")]

def default_params():
    return copy.deepcopy(DEFAULTS)

# ---------------------------------------------------------- utilidades

def qc(s):
    c = QColor(s)
    return c if c.isValid() else QColor("#888888")

def hsl_adj(c, dl=0.0, ds=0.0, a=None):
    """Ajusta luminosidade/saturação (deltas em 0..1)."""
    h, s, l, al = c.getHslF()
    if h < 0: h = 0
    l = min(1, max(0, l + dl)); s = min(1, max(0, s + ds))
    out = QColor.fromHslF(h, s, l, al if a is None else a)
    return out

def with_alpha(c, a):
    c = QColor(c); c.setAlphaF(max(0.0, min(1.0, a))); return c

def mix(c1, c2, t):
    return QColor.fromRgbF(c1.redF()*(1-t)+c2.redF()*t, c1.greenF()*(1-t)+c2.greenF()*t,
                           c1.blueF()*(1-t)+c2.blueF()*t, c1.alphaF()*(1-t)+c2.alphaF()*t)

def rpoly(pts, radii):
    """Polígono com cantos arredondados (curvas cúbicas suaves)."""
    n = len(pts)
    if not isinstance(radii, (list, tuple)):
        radii = [radii]*n
    path = QPainterPath()
    K = 0.5523
    for i in range(n):
        P = pts[i]; A = pts[i-1]; B = pts[(i+1) % n]
        la = math.hypot(A[0]-P[0], A[1]-P[1]); lb = math.hypot(B[0]-P[0], B[1]-P[1])
        r = min(radii[i], la*0.5, lb*0.5)
        p1 = (P[0]+(A[0]-P[0])/la*r, P[1]+(A[1]-P[1])/la*r)
        p2 = (P[0]+(B[0]-P[0])/lb*r, P[1]+(B[1]-P[1])/lb*r)
        if i == 0: path.moveTo(*p1)
        else: path.lineTo(*p1)
        c1 = (p1[0]+(P[0]-p1[0])*K, p1[1]+(P[1]-p1[1])*K)
        c2 = (p2[0]+(P[0]-p2[0])*K, p2[1]+(P[1]-p2[1])*K)
        path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*p2))
    path.closeSubpath()
    return path

# ------------------------------------------------------------ geometria

class Geo:
    """Geometria de um estilo: painel traseiro, frente, área dos papéis."""
    def __init__(self, back, front, front_top, body_top, left, right, bottom, papers=True):
        self.back = back; self.front = front; self.front_top = front_top
        self.body_top = body_top; self.left = left; self.right = right; self.bottom = bottom
        self.papers = papers
        # extras usados pelos formatos da v3 (shapes.py)
        self.behind = []; self.back_deco = None; self.front_deco = None; self.fill = None
        self.rim = None; self.back_dark = None; self.emblem_c = None; self.force_glass = False
        self.no_gloss = False; self.xform = None; self.back_deco_late = False

def geometry(style):
    if style == "classica":
        back = rpoly([(95,200),(385,200),(440,256),(905,256),(905,846),(95,846)], [20,26,26,20,20,20])
        front = rpoly([(95,350),(905,350),(905,846),(95,846)], 20)
        return Geo(back, front, 350, 256, 95, 905, 846)
    if style == "moderna":
        back = rpoly([(78,188),(372,188),(448,256),(922,256),(922,852),(78,852)], [56,58,58,56,56,56])
        front = rpoly([(78,362),(922,362),(922,852),(78,852)], [42,42,56,56])
        return Geo(back, front, 362, 256, 78, 922, 852)
    if style == "mac":
        back = rpoly([(84,212),(318,212),(370,262),(916,262),(916,840),(84,840)], [32,22,22,32,34,34])
        front = rpoly([(84,322),(916,322),(916,840),(84,840)], [30,30,34,34])
        return Geo(back, front, 322, 262, 84, 916, 840)
    if style == "larga":
        back = rpoly([(52,330),(566,330),(622,276),(948,276),(948,800),(52,800)], [24,30,30,24,26,26])
        front = rpoly([(52,408),(948,408),(948,800),(52,800)], [22,22,26,26])
        return Geo(back, front, 408, 330, 52, 948, 800)
    if style == "aberta":
        back = rpoly([(128,196),(392,196),(446,250),(872,250),(872,846),(128,846)], [24,28,28,24,20,20])
        front = rpoly([(36,452),(964,452),(894,852),(106,852)], [26,26,30,30])
        return Geo(back, front, 452, 250, 128, 872, 852)
    if style == "minimal":
        back = rpoly([(108,236),(392,236),(436,282),(892,282),(892,822),(108,822)], [6,4,4,6,6,6])
        front = rpoly([(108,372),(892,372),(892,822),(108,822)], 6)
        return Geo(back, front, 372, 282, 108, 892, 822)
    if style == "fofa":
        back = rpoly([(92,196),(414,196),(486,262),(908,262),(908,858),(92,858)], [84,60,60,90,110,110])
        front = rpoly([(70,382),(930,382),(930,858),(70,858)], [76,76,120,120])
        return Geo(back, front, 382, 262, 70, 930, 858)
    from . import shapes
    if style in shapes.EXTRA_FUNCS:
        return shapes.EXTRA_FUNCS[style]()
    return geometry("moderna")

def style_flags(style):
    """Ajustes visuais por estilo."""
    return {
        "classica": dict(back_dark=0.13, rim=1.0),
        "moderna":  dict(back_dark=0.12, rim=0.9),
        "mac":      dict(back_dark=0.10, rim=1.6),
        "larga":    dict(back_dark=0.13, rim=1.0),
        "aberta":   dict(back_dark=0.20, rim=1.0),
        "minimal":  dict(back_dark=0.14, rim=0.25),
        "fofa":     dict(back_dark=0.11, rim=1.2),
    }.get(style, dict(back_dark=0.12, rim=1.0))

# --------------------------------------------------- QImage <-> PIL / blur

def new_layer(S):
    img = QImage(S, S, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    return img

def blur(img, radius):
    """Desfoque gaussiano em espaço pré-multiplicado (correto p/ cor e alfa)."""
    if radius <= 0.3:
        return img
    img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    w, h = img.width(), img.height()
    data = bytes(img.constBits())[: w*h*4]
    pil = Image.frombuffer("RGBA", (w, h), data, "raw", "RGBA", 0, 1)
    pil = pil.filter(ImageFilter.GaussianBlur(radius))
    out = QImage(pil.tobytes(), w, h, w*4, QImage.Format_ARGB32_Premultiplied)
    return out.copy()

def tinted(img, color):
    """Silhueta de img preenchida com uma cor (mantém o alfa)."""
    out = img.copy()
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), color)
    p.end()
    return out

def qimage_to_pil(img):
    img = img.convertToFormat(QImage.Format_RGBA8888)
    w, h = img.width(), img.height()
    return Image.frombuffer("RGBA", (w, h), bytes(img.constBits())[: w*h*4], "raw", "RGBA", 0, 1).copy()

def pil_to_qimage(pil):
    pil = pil.convert("RGBA")
    w, h = pil.size
    return QImage(pil.tobytes(), w, h, w*4, QImage.Format_RGBA8888).copy()

# ------------------------------------------------------------- render

_overlay_cache = {}
_mip_cache = {}
MAX_SIDE = 2048

def _read_image(path, max_side=MAX_SIDE):
    """Lê qualquer imagem (PNG/JPG/WebP/BMP/GIF...), respeitando a rotação EXIF e
    reduzindo imagens gigantes já na leitura (economiza memória e deixa a prévia rápida)."""
    from PySide6.QtGui import QImageReader
    img = QImage()
    try:
        r = QImageReader(path); r.setAutoTransform(True)
        sz = r.size()
        if sz.isValid() and max(sz.width(), sz.height()) > max_side:
            f = max_side / max(sz.width(), sz.height())
            r.setScaledSize(sz * f)
        img = r.read()
    except Exception:
        img = QImage()
    if img.isNull():   # alternativa: Pillow (WebP, TIFF, etc.)
        try:
            pil = Image.open(path)
            try:
                from PIL import ImageOps
                pil = ImageOps.exif_transpose(pil)
            except Exception:
                pass
            pil = pil.convert("RGBA")
            pil.thumbnail((max_side, max_side), Image.LANCZOS)
            img = pil_to_qimage(pil)
        except Exception:
            return None
    if img.isNull():
        return None
    if max(img.width(), img.height()) > max_side:
        img = img.scaled(max_side, max_side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return img.convertToFormat(QImage.Format_ARGB32_Premultiplied)

def load_overlay(path):
    """Carrega (com cache) uma imagem usada como PNG sobreposto ou como capa."""
    if not path:
        return None
    if path in _overlay_cache:
        return _overlay_cache[path]
    if path.startswith("embedded:"):
        return None
    img = _read_image(path)
    if img is None:
        return None
    _overlay_cache[path] = img
    return img

load_image = load_overlay

def set_overlay_image(key, qimg):
    _mip_cache.pop(key, None)
    img = qimg
    if max(img.width(), img.height()) > MAX_SIDE:
        img = img.scaled(MAX_SIDE, MAX_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    _overlay_cache[key] = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)

def mip(img, need_w):
    """Versão reduzida (cache) com largura >= need_w px, para desenhar rápido e sem serrilhado."""
    w = img.width()
    if need_w <= 0 or need_w*2 > w:
        return img
    key = img.cacheKey()
    levels = _mip_cache.setdefault(key, {})
    lvl = 1
    while w // (2**(lvl+1)) >= need_w and w // (2**(lvl+1)) >= 8:
        lvl += 1
    if lvl not in levels:
        if len(_mip_cache) > 64: _mip_cache.clear(); levels = _mip_cache.setdefault(key, {})
        levels[lvl] = img.scaled(max(1, w // 2**lvl), max(1, img.height() // 2**lvl), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return levels[lvl]

_BLEND_MODES = {
    "suave": QPainter.CompositionMode_SourceOver, "multiplicar": QPainter.CompositionMode_Multiply,
    "sobrepor": QPainter.CompositionMode_Overlay, "luz": QPainter.CompositionMode_SoftLight,
    "tela": QPainter.CompositionMode_Screen,
}

def cover_limits(P):
    """Limites (em unidades do slider, 0..100) de deslocamento da capa no modo 'cobrir'."""
    img = load_image(P.get("cover_path", ""))
    if img is None or P.get("cover_fit") != "cobrir":
        return 100.0, 100.0
    geo = geometry(P["style"])
    fr = geo.front.boundingRect(); ref = geo.back.boundingRect().united(fr) if P["cover_area"] == "toda" else fr
    iw, ih = img.width(), img.height(); rw, rh = ref.width(), ref.height()
    s = max(rw/iw, rh/ih) * max(0.05, P["cover_zoom"]/100.0)
    return (min(100.0, max(0.0, (iw*s-rw)/2)/(rw*0.5)*100), min(100.0, max(0.0, (ih*s-rh)/2)/(rh*0.5)*100))

def _paint_cover(p, P, img, clip, ref, ftop, fbot, k, darken=0.0):
    """Desenha a imagem de capa recortada no formato `clip`, mapeada no retângulo `ref`."""
    iw, ih = img.width(), img.height()
    rw, rh = ref.width(), ref.height()
    z = max(0.05, P["cover_zoom"]/100.0)
    p.save()
    p.setClipPath(clip, Qt.IntersectClip)
    fit = P["cover_fit"]
    if fit == "lado":
        s = rw*0.34/iw*z
        src = mip(img, int(iw*s*k*1.5))
        ss = s * iw / src.width()
        br = QBrush(src)
        br.setTransform(QTransform().translate(ref.left() + P["cover_x"]/100.0*rw*0.5, ref.top() + P["cover_y"]/100.0*rh*0.5).scale(ss, ss))
        p.fillRect(ref.adjusted(-20, -20, 20, 20), br)
    else:
        s = (max(rw/iw, rh/ih) if fit == "cobrir" else min(rw/iw, rh/ih)) * z
        w, h = iw*s, ih*s
        ox, oy = P["cover_x"]/100.0*rw*0.5, P["cover_y"]/100.0*rh*0.5
        if fit == "cobrir":   # no modo cobrir a imagem nunca deixa buracos
            mx, my = max(0.0, (w-rw)/2), max(0.0, (h-rh)/2)
            ox, oy = max(-mx, min(mx, ox)), max(-my, min(my, oy))
        cx = ref.center().x() + ox
        cy = ref.center().y() + oy
        src = mip(img, int(w*k*1.2))
        p.drawImage(QRectF(cx-w/2, cy-h/2, w, h), src)
    t = P["cover_tint"]/100.0
    if t > 0:
        p.setCompositionMode(_BLEND_MODES.get(P["cover_blend"], QPainter.CompositionMode_SourceOver))
        g = grad_for(ref, ftop, fbot, P["grad_angle"] if P["gradient"] else 90)
        p.setOpacity(p.opacity()*t)
        p.fillRect(ref.adjusted(-20, -20, 20, 20), g)
    if darken > 0:
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setOpacity(1.0)
        p.fillRect(ref.adjusted(-20, -20, 20, 20), QColor(0, 0, 0, int(255*min(1, darken))))
    p.restore()

def front_colors(P):
    c1 = qc(P["color1"])
    if P["gradient"]:
        return c1, qc(P["color2"])
    return hsl_adj(c1, +0.06, +0.02), hsl_adj(c1, -0.05)

def grad_for(rect, top, bot, angle):
    a = math.radians(angle)
    cx, cy = rect.center().x(), rect.center().y()
    r = max(rect.width(), rect.height()) * 0.5
    dx, dy = math.cos(a)*r, math.sin(a)*r
    g = QLinearGradient(cx-dx, cy-dy, cx+dx, cy+dy)
    g.setColorAt(0, top); g.setColorAt(1, bot)
    return g

def _painter(img, S):
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    p.scale(S/U, S/U)
    return p

def _draw_overlay(p, P, geo, img, mode):
    w = U * (0.52 if mode == "dentro" else 0.34) * P["ov_scale"]/100.0
    h = w * img.height()/max(1, img.width())
    if mode == "dentro":
        cx = 500 + P["ov_x"]*4.0
        cy = geo.front_top - h*0.30 + P["ov_y"]*4.0
    else:
        ec = geo.emblem_c or (500, (geo.front_top + geo.bottom)/2 + 8)
        if geo.emblem_c is not None and P.get("mirror"): ec = (U - ec[0], ec[1])
        cx = ec[0] + P["ov_x"]*4.0
        cy = ec[1] + P["ov_y"]*4.0
    k = p.worldTransform().m11()
    p.save()
    p.translate(cx, cy)
    p.rotate(P["ov_rot"])
    p.drawImage(QRectF(-w/2, -h/2, w, h), mip(img, int(w*k*1.3)))
    p.restore()

def render(P, S=512):
    """Renderiza a pasta e devolve um QImage SxS (ARGB32 premultiplicado)."""
    P = {**DEFAULTS, **P}
    st = P["style"]
    geo = geometry(st)
    fl = style_flags(st)
    if geo.rim is not None: fl = dict(back_dark=geo.back_dark, rim=geo.rim)
    k = S/U                                   # px por unidade
    mirror = QTransform(-1, 0, 0, 1, U, 0) if P["mirror"] else None
    if mirror is not None:
        geo.back = mirror.map(geo.back); geo.front = mirror.map(geo.front)
        geo.behind = [(mirror.map(pth), spec) for pth, spec in geo.behind]
    c1 = qc(P["color1"])
    ftop, fbot = front_colors(P)
    from . import shapes
    ctx = shapes.Ctx(P, geo, ftop, fbot, k)
    if geo.fill == "dark":      # neon: superfície quase preta com a cor no brilho
        ctx.neon = QColor.fromHslF(max(0.0, c1.getHslF()[0]), 1.0, 0.62)
        ftop, fbot = mix(ftop, QColor("#05060A"), 0.80), mix(fbot, QColor("#05060A"), 0.86)
    elif geo.fill == "pale":    # ícone de linha: preenchimento clarinho + traço na cor
        ctx.line = QColor(ctx.mid) if not P["gradient"] else grad_for(QRectF(0, 0, U, U), ftop, fbot, P["grad_angle"])
        ctx.line = QBrush(ctx.line)
        ftop, fbot = mix(ftop, QColor("white"), 0.86), mix(fbot, QColor("white"), 0.80)
    btop = hsl_adj(ftop, -fl["back_dark"], -0.02)
    bbot = hsl_adj(fbot, -fl["back_dark"]-0.04, -0.02)
    fr = geo.front.boundingRect(); br = geo.back.boundingRect()
    ov = load_overlay(P["overlay_path"]) if P["overlay_mode"] != "nenhum" else None
    cover = load_image(P["cover_path"]) if P["fill"] == "imagem" and P["cover_path"] else None
    cref = br.united(fr)
    light = P["light"]/100.0
    lx = 500 + P["light_dir"]*4.2

    # ---------- camada traseira (painel + papéis + imagem saindo)
    back = new_layer(S)
    p = _painter(back, S)
    p.setPen(Qt.NoPen)
    # painéis extras atrás de tudo (pastas empilhadas, abas coloridas...)
    for pth, spec in geo.behind:
        pb = pth.boundingRect()
        if isinstance(spec, tuple) and spec[0] == "accent":
            col = shapes.accent(c1, spec[1])
            p.setBrush(grad_for(pb, hsl_adj(col, +0.06), hsl_adj(col, -0.06), 90)); p.drawPath(pth)
        else:
            p.setBrush(grad_for(pb, hsl_adj(btop, -spec), hsl_adj(bbot, -spec), P["grad_angle"] if P["gradient"] else 90)); p.drawPath(pth)
            if cover is not None and P["cover_area"] == "toda":
                _paint_cover(p, P, cover, pth, cref, ftop, fbot, k, darken=0.15 + spec + 0.5*P["cover_back_dark"]/100.0)
        p.save(); p.setClipPath(pth)
        p.setPen(QPen(QBrush(_rim_grad(pb, 0.45*fl["rim"]*(0.35+light))), 7)); p.setBrush(Qt.NoBrush); p.drawPath(pth); p.restore()
        p.setPen(Qt.NoPen)
    p.setBrush(grad_for(br, btop, bbot, P["grad_angle"] if P["gradient"] else 90))
    p.drawPath(geo.back)
    if cover is not None and P["cover_area"] == "toda":
        _paint_cover(p, P, cover, geo.back, cref, ftop, fbot, k, darken=0.10 + 0.55*P["cover_back_dark"]/100.0)
    # luz suave no painel traseiro
    if light > 0:
        p.save(); p.setClipPath(geo.back)
        g = QRadialGradient(lx, br.top(), br.width()*0.75)
        g.setColorAt(0, with_alpha(QColor("white"), 0.30*light)); g.setColorAt(1, with_alpha(QColor("white"), 0))
        p.fillRect(br, g); p.restore()
    # aresta superior (aba) iluminada
    p.save(); p.setClipPath(geo.back)
    pen = QPen(QBrush(_rim_grad(br, 0.55*fl["rim"]*(0.35+light))), 7)
    p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPath(geo.back); p.restore()
    p.setPen(Qt.NoPen)
    if geo.back_deco is not None and not geo.back_deco_late:
        _deco(p, geo.back_deco, ctx, mirror)
    # interior escuro da pasta aberta
    if st == "aberta":
        p.save(); p.setClipPath(geo.back)
        g = QLinearGradient(0, geo.body_top, 0, geo.front_top)
        g.setColorAt(0, with_alpha(QColor(0, 0, 0), 0.0)); g.setColorAt(1, with_alpha(QColor(0, 0, 0), 0.28))
        p.fillRect(QRectF(0, geo.body_top, U, geo.front_top-geo.body_top+40), g); p.restore()
    # papéis
    if P["papers"]:
        _draw_papers(p, geo, P, k)
    if geo.back_deco is not None and geo.back_deco_late:
        _deco(p, geo.back_deco, ctx, mirror)
    p.end()
    if ov is not None and P["overlay_mode"] == "dentro":
        if P["ov_shadow"]:
            ol = new_layer(S); q = _painter(ol, S); _draw_overlay(q, P, geo, ov, "dentro"); q.end()
            sh = blur(tinted(ol, QColor(0, 0, 0, 120)), 10*k)
            q = QPainter(back); q.drawImage(0, int(6*k), sh); q.end()
        q = _painter(back, S); _draw_overlay(q, P, geo, ov, "dentro"); q.end()

    # ---------- sombra de contato (frente projetando sobre o que está atrás)
    fmask = new_layer(S); q = _painter(fmask, S); q.setPen(Qt.NoPen); q.setBrush(QColor("black")); q.drawPath(geo.front); q.end()
    inner = P["inner"]/100.0
    cs = blur(tinted(fmask, QColor(0, 0, 0, int(255*min(1, 0.25+0.55*inner)))), 16*k)
    q = QPainter(back); q.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    q.drawImage(0, -int(round(7*k)), cs); q.end()

    # ---------- frente
    front = new_layer(S)
    p = _painter(front, S); p.setPen(Qt.NoPen)
    glass = P["glass"] or geo.force_glass
    ga = P["glass_amount"]/100.0 if P["glass"] else 0.5
    if glass:
        p.save(); p.setClipPath(geo.front)
        p.resetTransform(); p.drawImage(0, 0, blur(back, 18*k)); p.restore()
        p.setOpacity(1.0 - 0.72*ga)
    p.setBrush(grad_for(fr, ftop, fbot, P["grad_angle"] if P["gradient"] else 90))
    p.drawPath(geo.front)
    if cover is not None:
        _paint_cover(p, P, cover, geo.front, cref if P["cover_area"] == "toda" else fr, ftop, fbot, k)
    p.setOpacity(1.0)
    p.save(); p.setClipPath(geo.front)
    if glass:   # tom leitoso do vidro fosco
        g = QLinearGradient(0, fr.top(), 0, fr.bottom())
        g.setColorAt(0, with_alpha(QColor("white"), 0.22*ga)); g.setColorAt(1, with_alpha(QColor("white"), 0.05*ga))
        p.fillRect(fr, g)
    # luz
    if light > 0:
        g = QRadialGradient(lx, fr.top()-40, fr.width()*0.85)
        g.setColorAt(0, with_alpha(QColor("white"), 0.42*light))
        g.setColorAt(0.45, with_alpha(QColor("white"), 0.12*light))
        g.setColorAt(1, with_alpha(QColor("white"), 0))
        p.fillRect(fr, g)
    # sombreamento interno: escurece a base + borda interna
    if inner > 0:
        g = QLinearGradient(0, fr.top(), 0, fr.bottom())
        g.setColorAt(0, with_alpha(QColor(0, 0, 0), 0))
        g.setColorAt(0.55, with_alpha(QColor(0, 0, 0), 0.04*inner))
        g.setColorAt(1, with_alpha(QColor(0, 0, 0), 0.30*inner))
        p.fillRect(fr, g)
        ib = QLinearGradient(0, fr.top(), 0, fr.bottom())
        ib.setColorAt(0, with_alpha(QColor(0, 0, 0), 0)); ib.setColorAt(0.6, with_alpha(QColor(0, 0, 0), 0.0))
        ib.setColorAt(1, with_alpha(QColor(0, 0, 0), 0.24*inner))
        p.setPen(QPen(QBrush(ib), 14)); p.setBrush(Qt.NoBrush); p.drawPath(geo.front); p.setPen(Qt.NoPen)
    # brilho (gloss): reflexo curvo na metade superior
    gloss = P["gloss"]/100.0 * (0.4 if geo.no_gloss else 1.0)
    if gloss > 0:
        gp = QPainterPath()
        top = fr.top()
        hgt = fr.height()*0.46
        gp.moveTo(fr.left()-10, top-10); gp.lineTo(fr.right()+10, top-10)
        gp.lineTo(fr.right()+10, top+hgt*0.55)
        gp.cubicTo(fr.right()-fr.width()*0.3, top+hgt*0.95, fr.left()+fr.width()*0.35, top+hgt*0.75, fr.left()-10, top+hgt*1.05)
        gp.closeSubpath()
        g = QLinearGradient(0, top, 0, top+hgt)
        g.setColorAt(0, with_alpha(QColor("white"), 0.34*gloss)); g.setColorAt(1, with_alpha(QColor("white"), 0.04*gloss))
        p.setBrush(g); p.drawPath(gp)
    # aresta superior iluminada (bisel)
    p.setPen(QPen(QBrush(_rim_grad(fr, 0.75*fl["rim"]*(0.4+0.6*max(light, gloss)))), 8 if st != "minimal" else 4))
    p.setBrush(Qt.NoBrush); p.drawPath(geo.front)
    p.restore()
    if geo.front_deco is not None:
        _deco(p, geo.front_deco, ctx, mirror)
    p.end()

    # ---------- borda
    if P["border"]:
        bc = qc(P["border_color"])
        if bc.alpha() == 0:
            bc = hsl_adj(c1, -0.30, a=0.95)
        bw = 2 + P["border_width"]*0.22
        for img_, path in ((back, geo.back), (front, geo.front)):
            q = _painter(img_, S); q.setPen(QPen(bc, bw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); q.setBrush(Qt.NoBrush)
            q.setClipPath(path); q.drawPath(path); q.end()

    # ---------- emblema (imagem na frente)
    if ov is not None and P["overlay_mode"] == "frente":
        _draw_emblem(front, P, geo, ov, S, k, ftop, fbot)

    # ---------- composição final
    body = new_layer(S)
    q = QPainter(body); q.drawImage(0, 0, back); q.drawImage(0, 0, front); q.end()
    out = new_layer(S)
    q = QPainter(out)
    if P["glow"] > 0:
        gl = blur(tinted(body, with_alpha(qc(P["glow_color"]), min(1, 0.35+0.65*P["glow"]/100))), (14+P["glow"]*0.45)*k)
        q.drawImage(0, 0, gl)
        if P["glow"] > 60: q.drawImage(0, 0, gl)
    if P["shadow"] > 0:
        sa = P["shadow"]/100.0
        dist = P["shadow_dist"]/100.0
        rad = (4 + P["shadow_blur"]*0.42 + dist*12) * k
        # sombra ambiente (curta e escura) + sombra projetada (longa e suave)
        amb = blur(tinted(body, QColor(0, 0, 0, int(255*min(1, 0.55*sa)))), max(1.0, 5*k))
        q.drawImage(0, int(round(4*k)), amb)
        sh = blur(tinted(body, QColor(0, 0, 0, int(255*min(1, 0.85*sa)))), rad)
        q.drawImage(int(round(dist*10*k)), int(round((6+dist*48)*k)), sh)
    q.drawImage(0, 0, body)
    q.end()
    return out

def _deco(p, fn, ctx, mirror):
    """Desenha os detalhes de um formato (espelhados junto quando a aba vai para a direita)."""
    p.save()
    if mirror is not None:
        p.setTransform(mirror, True)
        g = ctx.geo   # os caminhos já estão espelhados: desespelha para a função de detalhe
        saved = (g.back, g.front)
        g.back, g.front = mirror.map(g.back), mirror.map(g.front)
    try:
        fn(p, ctx)
    finally:
        if mirror is not None:
            g.back, g.front = saved
        p.restore()
        p.setPen(Qt.NoPen)

def _rim_grad(rect, alpha):
    g = QLinearGradient(0, rect.top(), 0, rect.top()+70)
    g.setColorAt(0, with_alpha(QColor("white"), min(1, alpha)))
    g.setColorAt(1, with_alpha(QColor("white"), 0))
    return g

def _draw_papers(p, geo, P, k):
    top = geo.body_top + 34
    L, R = geo.left + 70, geo.right - 70
    if geo.right - geo.left > 850:
        L += 10; R -= 10
    sheets = [(-1.6, QColor("#E9EEF3"), 26), (1.1, QColor("#FFFFFF"), 0)]
    p.save()
    if geo.xform is not None: p.setTransform(geo.xform, True)
    p.setClipRect(QRectF(0, 0, U, geo.front_top + 60))
    for ang, col, dy in sheets:
        p.save()
        p.translate(500, top+dy+300); p.rotate(ang); p.translate(-500, -(top+dy+300))
        rr = QRectF(L, top+dy, R-L, geo.bottom-top)
        g = QLinearGradient(0, rr.top(), 0, rr.top()+200)
        g.setColorAt(0, col); g.setColorAt(1, col.darker(106))
        p.setPen(QPen(QColor(0, 0, 0, 28), 2)); p.setBrush(g)
        p.drawRoundedRect(rr, 10, 10)
        p.restore()
    # linhas de texto na folha da frente
    p.setPen(QPen(QColor(120, 140, 160, 70), 6, Qt.SolidLine, Qt.RoundCap))
    y = top + 34
    for i, frac in enumerate((0.55, 0.78, 0.66)):
        p.drawLine(QPointF(L+50, y+i*28), QPointF(L+50+(R-L-100)*frac, y+i*28))
    p.restore()

def _draw_emblem(front, P, geo, ov, S, k, ftop, fbot):
    lay = new_layer(S); q = _painter(lay, S); _draw_overlay(q, P, geo, ov, "frente"); q.end()
    style = P["emblem_style"]
    p = QPainter(front)
    if style == "gravado":
        clip = QPainterPath(geo.front); clip = QTransform().scale(S/U, S/U).map(clip); p.setClipPath(clip)
        mid = mix(ftop, fbot, 0.5)
        dark = tinted(lay, with_alpha(hsl_adj(mid, -0.22, -0.05), 0.78))
        hi = tinted(lay, with_alpha(hsl_adj(mid, +0.22), 0.55))
        p.drawImage(0, int(round(3*k)) or 1, hi)
        p.drawImage(0, 0, dark)
    elif style == "branco":
        if P["ov_shadow"]:
            p.drawImage(0, int(round(5*k)), blur(tinted(lay, QColor(0, 0, 0, 90)), 8*k))
        p.drawImage(0, 0, tinted(lay, QColor(255, 255, 255, 240)))
    else:
        if P["ov_shadow"]:
            p.drawImage(0, int(round(6*k)), blur(tinted(lay, QColor(0, 0, 0, 110)), 9*k))
        p.drawImage(0, 0, lay)
    p.end()

# ------------------------------------------------------------- exportação

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

def downscale(big, size):
    im = big.resize((size, size), Image.LANCZOS) if big.size[0] != size else big.copy()
    if size <= 48:
        im = im.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60 if size <= 24 else 40, threshold=0))
    return im

def render_sizes(P, sizes, base=1024):
    """Renderiza uma vez em alta resolução e reduz (Lanczos) para cada tamanho."""
    big = qimage_to_pil(render(P, max(base, max(sizes))))
    return [downscale(big, s) for s in sizes]

def render_size(P, size):
    return render_sizes(P, [size])[0]

def ico_bytes(images):
    """Monta um .ico: tamanhos < 256 em BMP 32 bits (máx. compatibilidade) e 256 em PNG."""
    entries = []
    for im in sorted(images, key=lambda i: i.size[0]):
        w, h = im.size
        if w >= 256:
            b = io.BytesIO(); im.save(b, "PNG", optimize=True); data = b.getvalue()
        else:
            px = im.convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "BGRA")
            mask_row = ((w + 31)//32)*4
            hdr = struct.pack("<IiiHHIIiiII", 40, w, h*2, 1, 32, 0, len(px)+mask_row*h, 0, 0, 0, 0)
            data = hdr + px + b"\x00"*(mask_row*h)
        entries.append((w, h, data))
    out = io.BytesIO()
    out.write(struct.pack("<HHH", 0, 1, len(entries)))
    offset = 6 + 16*len(entries)
    for w, h, data in entries:
        out.write(struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    for _, _, data in entries:
        out.write(data)
    return out.getvalue()

def export_ico(P, path, sizes=None):
    sizes = sizes or ICO_SIZES
    with open(path, "wb") as f:
        f.write(ico_bytes(render_sizes(P, sizes)))

def export_png(P, path, size=512):
    render_size(P, size).save(path, "PNG")

def parse_ico(path):
    """Lê o diretório de um .ico (para verificação)."""
    d = open(path, "rb").read()
    _, typ, n = struct.unpack_from("<HHH", d, 0)
    res = []
    for i in range(n):
        w, h, _, _, planes, bpp, size, off = struct.unpack_from("<BBBBHHII", d, 6+16*i)
        kind = "PNG" if d[off:off+8] == b"\x89PNG\r\n\x1a\n" else "BMP"
        res.append((w or 256, h or 256, bpp, size, kind))
    return typ, res

# ------------------------------------------------------------- formatos v3
from . import shapes as _shapes
STYLES += [(e[0], e[1]) for e in _shapes.EXTRA]
STYLE_IDS = [s[0] for s in STYLES]
CATEGORIES = _shapes.CATEGORIES
STYLE_CATS = dict(_shapes.ORIGINAL_CATS); STYLE_CATS.update({e[0]: e[2] for e in _shapes.EXTRA})
STYLE_NAMES = dict(STYLES)

# Stable, language-independent category ids (used by the UI and translations).
CATEGORY_IDS = {"Clássicas": "classic", "Modernas": "modern", "Retrô": "retro",
                "Escritório": "office", "Divertidas": "fun", "Especiais": "special"}
CATEGORY_ORDER = [CATEGORY_IDS[c] for c in CATEGORIES]
STYLE_CAT_IDS = {sid: CATEGORY_IDS[c] for sid, c in STYLE_CATS.items()}

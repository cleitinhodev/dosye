# -*- coding: utf-8 -*-
"""Gera as capas de exemplo (texturas procedurais) — roda só na hora do build (usa numpy)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

W, H = 1024, 768
COVERS = [("galaxia", "Galáxia"), ("marmore", "Mármore"), ("aurora", "Aurora"),
          ("madeira", "Madeira"), ("synthwave", "Pôr do sol retrô"), ("granilite", "Granilite")]
rng = np.random.default_rng(7)

def noise(w, h, scale, seed):
    r = np.random.default_rng(seed)
    gw, gh = max(2, int(w/scale)+2), max(2, int(h/scale)+2)
    g = (r.random((gh, gw))*255).astype(np.uint8)
    im = Image.fromarray(g).resize((int(gw*scale), int(gh*scale)), Image.BICUBIC).crop((0, 0, w, h))
    return np.asarray(im, dtype=np.float32)/255.0

def fbm(w, h, base=256, octaves=6, seed=1):
    acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        acc += noise(w, h, max(2, base/2**o), seed+o)*amp; tot += amp; amp *= 0.5
    return acc/tot

def ramp(t, stops):
    t = np.clip(t, 0, 1); out = np.zeros(t.shape+(3,), np.float32)
    xs = [s[0] for s in stops]; cols = [np.array(s[1], np.float32) for s in stops]
    for c in range(3):
        out[..., c] = np.interp(t, xs, [cc[c] for cc in cols])
    return out

def to_img(a): return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")

def galaxia():
    n = fbm(W, H, 300, 7, 11); m = fbm(W, H, 180, 6, 31)
    t = np.clip((n-0.35)*1.9, 0, 1)
    a = ramp(t, [(0, (8, 6, 28)), (0.35, (40, 18, 90)), (0.6, (140, 40, 160)), (0.8, (240, 110, 170)), (1, (255, 220, 200))])
    a += ramp(np.clip((m-0.5)*2.5, 0, 1), [(0, (0, 0, 0)), (1, (30, 90, 200))])*0.8
    img = to_img(a)
    d = ImageDraw.Draw(img)
    for _ in range(900):
        x, y = rng.random()*W, rng.random()*H; r = rng.random()**6*2.4+0.3; b = int(150+rng.random()*105)
        d.ellipse((x-r, y-r, x+r, y+r), fill=(b, b, min(255, b+20)))
    glow = img.filter(ImageFilter.GaussianBlur(3))
    return Image.blend(img, glow, 0.25)

def marmore():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    n = fbm(W, H, 220, 7, 5)
    v = np.abs(np.sin((x*0.006 + y*0.004) + n*9.0))
    vein = np.clip(1 - v*7, 0, 1)**1.5
    fine = np.clip(1 - np.abs(np.sin((x*0.004 - y*0.007) + fbm(W, H, 120, 6, 9)*12))*14, 0, 1)
    base = ramp(fbm(W, H, 400, 4, 3), [(0, (236, 232, 228)), (1, (252, 250, 248))])
    gold = np.array((196, 156, 84), np.float32); grey = np.array((150, 150, 158), np.float32)
    a = base*(1-vein[..., None]*0.9) + gold*vein[..., None]*0.9
    a = a*(1-fine[..., None]*0.35) + grey*fine[..., None]*0.35
    return to_img(a)

def aurora():
    img = Image.new("RGB", (W, H), (12, 14, 40)); d = ImageDraw.Draw(img)
    for (cx, cy, r, col) in ((0.2, 0.3, 0.45, (124, 92, 255)), (0.75, 0.25, 0.4, (40, 200, 255)), (0.5, 0.8, 0.5, (255, 90, 170)),
                             (0.9, 0.85, 0.35, (255, 190, 90)), (0.1, 0.9, 0.3, (40, 230, 180))):
        d.ellipse(((cx-r)*W, (cy-r)*H*1.3, (cx+r)*W, (cy+r)*H*1.3), fill=col)
    img = img.filter(ImageFilter.GaussianBlur(120))
    a = np.asarray(img, np.float32)
    a += (fbm(W, H, 4, 1, 99)[..., None]-0.5)*10   # granulado sutil
    return to_img(a)

def madeira():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    n = fbm(W, H, 160, 6, 21)
    d = np.sqrt(((x-W*0.3)*0.25)**2 + ((y+H*1.2)*1.0)**2)*0.05 + n*6
    rings = (np.sin(d*2.2)*0.5+0.5)**2.2
    grain = fbm(W, H, 6, 3, 41)
    t = rings*0.65 + grain*0.25 + n*0.2
    return to_img(ramp(t, [(0, (92, 52, 26)), (0.5, (150, 92, 50)), (1, (206, 150, 96))]))

def synthwave():
    img = Image.new("RGB", (W, H)); a = np.zeros((H, W, 3), np.float32)
    t = np.linspace(0, 1, H)[:, None]
    sky = ramp(np.repeat(t, W, 1), [(0, (20, 8, 60)), (0.35, (110, 30, 140)), (0.58, (255, 90, 120)), (0.6, (40, 10, 70)), (1, (12, 4, 30))])
    img = to_img(sky); d = ImageDraw.Draw(img)
    cx, cy, R = W/2, H*0.45, 190
    sun = Image.new("L", (W, H), 0); ds = ImageDraw.Draw(sun); ds.ellipse((cx-R, cy-R, cx+R, cy+R), fill=255)
    for i in range(7):
        yy = cy + 20 + i*24; ds.rectangle((0, yy, W, yy+4+i*2), fill=0)
    ds.rectangle((0, H*0.6, W, H), fill=0)
    sg = ramp(np.repeat(np.linspace(0, 1, H)[:, None], W, 1)*1.0, [(0, (255, 240, 120)), (0.45, (255, 150, 80)), (0.6, (255, 60, 140)), (1, (255, 60, 140))])
    img = Image.composite(to_img(sg), img, sun)
    glow = Image.new("RGB", (W, H)); ImageDraw.Draw(glow).ellipse((cx-R*1.4, cy-R*1.4, cx+R*1.4, cy+R*1.4), fill=(255, 80, 150))
    img = Image.blend(img, Image.composite(glow.filter(ImageFilter.GaussianBlur(60)), img, Image.new("L", (W, H), 255)), 0.0)
    d = ImageDraw.Draw(img); hy = int(H*0.6)
    for i in range(1, 14):
        yy = hy + (H-hy)*(i/13)**1.8; d.line((0, yy, W, yy), fill=(255, 70, 200), width=2)
    for i in range(-14, 15):
        d.line((cx + i*14, hy, cx + i*150, H), fill=(255, 70, 200), width=2)
    return img.filter(ImageFilter.GaussianBlur(0.6))

def granilite():
    img = Image.new("RGB", (W, H), (244, 236, 224)); d = ImageDraw.Draw(img)
    cols = [(232, 120, 90), (60, 110, 120), (240, 190, 90), (30, 40, 60), (200, 160, 200), (120, 170, 140)]
    for _ in range(420):
        x, y = rng.random()*W, rng.random()*H; r = 4 + rng.random()**2.5*26
        n = int(rng.integers(4, 8)); ang0 = rng.random()*6.28
        pts = [(x+math.cos(ang0+i*6.28/n)*r*(0.6+rng.random()*0.5), y+math.sin(ang0+i*6.28/n)*r*(0.6+rng.random()*0.5)) for i in range(n)]
        d.polygon(pts, fill=cols[int(rng.integers(0, len(cols)))])
    return img

FUNCS = dict(galaxia=galaxia, marmore=marmore, aurora=aurora, madeira=madeira, synthwave=synthwave, granilite=granilite)

def generate(outdir):
    os.makedirs(outdir, exist_ok=True)
    for key, _ in COVERS:
        FUNCS[key]().save(os.path.join(outdir, f"capa_{key}.jpg"), quality=90)

if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "assets")

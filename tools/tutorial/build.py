"""Builds the standalone tutorial page:  OUT/index.html + OUT/assets/*.webp

    PYTHONPATH=src python tools/tutorial/build.py SHOTS_DIR OUT_DIR [--hero IMAGE] [--character IMAGE]

SHOTS_DIR = output of make_screenshots.py. UI labels and help texts are read from the app's locale
files, so the page always uses the real wording. Page-only texts live in page_strings.py.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from page_strings import S, WIN  # noqa: E402

LANG_ORDER = ["ht", "fr", "gcf", "mfe", "en", "pt_BR", "es", "de", "it", "pl", "tr", "ru", "ja", "zh_CN", "ko"]
SHOTS = ["main", "shapes", "colors", "effects", "cover", "png_coming_out", "emblem", "export", "apply",
         "repair", "settings", "about", "help"]
DESIGNS = ["design_hero", "design_emblem", "design_open"]
Q = 88


def webp(src, dst, max_w=None, q=Q):
    from PIL import Image
    im = Image.open(src)
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=q, method=6)
    return im.size


def process_help(body, loc, en):
    """<b>native label</b> -> <b>English label</b> (native label), using the real UI strings."""
    if loc is en:
        return body
    def norm(t):
        return re.sub(r"[\s…:.]+$", "", html.unescape(t).strip()).casefold()
    table = {}
    for k, v in loc.items():
        if k.startswith(("help.", "_", "msg.", "tip.", "shape.")) or k not in en or not isinstance(v, str):
            continue
        if len(v) > 60 or "{" in v:
            continue
        table.setdefault(norm(v), en[k])
    def rep(m):
        inner = m.group(1)
        e = table.get(norm(inner))
        if e and norm(e) != norm(inner):
            e = re.sub(r"…$", "", e)
            return f'<b>{html.escape(e)}</b> <span class="nat">({inner})</span>'
        return m.group(0)
    return re.sub(r"<b>(.*?)</b>", rep, body)


UI_KEYS = [
    "app.tagline", "shapes.title", "shapes.search", "hdr.surprise", "hdr.open", "hdr.save", "hdr.reset", "hdr.settings",
    "hdr.help", "hdr.about", "hdr.donate", "cat.all", "cat.classic", "cat.modern", "cat.retro", "cat.office", "cat.fun",
    "cat.special", "preview.title", "fill.title", "fill.color", "fill.image", "cover.choose", "cover.examples",
    "cover.apply_to", "cover.area_all", "cover.area_front", "fit.cobrir", "fit.ajustar", "fit.lado", "cover.zoom",
    "cover.tint", "cover.blend", "cover.back_dark", "color.main", "color.gradient", "color.second", "color.angle",
    "color.palette", "light.title", "light.intensity", "light.dir", "light.gloss", "light.glow", "shadow.title",
    "shadow.drop", "shadow.inner", "details.title", "details.papers", "details.mirror", "details.glass", "details.border",
    "png.title", "png.none", "png.inside", "png.front", "png.load", "png.scale", "png.rot", "png.shadow",
    "png.emblem_style", "emblem.original", "emblem.gravado", "emblem.branco", "export.ico", "export.png", "export.apply",
    "export.remove", "export.repair", "settings.title", "settings.language", "settings.animations", "settings.reduce",
    "settings.intensity", "settings.export", "settings.export_dir", "settings.png_size", "settings.ico_sizes",
    "settings.restore", "about.desc", "about.meaning", "about.site", "about.project", "about.donate", "about.license",
    "help.title", "help.shortcuts.title", "repair.title", "act.export_ico", "act.export_png", "act.open_preset",
    "act.save_preset", "act.surprise", "act.search", "act.settings", "act.help", "act.quit", "_language",
]
HELP_SECS = ["start", "shapes", "fill", "png", "effects", "export", "folder", "repair", "presets"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots"); ap.add_argument("out")
    ap.add_argument("--hero", help="hero background picture (default: bundled galaxy texture)")
    ap.add_argument("--character", help="decorative character picture (default: the cut-out made for the screenshots)")
    a = ap.parse_args()
    repo = os.path.abspath(os.path.join(HERE, "..", ".."))
    src_assets = os.path.join(repo, "src", "dosye", "assets")
    locdir = os.path.join(repo, "src", "dosye", "i18n", "locales")
    out_assets = os.path.join(a.out, "assets")
    if os.path.isdir(out_assets):
        shutil.rmtree(out_assets)
    os.makedirs(out_assets)

    sizes = {}
    for n in SHOTS:
        sizes[n] = webp(os.path.join(a.shots, n + ".png"), os.path.join(out_assets, f"shot-{n}.webp"))
    for n in DESIGNS:
        sizes[n] = webp(os.path.join(a.shots, n + ".png"), os.path.join(out_assets, n.replace("_", "-") + ".webp"), q=90)
    sizes["icon"] = webp(os.path.join(src_assets, "icons", "dosye_icon.png"), os.path.join(out_assets, "dosye-icon.webp"), 512, 90)
    shutil.copy(os.path.join(src_assets, "icons", "dosye_favicon.png"), os.path.join(out_assets, "favicon.png"))
    sizes["favicon"] = webp(os.path.join(src_assets, "icons", "dosye_favicon.png"), os.path.join(out_assets, "dosye-favicon.webp"), 256, 90)
    hero = a.hero or os.path.join(src_assets, "covers", "galaxia.jpg")
    sizes["hero"] = webp(hero, os.path.join(out_assets, "hero-bg.webp"), 1920, 84)
    char = a.character or os.path.join(a.shots, "character.png")
    if os.path.exists(char):
        sizes["character"] = webp(char, os.path.join(out_assets, "character.webp"), 900, 90)

    en = json.load(open(os.path.join(locdir, "en.json"), encoding="utf-8"))
    from dosye.ui.dialogs import SHORTCUTS
    data = {}
    for code in LANG_ORDER:
        loc = json.load(open(os.path.join(locdir, f"{code}.json"), encoding="utf-8"))
        ui = {k: loc.get(k, en.get(k, k)) for k in UI_KEYS}
        hp = {}
        for sec in HELP_SECS:
            hp[sec + ".title"] = loc.get(f"help.{sec}.title", en[f"help.{sec}.title"])
            hp[sec + ".body"] = process_help(loc.get(f"help.{sec}.body", en[f"help.{sec}.body"]), loc if code != "en" else en, en)
        data[code] = {"ui": ui, "help": hp, "page": S[code], "win": WIN[code]}
    en_ui = {k: en.get(k, k) for k in UI_KEYS}

    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    page = (tpl.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
               .replace("/*__EN_UI__*/{}", json.dumps(en_ui, ensure_ascii=False, separators=(",", ":")))
               .replace("/*__SIZES__*/{}", json.dumps({k: list(v) for k, v in sizes.items()}))
               .replace("/*__SHORTCUTS__*/[]", json.dumps(SHORTCUTS)))
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(page)
    tot = sum(os.path.getsize(os.path.join(out_assets, f)) for f in os.listdir(out_assets))
    print(f"index.html {os.path.getsize(os.path.join(a.out, 'index.html')) // 1024} KB, assets {tot // 1024} KB ({len(os.listdir(out_assets))} files)")


if __name__ == "__main__":
    main()

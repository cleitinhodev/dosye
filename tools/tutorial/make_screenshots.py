"""Renders the English screenshots used by the tutorial page and the README.

    QT_QPA_PLATFORM=offscreen PYTHONPATH=src python tools/tutorial/make_screenshots.py OUT_DIR \
        [--cover IMAGE] [--character IMAGE]

--cover      picture used as the folder cover (default: the bundled "synthwave" texture)
--character  picture used as the PNG coming out of the folder / emblem (default: the bundled moon).
             A picture without transparency gets its plain (white) background cut away.
Writes PNG files; tools/tutorial/build.py converts them to WebP.
"""
import argparse
import os
import sys
import tempfile
import time


def cutout(path, out_png):
    """Makes the flat background of *path* transparent (flood fill from the border), keeps real alpha."""
    from PIL import Image, ImageFilter, ImageChops
    im = Image.open(path).convert("RGBA")
    a = im.getchannel("A")
    if a.getextrema()[0] < 250:          # already has transparency
        im.save(out_png); return out_png, "kept original transparency"
    w, h = im.size
    rgb = im.convert("RGB")
    # sample the border colour
    border = [rgb.getpixel((x, 0)) for x in range(0, w, 7)] + [rgb.getpixel((x, h - 1)) for x in range(0, w, 7)] \
        + [rgb.getpixel((0, y)) for y in range(0, h, 7)] + [rgb.getpixel((w - 1, y)) for y in range(0, h, 7)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    # distance from the background colour
    diff = ImageChops.difference(rgb, Image.new("RGB", (w, h), bg)).convert("L")
    near = diff.point(lambda v: 255 if v < 26 else 0)
    # flood fill from every border pixel that is background -> region connected to the border
    mask = near.copy()
    seed_val = 128
    from PIL import ImageDraw
    for x in range(0, w, 3):
        for y in (0, h - 1):
            if mask.getpixel((x, y)) == 255:
                ImageDraw.floodfill(mask, (x, y), seed_val)
    for y in range(0, h, 3):
        for x in (0, w - 1):
            if mask.getpixel((x, y)) == 255:
                ImageDraw.floodfill(mask, (x, y), seed_val)
    bgmask = mask.point(lambda v: 255 if v == seed_val else 0)
    bgmask = bgmask.filter(ImageFilter.MaxFilter(3))          # eat the 1-px halo
    alpha = ImageChops.invert(bgmask).filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(ImageChops.multiply(alpha, a))
    bbox = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        im = im.crop(bbox)
    im.save(out_png)
    return out_png, f"background {bg} removed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--cover")
    ap.add_argument("--character")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    os.environ.setdefault("XDG_CONFIG_HOME", tempfile.mkdtemp(prefix="dosye_shots_cfg_"))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    app = QApplication([sys.argv[0]])
    app.setStyle("Fusion")
    from dosye import app as A, i18n
    from dosye.paths import asset
    from dosye.settings import Settings
    from dosye.core import render as fc
    A._palette(app)
    s = Settings(); s.data["language"] = "en"; A.resolve_language(s, "en"); A.apply_theme(app, s)
    from dosye.ui.main_window import MainWindow
    from dosye.ui.dialogs import SettingsDialog, AboutDialog, HelpDialog, RepairDialog
    from dosye.ui.widgets import Section

    cover = a.cover or asset("covers", "synthwave.jpg")
    char = a.character or asset("stickers", "lua.png")
    char_png, note = cutout(char, os.path.join(tempfile.mkdtemp(), "character.png"))
    print("character:", note)
    import shutil; shutil.copy(char_png, os.path.join(a.out, "character.png"))

    w = MainWindow(s); w.setWindowState(Qt.WindowNoState); w.resize(1366, 768); w.show()

    def settle(t=0.25):
        end = time.time() + t
        while time.time() < end:
            app.processEvents(); time.sleep(0.01)
        w._sync_ui(); app.processEvents()
        w.t_main.stop(); w.t_slow.stop(); w._render_main(); w._render_slow(); w.flush_thumbnails(); app.processEvents()

    def section(title_key):
        title = i18n.tr(title_key)
        from PySide6.QtWidgets import QLabel
        for sec in w.findChildren(Section):
            if any(l.text().strip() == title for l in sec.findChildren(QLabel)):
                return sec
        return None

    def scroll_to(title_key):
        sec = section(title_key)
        if sec is not None:
            sb = w.panel_scroll.verticalScrollBar()
            y = sec.mapTo(w.panel_scroll.widget(), sec.rect().topLeft()).y()
            sb.setValue(max(0, y - 6))
        settle()

    def shot(name, widget=None):
        p = os.path.join(a.out, name + ".png"); (widget or w).grab().save(p); print("saved", p)

    def hero_design():
        w.reset(); settle()
        w.style_btns["moderna"].click()
        w._load_cover_file(cover); w.set("cover_area", "toda"); w.set("cover_back_dark", 45)
        w._load_overlay_file(char_png); w.set("overlay_mode", "dentro")
        w.set("ov_scale", 118); w.set("ov_y", -6)
        w.set("glow", 45); w.set("glow_color", "#B18CFF"); w.set("gloss", 45); w.set("light", 60)
        w.set_color1("#5B3FD8"); w.set_color2("#C084FC")
        settle(0.4)

    # 1) main window: cover + character coming out
    hero_design()
    shot("main")
    scroll_to("fill.title"); shot("cover")
    scroll_to("png.title"); shot("png_coming_out")
    # big transparent renders of the design for the page
    for nm, size in (("design_hero", 512),):
        fc.render_size(w.P, size).save(os.path.join(a.out, nm + ".png"))

    # 2) emblem on a gradient folder
    w.reset(); settle()
    w.style_btns["classica"].click()
    w.set_color1("#3B2BB8"); w.set("gradient", True); w.set_color2("#B15CFF"); w.set("grad_angle", 120)
    w._load_overlay_file(char_png); w.set("overlay_mode", "frente"); w.set("emblem_style", "original")
    w.set("ov_scale", 95); w.set("glow", 35); w.set("glow_color", "#FFC93C"); w.set("glass", True)
    settle(0.4)
    scroll_to("png.title"); shot("emblem")
    fc.render_size(w.P, 512).save(os.path.join(a.out, "design_emblem.png"))
    scroll_to("fill.title"); shot("colors")

    # 3) light & shadow
    w.reset(); settle()
    w.style_btns["aberta"].click()
    w.set_color1("#FFC93C"); w.set("gradient", True); w.set_color2("#FF7A3C")
    w._load_overlay_file(char_png); w.set("overlay_mode", "dentro"); w.set("ov_scale", 105)
    w.set("glow", 70); w.set("glow_color", "#FFD27A"); w.set("gloss", 70); w.set("shadow", 70)
    w.set("light_dir", 40); w.set("border", True)
    settle(0.4)
    scroll_to("light.title"); shot("effects")
    fc.render_size(w.P, 512).save(os.path.join(a.out, "design_open.png"))

    # 4) shapes & categories
    w.reset(); settle()
    w.cat_btns["fun"].click(); w.style_btns["gatinho"].click()
    w.set_color1("#8B5CFF"); w.set("gradient", True); w.set_color2("#4CC9F0"); w.set("glow", 40)
    settle(0.4); shot("shapes")
    w.cat_btns["all"].click()

    # 5) export: real toast after exporting an .ico with every size
    hero_design()
    ico = os.path.join(tempfile.mkdtemp(), "folder.ico")
    sizes = s["ico_sizes"]
    fc.export_ico(w.P, ico, sizes)
    w.panel_scroll.verticalScrollBar().setValue(w.panel_scroll.verticalScrollBar().maximum())
    w.toast.show_message(i18n.tr("msg.ico_done", n=len(sizes), sizes=", ".join(map(str, sizes))), ico)
    settle(0.8); shot("export")

    # 6) apply toast (Windows wording)
    w.toast.show_message(i18n.tr("msg.apply_done_win"), os.path.dirname(ico)); settle(0.8); shot("apply")
    w.toast.hide(); settle()

    # 7) dialogs
    dlg = SettingsDialog(w, s); dlg.show(); settle(); dlg.adjustSize(); settle(); shot("settings", dlg); dlg.close()
    dlg = AboutDialog(w); dlg.show(); settle(); dlg.adjustSize(); settle(); shot("about", dlg); dlg.close()
    dlg = HelpDialog(w); dlg.resize(760, 640); dlg.show(); settle(); shot("help", dlg); dlg.close()
    # repair dialog over a fake pendrive with a few Dosye folders
    from dosye.system import foldericon as fi
    import io
    buf = io.BytesIO(); fc.render_size(w.P, 256).save(buf, "PNG")
    root = os.path.join(tempfile.mkdtemp(), "PENDRIVE")
    for i, nm in enumerate(("Photos", "Work/Reports", "Music", "Games/Saves", "Projects/Dosye")):
        d = os.path.join(root, nm); os.makedirs(d)
        if nm != "Music":
            open(os.path.join(d, f".dosye_icon_17000000{i}.png"), "wb").write(buf.getvalue())
    fi.repair_folder(os.path.join(root, "Photos"))
    dlg = RepairDialog(w, root); dlg.show(); t0 = time.time()
    while not dlg.is_done() and time.time() - t0 < 20:
        app.processEvents(); time.sleep(0.02)
    settle(); shot("repair", dlg); dlg.accept()
    print("done")
    os._exit(0)


if __name__ == "__main__":
    main()

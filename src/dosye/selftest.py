"""Automated self-test (used for releases and CI):  dosye --selftest OUT_DIR

Checks every shape exports a valid .ico, every language has every key, the UI
fits small screens in every language, presets old and new load, settings toggle
the animation clock, folder-icon integration works, and measures idle CPU.
Writes OUT_DIR/selftest.txt and screenshots. Exit code 0 = all good.
"""
import json
import os
import sys
import tempfile
import time
import traceback

from PySide6.QtCore import Qt, QTimer, QElapsedTimer
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtGui import QFont, QFontMetrics

from . import __version__, i18n
from .core import render as fc
from .system import folders, IS_WINDOWS, IS_LINUX
from .ui.effects import FX, clock


class Log:
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8"); self.fail = []

    def __call__(self, *a):
        line = " ".join(str(x) for x in a)
        self.f.write(line + "\n"); self.f.flush()

    def check(self, ok, what):
        self(("OK   " if ok else "FAIL ") + what)
        if not ok:
            self.fail.append(what)
        return ok


def _cpu_percent(app, seconds):
    t0 = time.process_time(); wall = QElapsedTimer(); wall.start()
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents(); time.sleep(0.005)
    return 100.0 * (time.process_time() - t0) / (wall.elapsed() / 1000.0)


def _overflow_buttons(root):
    """Buttons whose text needs more width than they have (would be clipped)."""
    out = []
    for b in root.findChildren(QPushButton):
        if not b.isVisible() or not b.text().strip():
            continue
        f = QFont(b.font())
        if b.isCheckable():
            f.setWeight(QFont.DemiBold)  # checked seg/chip buttons are drawn semi-bold
        # text + icon + horizontal padding + border (seg 4+4+1+1, chip 2+2+1+1)
        pad = {"chip": 6}.get(b.objectName(), 10)
        need = QFontMetrics(f).horizontalAdvance(b.text().strip()) + (b.iconSize().width() + 6 if not b.icon().isNull() else 0) + pad
        if need > b.width():
            out.append(f"{b.text().strip()!r} need={need} have={b.width()}")
    return out


def _rmtree(path):
    """shutil.rmtree that first clears Read-only/Hidden/System (Windows refuses otherwise)."""
    import shutil
    from .system import dosattr
    for dp, dns, fns in os.walk(path):
        for n in dns + fns:
            dosattr.clear(os.path.join(dp, n))
    dosattr.clear(path)
    shutil.rmtree(path, ignore_errors=True)


def _folder_tests(w, app, log, out):
    from .system import foldericon as fi, dosattr
    from .ui.dialogs import RepairDialog
    d = tempfile.mkdtemp(prefix="dosye_test_")
    res = w.apply_folder_icon(d)
    names = sorted(os.listdir(d))
    log(f"     result={res!r} files={names}")
    ico = [n for n in names if n.startswith(".dosye_icon_") and n.endswith(".ico")]
    png = [n for n in names if n.startswith(".dosye_icon_") and n.endswith(".png")]
    log.check(len(ico) == 1 and len(png) == 1 and ico[0][:-4] == png[0][:-4], "hidden .ico + .png with the same cache-busting name")
    raw = open(os.path.join(d, "desktop.ini"), "rb").read()
    txt = raw.decode("utf-16")
    log.check(raw[:2] == b"\xff\xfe" and "\r\n" in txt and "\n" not in txt.replace("\r\n", "")
              and f"IconResource={ico[0]},0" in txt, "desktop.ini: UTF-16 BOM, CRLF, relative IconResource")
    dirf = open(os.path.join(d, ".directory"), encoding="utf-8").read()
    log.check(f"Icon=./{png[0]}" in dirf, "KDE/PCManFM-Qt .directory: Icon=./ relative")
    fa = dosattr.get(d)
    if IS_WINDOWS:
        ia = dosattr.get(os.path.join(d, "desktop.ini")) or 0
        log.check(fa is not None and fa & (dosattr.READONLY | dosattr.SYSTEM) and ia & dosattr.HIDDEN and res.win_attr,
                  f"Windows: folder Read-only/System (0x{fa or 0:x}), desktop.ini hidden (0x{ia:x})")
    else:
        log(f"     DOS attributes on this file system: {'0x%x' % fa if fa is not None else 'not stored (ext4/btrfs…)'} win_attr={res.win_attr}")
        if fi.gio_available():
            if res.gio:
                log.check(fi.gio_get(d) == fi._file_uri(os.path.join(d, png[0])), "GIO metadata::custom-icon set")
            else:   # headless CI: no gvfsd-metadata session daemon, so GIO refuses the attribute
                log("     WARN gio present but metadata::custom-icon not settable here (no gvfsd-metadata?)")
        else:
            log("     gio not installed: GNOME/Nemo/Caja/Thunar method skipped")
    log(f"     message: {w.apply_message(res)}")
    # simulate a copy that lost the attribute / a cloud service dropping desktop.ini and the PNG
    dosattr.change(d, remove=dosattr.READONLY | dosattr.SYSTEM)
    for n in (png[0], "desktop.ini"):
        fi._remove(os.path.join(d, n))
    r = fi.repair_tree(d)
    after = sorted(os.listdir(d))
    log.check(r["fixed"] == 1 and set(after) == set(names)
              and (not IS_WINDOWS or dosattr.get(d) & (dosattr.READONLY | dosattr.SYSTEM)), f"repair restores lost files/attribute ({r['fixed']} fixed): {after}")
    r2 = fi.repair_tree(d)
    log.check(r2["fixed"] == 0 and r2["ok"] == 1, "repair is idempotent (second run changes nothing)")
    # Dosye 1.0.0 layouts (Linux: PNG + absolute .directory, Windows/Gerador: .icone_pasta_ .ico)
    root = tempfile.mkdtemp(prefix="dosye_tree_")
    a, b = os.path.join(root, "linux100"), os.path.join(root, "sub", "win100")
    os.makedirs(a); os.makedirs(b)
    open(os.path.join(a, ".dosye_icon_1700000000.png"), "wb").write(open(os.path.join(d, png[0]), "rb").read())
    open(os.path.join(a, ".directory"), "w").write(f"[Desktop Entry]\nIcon={a}/.dosye_icon_1700000000.png\n")
    open(os.path.join(b, ".icone_pasta_1600000000.ico"), "wb").write(open(os.path.join(d, ico[0]), "rb").read())
    open(os.path.join(b, "desktop.ini"), "wb").write("[.ShellClassInfo]\r\nIconResource=.icone_pasta_1600000000.ico,0\r\n".encode("utf-16"))
    os.makedirs(os.path.join(root, "plain", "deep"))
    r3 = fi.repair_tree(root)
    okA = {".dosye_icon_1700000000.ico", "desktop.ini"} <= set(os.listdir(a)) and "Icon=./.dosye_icon_1700000000.png" in open(os.path.join(a, ".directory")).read()
    okB = {".icone_pasta_1600000000.png", ".directory"} <= set(os.listdir(b))
    log.check(r3["found"] == 2 and r3["fixed"] == 2 and okA and okB, f"1.0.0 / Gerador de Pastas folders upgraded by repair (scanned {r3['scanned']})")
    # repair dialog (UI) + screenshot
    import shutil
    _rmtree(a); os.makedirs(a)
    open(os.path.join(a, ".dosye_icon_1700000000.png"), "wb").write(open(os.path.join(d, png[0]), "rb").read())
    dlg = RepairDialog(w, root); dlg.show()
    t0 = time.time()
    while not dlg.is_done() and time.time() - t0 < 30:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()
    dlg.grab().save(os.path.join(out, f"repair_dialog_{i18n.current()}.png"))
    log.check(dlg.is_done() and dlg.summary["found"] == 2 and dlg.summary["fixed"] == 1, f"Repair dialog: {dlg.summary}")
    dlg.accept()
    # removal deletes every format, new and legacy
    ok_rm = True
    for f in (d, a, b):
        had = folders.remove(f)
        left = [n for n in os.listdir(f) if fi._is_ours(n) or n in ("desktop.ini", ".directory")]
        ok_rm &= had and not left and not ((dosattr.get(f) or 0) & (dosattr.READONLY | dosattr.SYSTEM))
    log.check(ok_rm, "remove deletes all formats (1.1 and legacy) and clears the folder attribute")
    for f in (d, root):
        _rmtree(f)


def run(w, app, out):
    os.makedirs(out, exist_ok=True)
    log = Log(os.path.join(out, "selftest.txt"))
    log(f"Dosye {__version__} self-test — {sys.platform} — Python {sys.version.split()[0]}")
    def settle():
        for _ in range(3):
            app.processEvents()
        w.t_main.stop(); w.t_slow.stop(); w._render_main(); w._render_slow(); w.flush_thumbnails(); app.processEvents()
    try:
        w.setWindowState(Qt.WindowNoState); w.resize(1366, 728); settle()

        # 1) translations ------------------------------------------------------
        log("\n[i18n]")
        for code, name, _ in i18n.LANGUAGES:
            m, b = i18n.missing_keys(code), i18n.bad_placeholders(code)
            log.check(not m and not b, f"language {code} ({name}): missing={len(m)} placeholder_errors={len(b)}" + (f" {m[:6]}" if m else ""))
        en = i18n._load("en")
        needed = [f"shape.{s}" for s in fc.STYLE_IDS] + [f"cat.{c}" for c in fc.CATEGORY_ORDER]
        log.check(all(k in en for k in needed), f"English has names for all {len(fc.STYLE_IDS)} shapes and {len(fc.CATEGORY_ORDER)} categories")

        # 2) every shape -> .ico ------------------------------------------------
        log("\n[export]")
        n_ok = 0
        for sid in fc.STYLE_IDS:
            w.style_btns[sid].click(); app.processEvents()
            p = os.path.join(out, "ico", f"{sid}.ico"); os.makedirs(os.path.dirname(p), exist_ok=True)
            fc.export_ico(w.P, p)
            typ, entries = fc.parse_ico(p)
            n_ok += [e[0] for e in entries] == fc.ICO_SIZES
        log.check(n_ok == len(fc.STYLE_IDS), f"all shapes exported to .ico with {fc.ICO_SIZES}: {n_ok}/{len(fc.STYLE_IDS)}")
        p = os.path.join(out, "custom_sizes.ico"); fc.export_ico(w.P, p, [16, 32, 256])
        log.check([e[0] for e in fc.parse_ico(p)[1]] == [16, 32, 256], "custom .ico sizes from settings (16, 32, 256)")
        p = os.path.join(out, "export_1024.png"); fc.export_png(w.P, p, 1024)
        from PIL import Image
        log.check(Image.open(p).size == (1024, 1024), "PNG export 1024 px")

        # 3) features ----------------------------------------------------------
        log("\n[features]")
        from .paths import asset
        w.reset(); settle()
        w._load_cover_file(asset("covers", "galaxia.jpg")); w.set("cover_area", "frente"); settle()
        log.check(w.P["fill"] == "imagem" and w.cover_box.isVisible(), "image cover loads (front only)")
        w._load_overlay_file(asset("stickers", "fotos.png")); w.set("overlay_mode", "dentro"); settle()
        log.check(w.P["overlay_mode"] == "dentro", "PNG coming out of the folder")
        for st in ("original", "gravado", "branco"):
            w.set("overlay_mode", "frente"); w.set("emblem_style", st); settle()
        for k in ("mirror", "glass", "border", "papers"):
            w.set(k, True)
        w.set("glow", 60); settle()
        log.check(True, "emblem styles, mirror, glass, border, papers, glow render")
        seen = set()
        for _ in range(40):
            w.randomize(); seen.add(w.P["style"])
        log.check(len(seen) > 15, f"Surprise me: {len(seen)} different shapes in 40 draws")
        w.search.setText("coracao"); app.processEvents()
        log.check(w._visible_ids() == ["coracao"], "search without accents finds 'Coração'/Heart")
        w.search.setText("zipper"); app.processEvents()
        log.check("ziper" in w._visible_ids(), "search by English name works in any language")
        w.search.clear(); w.cat_btns["office"].click(); app.processEvents()
        log.check(len(w._visible_ids()) == 13, f"category Office shows 13 shapes ({len(w._visible_ids())})")
        w.cat_btns["all"].click(); app.processEvents()

        # 4) presets -----------------------------------------------------------
        log("\n[presets]")
        w.reset(); w._load_cover_file(asset("covers", "aurora.jpg")); w._load_overlay_file(asset("stickers", "lua.png")); settle()
        data = w.preset_data(); pp = os.path.join(out, "test.dosye.json")
        json.dump(data, open(pp, "w", encoding="utf-8"))
        before = fc.qimage_to_pil(fc.render(w.P, 256))
        w.reset(); settle(); w.load_preset_file(pp); settle()
        after = fc.qimage_to_pil(fc.render(w.P, 256))
        from PIL import ImageChops
        diff = max(ImageChops.difference(before, after).getextrema()[c][1] for c in range(4))
        log.check(diff <= 2, f".dosye.json round-trip with embedded images (max pixel diff {diff})")
        old = {"app": "GeradorDePastas", "versao": 1, "params": {"style": "mac", "color1": "#22C55E", "gradient": False, "chave_velha": 1}}
        p1 = os.path.join(out, "old_v1.pasta.json"); json.dump(old, open(p1, "w", encoding="utf-8"))
        w.load_preset_file(p1); settle()
        log.check((w.P["style"], w.P["color1"]) == ("mac", "#22C55E") and w.style_btns["mac"].isChecked(), "old Gerador de Pastas v1 preset (.pasta.json)")
        old["params"].update(style="unknown_shape", overlay_mode="???"); json.dump(old, open(p1, "w", encoding="utf-8"))
        w.load_preset_file(p1); settle()
        log.check(w.P["style"] == "moderna" and w.P["overlay_mode"] == "nenhum", "invalid values fall back to defaults")

        # 5) folder icon integration (portable: every format on every OS) ------
        log("\n[folder icon]")
        if folders.supported():
            _folder_tests(w, app, log, out)
        else:
            log("     not supported on this OS")

        # 6) settings + animation clock -------------------------------------
        log("\n[settings & animations]")
        from .app import apply_theme
        s = w.settings
        saved = dict(s.data)
        w.apply_settings({"animations": True, "reduce_effects": False}); app.processEvents()
        log.check(clock().is_running() == (w.isVisible() and clock()._active), f"animations ON -> clock running={clock().is_running()}")
        cpu_on = _cpu_percent(app, 6)
        w.apply_settings({"animations": False}); app.processEvents()
        log.check(not clock().is_running() and not FX.animations, "animations OFF -> clock stopped")
        cpu_off = _cpu_percent(app, 6)
        w.apply_settings({"reduce_effects": True}); app.processEvents()
        log.check(not FX.glow and not clock().is_running(), "reduce effects -> no glow, no animation")
        cpu_red = _cpu_percent(app, 4)
        log(f"     idle CPU (this process): animations on {cpu_on:.1f}% | off {cpu_off:.1f}% | reduced {cpu_red:.1f}%")
        w.showMinimized(); app.processEvents()
        log.check(not clock().is_running(), "clock paused while minimized")
        w.showNormal(); app.processEvents()
        s.data.update(saved); w.apply_settings({"animations": True, "reduce_effects": False})

        # 6b) language switch at runtime (1.0.0 bug: Settings saved it but nothing changed)
        log("\n[language switch]")
        en, ja = i18n._load("en"), i18n._load("ja")
        w.apply_settings({"language": "pt_BR"}); settle()
        pt = i18n._load("pt_BR")
        log.check(w.search.placeholderText() == pt["shapes.search"], f"start in pt_BR: {w.search.placeholderText()!r}")
        for code, ref in (("en", en), ("ja", ja), ("ht", i18n._load("ht"))):
            w.apply_settings({"language": code}); settle()
            texts = {b.text().strip() for b in w.centralWidget().findChildren(QPushButton)}
            ok = (i18n.current() == code and w.search.placeholderText() == ref["shapes.search"]
                  and ref["export.repair"] in texts and ref["export.ico"] in texts
                  and w.b_repair.toolTip() == ref["export.repair_tip"])
            log.check(ok, f"Settings -> {code}: UI switched live (placeholder {w.search.placeholderText()!r}, buttons/tooltips)")
            w.grab().save(os.path.join(out, f"runtime_switch_{code}.png"))
        from PySide6.QtCore import QCoreApplication
        qt_cancel = QCoreApplication.translate("QPlatformTheme", "Cancel")
        log(f"     Qt standard buttons in 'ht' (via qtbase_fr): Cancel -> {qt_cancel!r}")
        w.apply_settings({"language": saved.get("language", "auto")}); settle()

        # 7) layout in every language ------------------------------------------
        log("\n[layout]")
        shots = {"pt_BR", "ht", "ja"}
        w.reset()
        for code, name, _ in i18n.LANGUAGES:
            i18n.set_language(code); apply_theme(app, s); w.build_ui()
            for (W_, H_) in ((1366, 728), (1093, 584)):
                w.resize(W_, H_); settle()
                sc, ss = w.panel_scroll, w.shape_scroll
                ok = (sc.widget().width() <= sc.viewport().width() and sc.parent().width() == 370
                      and ss.parent().width() == 250 and w.width() <= W_ and w.minimumSizeHint().width() <= W_)
                clipped = _overflow_buttons(w.centralWidget())
                log.check(ok, f"{code} {W_}x{H_}: window={w.width()}x{w.height()} min={w.minimumSizeHint().width()} panels ok")
                if clipped:
                    log(f"     WARN {code} {W_}x{H_} clipped text: {clipped[:5]}")
                if code in shots and W_ == 1366:
                    w.grab().save(os.path.join(out, f"ui_{code}.png"))
            if code == "ht":
                w.resize(1093, 584); settle(); w.grab().save(os.path.join(out, "ui_ht_1093x584.png"))
        # dialogs
        for code in ("pt_BR", "ht", "ja", "en"):
            i18n.set_language(code); apply_theme(app, s); w.build_ui(); w.resize(1366, 728); settle()
            from .ui.dialogs import AboutDialog, SettingsDialog, HelpDialog
            for cls, nm in ((AboutDialog, "about"), (SettingsDialog, "settings"), (HelpDialog, "help")):
                dlg = cls(w, s) if cls is SettingsDialog else cls(w)
                dlg.show(); app.processEvents(); dlg.adjustSize() if cls is not HelpDialog else None; app.processEvents()
                dlg.grab().save(os.path.join(out, f"dialog_{nm}_{code}.png")); dlg.close()
        # category + shape screenshot
        i18n.set_language("pt_BR"); apply_theme(app, s); w.build_ui(); w.resize(1366, 728)
        w.cat_btns["fun"].click(); w.style_btns["gatinho"].click(); settle()
        w.grab().save(os.path.join(out, "ui_pt_BR_divertidas.png"))
        log.check(True, "screenshots saved")
    except Exception:
        log("ERROR\n" + traceback.format_exc()); log.fail.append("exception")
    log("\nRESULT: " + ("ALL OK" if not log.fail else f"{len(log.fail)} FAILURE(S): {log.fail}"))
    log.f.close()
    app.exit(0 if not log.fail else 1)

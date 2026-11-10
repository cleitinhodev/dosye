"""Dosye main window."""
import base64
import io
import json
import os
import random
import sys
import time
import unicodedata

from PySide6.QtCore import Qt, QObject, QTimer, QSize, QByteArray, QBuffer, QIODevice, QUrl
from PySide6.QtGui import QPixmap, QColor, QIcon, QImage, QKeySequence, QShortcut, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
                               QPushButton, QCheckBox, QFrame, QFileDialog, QMessageBox, QButtonGroup, QSizePolicy,
                               QLineEdit)

from .. import __version__, APP_NAME, URL_DONATE
from ..core import render as fc
from .. import i18n
from ..i18n import tr
from ..paths import asset, is_asset, presets_dir, pictures_dir
from ..system import folders, windows, IS_WINDOWS
from . import theme
from .effects import FX, clock, HoverGlow, fade_in
from .icons import icon
from .widgets import (ElidedLabel, Thumb, VScroll, combo, set_combo_data, SliderRow, ColorButton, Section, row,
                      ShapeTile, Preview, SizeStrip, StarHeader, GradientTitle, Toast, app_pixmap, bg_swatch, TextFitter, BACKGROUNDS)
from .dialogs import SettingsDialog, HelpDialog, AboutDialog

STICKERS = ["lua", "fotos", "musica", "codigo", "coracao", "estrela", "nuvem", "jogo", "download"]
COVERS = ["galaxia", "marmore", "aurora", "madeira", "synthwave", "granilite"]
IMG_EXT = "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"
PRESET_EXT = "*.dosye.json *.pasta.json *.json"


def start_design():
    """What a fresh Dosye shows: the indigo night folder with the golden moon, like the app icon."""
    P = fc.default_params()
    P.update(style="moderna", color1="#3A34D6", color2="#7B3FF2", gradient=True, grad_angle=60,
             overlay_mode="frente", overlay_path=asset("stickers", "lua.png"), emblem_style="original",
             ov_scale=78, ov_y=4, glow=0, light=45, gloss=40, papers=True)
    return P


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


class MainWindow(QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.P = start_design()
        self.last_dir = None
        self.glows = []
        self.ui_ready = False
        self.t_main = QTimer(self, singleShot=True, interval=12, timeout=self._render_main)
        self.t_slow = QTimer(self, singleShot=True, interval=220, timeout=self._render_slow)
        self.t_thumbs = QTimer(self, interval=0, timeout=self._thumb_tick)
        self._crossfade = False
        self.build_ui()
        self._shortcuts()
        QGuiApplication.instance().applicationStateChanged.connect(
            lambda st: clock().set_app_active(st == Qt.ApplicationActive))
        scr = QApplication.primaryScreen()
        ag = scr.availableGeometry() if scr else None
        if ag is not None:
            self.resize(min(1400, ag.width() - 40), min(900, ag.height() - 60))
            if ag.width() < 1300 or ag.height() < 760:
                self.setWindowState(Qt.WindowMaximized)
        else:
            self.resize(1360, 860)

    # ================================================================ build
    def build_ui(self):
        """(Re)creates every widget — used at start and when the language changes."""
        self.ui_ready = False
        self.t_thumbs.stop()
        old = self.centralWidget()
        self.glows = []
        if getattr(self, "_owner", None) is not None:
            self._owner.deleteLater()
        self._owner = QObject(self)          # parent of per-build helper objects (button groups)
        self.setWindowTitle(APP_NAME)
        root = QWidget(); root.setObjectName("root")
        outer = QVBoxLayout(root); outer.setContentsMargins(16, 12, 16, 16); outer.setSpacing(12)
        outer.addWidget(self._header())
        body = QHBoxLayout(); body.setSpacing(12); outer.addLayout(body, 1)
        body.addWidget(self._sidebar())
        body.addLayout(self._center(), 1)
        body.addWidget(self._panel())
        self.setCentralWidget(root)
        if old is not None:
            old.deleteLater()
        self.toast = Toast(self.preview)
        self.ui_ready = True
        self._sync_ui()
        self.refresh()
        self.preview.set_bg(self.settings["preview_bg"])
        for k, b in self.bg_btns.items():
            b.setChecked(k == self.preview.bg)
        self._update_strip_visibility()
        # Long labels (some languages / wider system fonts) shrink instead of being clipped.
        self._fitter = TextFitter(self._owner)
        for b in root.findChildren(QPushButton):
            if b.objectName() in TextFitter.PAD and b.text().strip():
                self._fitter.watch(b)

    def _glow(self, w, **kw):
        g = HoverGlow(w, **kw); self.glows.append(g); return g

    # ---------------------------------------------------------------- header
    def _header(self):
        w = StarHeader(); w.setFixedHeight(74)
        h = QHBoxLayout(w); h.setContentsMargins(14, 8, 14, 8); h.setSpacing(8)
        self.logo = QLabel(); self.logo.setFixedSize(56, 56)
        self.logo.setPixmap(app_pixmap(asset("icons", "dosye_icon.png"), 56, self.devicePixelRatioF()))
        self.logo.setToolTip(f"{APP_NAME} {__version__}")
        h.addWidget(self.logo)
        tv = QVBoxLayout(); tv.setSpacing(0); tv.setContentsMargins(0, 0, 0, 0)
        tv.addStretch(1)
        tv.addWidget(GradientTitle(APP_NAME, 19))
        self.tagline = ElidedLabel(tr("app.tagline"), Qt.ElideRight); self.tagline.setObjectName("rowLabel")
        self.tagline.setStyleSheet("color: #C9C6FF; font-size: 9pt;")
        tv.addWidget(self.tagline); tv.addStretch(1)
        h.addLayout(tv, 1)
        gold = theme.GOLD_LIGHT
        def btn(text, ic, slot, name="ghost", tip="", color=theme.TEXT):
            b = QPushButton(icon(ic, color, 18), (" " + text) if text else "")
            b.setObjectName(name); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(slot)
            b.setIconSize(QSize(18, 18))
            if tip:
                b.setToolTip(tip)
            h.addWidget(b); return b
        self.b_surprise = btn(tr("hdr.surprise"), "sparkle", self.randomize, "gold", tr("hdr.surprise_tip") + "  (Ctrl+R)", "#3A2400")
        self._glow(self.b_surprise, color=theme.GOLD, radius=24)
        for text, ic, slot, tip in ((tr("hdr.open"), "open", self.load_preset, tr("hdr.open_tip") + "  (Ctrl+O)"),
                                    (tr("hdr.save"), "save", self.save_preset, tr("hdr.save_tip") + "  (Ctrl+S)"),
                                    (tr("hdr.reset"), "reset", self.reset, tr("hdr.reset_tip"))):
            self._glow(btn(text, ic, slot, tip=tip))
        sep = QFrame(); sep.setFixedSize(1, 30); sep.setStyleSheet("background: rgba(200,190,255,0.25);"); h.addWidget(sep)
        for ic, slot, tip in (("gear", self.open_settings, tr("hdr.settings") + "  (Ctrl+,)"),
                              ("help", self.open_help, tr("hdr.help") + "  (F1)"),
                              ("info", self.open_about, tr("hdr.about"))):
            b = btn("", ic, slot, "iconbtn", tip, gold); b.setFixedSize(38, 36); self._glow(b)
        self.b_donate = btn(tr("hdr.donate"), "heart", lambda: QDesktopServices.openUrl(QUrl(URL_DONATE)),
                            "heart", tr("hdr.donate_tip"), theme.PINK)
        self._glow(self.b_donate, color=theme.PINK, radius=22)
        self.header = w
        return w

    # ---------------------------------------------------------------- sidebar
    def _sidebar(self):
        w = QFrame(); w.setObjectName("sidebar"); w.setFixedWidth(250)
        v = QVBoxLayout(w); v.setContentsMargins(12, 12, 6, 8); v.setSpacing(8)
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 6, 0)
        t = ElidedLabel(tr("shapes.title"), Qt.ElideRight); t.setObjectName("sectionTitle"); top.addWidget(t, 1)
        self.shape_count = QLabel(""); self.shape_count.setObjectName("count"); top.addWidget(self.shape_count)
        v.addLayout(top)
        self.search = QLineEdit(); self.search.setPlaceholderText(tr("shapes.search")); self.search.setClearButtonEnabled(True)
        self.search.addAction(icon("search", theme.DIM, 16), QLineEdit.LeadingPosition)
        self.search.textChanged.connect(lambda _t: self._apply_filter())
        sh = QHBoxLayout(); sh.setContentsMargins(0, 0, 6, 0); sh.addWidget(self.search); v.addLayout(sh)
        chips = QGridLayout(); chips.setSpacing(5); chips.setContentsMargins(0, 0, 6, 0)
        self.cat_group = QButtonGroup(self._owner); self.cat_btns = {}
        for i, cat in enumerate(["all"] + fc.CATEGORY_ORDER):
            bt = QPushButton(tr(f"cat.{cat}")); bt.setObjectName("chip"); bt.setCheckable(True); bt.setCursor(Qt.PointingHandCursor)
            n = len(fc.STYLE_IDS) if cat == "all" else sum(1 for s in fc.STYLE_IDS if fc.STYLE_CAT_IDS.get(s) == cat)
            bt.setToolTip(tr("shapes.cat_tip", cat=tr(f"cat.{cat}"), n=n))
            bt.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            bt.clicked.connect(lambda _=False: self._apply_filter(animate=True))
            self.cat_group.addButton(bt); self.cat_btns[cat] = bt
            chips.addWidget(bt, i // 3, i % 3)
        self.cat_btns["all"].setChecked(True)
        v.addLayout(chips)
        self.shape_scroll = VScroll()
        inner = QWidget(); self.shape_scroll.setWidget(inner); self.shape_inner = inner
        self.shape_grid = QGridLayout(inner); self.shape_grid.setContentsMargins(0, 2, 4, 2); self.shape_grid.setSpacing(4)
        self.shape_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.style_btns = {}
        self.style_group = QButtonGroup(self._owner); self.style_group.setExclusive(True)
        for sid in fc.STYLE_IDS:
            name = tr(f"shape.{sid}")
            tip = f"{name} — {tr('cat.' + fc.STYLE_CAT_IDS.get(sid, 'all'))}"
            if i18n.has(f"tip.{sid}"):
                tip += "\n" + tr(f"tip.{sid}")
            bt = ShapeTile(sid, name, tip)
            bt.clicked.connect(lambda _=False, s=sid: self.set("style", s))
            self.style_group.addButton(bt); self.style_btns[sid] = bt
        self.empty_lbl = QLabel(tr("shapes.none")); self.empty_lbl.setObjectName("hint"); self.empty_lbl.setWordWrap(True)
        v.addWidget(self.shape_scroll, 1)
        self.thumb_stale = set(self.style_btns)
        self._apply_filter()
        return w

    def _visible_ids(self):
        cat = next((c for c, bt in self.cat_btns.items() if bt.isChecked()), "all")
        q = _norm(self.search.text().strip())
        out = []
        for sid in fc.STYLE_IDS:
            c = fc.STYLE_CAT_IDS.get(sid)
            if cat != "all" and c != cat:
                continue
            if q:
                hay = " ".join((tr(f"shape.{sid}"), i18n.tr_in("en", f"shape.{sid}"), fc.STYLE_NAMES[sid], sid, tr(f"cat.{c}")))
                if q not in _norm(hay):
                    continue
            out.append(sid)
        return out

    def _apply_filter(self, animate=False):
        ids = self._visible_ids()
        g = self.shape_grid
        while g.count():
            it = g.takeAt(0)
            if it.widget():
                it.widget().hide()
        for i, sid in enumerate(ids):
            bt = self.style_btns[sid]; g.addWidget(bt, i // 2, i % 2); bt.show()
        if not ids:
            g.addWidget(self.empty_lbl, 0, 0, 1, 2); self.empty_lbl.show()
        self.shape_count.setText(tr("shapes.count", n=len(ids), total=len(fc.STYLE_IDS)))
        self.shape_scroll.verticalScrollBar().setValue(0)
        if animate:
            fade_in(self.shape_inner, 200)
        self.t_thumbs.start()

    def _thumb_tick(self):
        """Thumbnails are rendered a few at a time (visible ones first) so the UI never freezes."""
        todo = [s for s in self._visible_ids() if s in self.thumb_stale][:3]
        if not todo:
            self.t_thumbs.stop(); return
        dpr = self.devicePixelRatioF()
        for sid in todo:
            q = dict(self.P); q["style"] = sid
            img = fc.render(q, int(70 * dpr * 2))
            pm = QPixmap.fromImage(img.scaled(int(70 * dpr), int(70 * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            pm.setDevicePixelRatio(dpr)
            self.style_btns[sid].set_pixmap(pm)
            self.thumb_stale.discard(sid)

    def flush_thumbnails(self):
        while self.t_thumbs.isActive():
            self._thumb_tick()

    # ---------------------------------------------------------------- center
    def _center(self):
        v = QVBoxLayout(); v.setSpacing(10)
        top = QHBoxLayout(); top.setSpacing(6)
        lt = QLabel(tr("preview.title")); lt.setObjectName("sectionTitle"); top.addWidget(lt); top.addStretch(1)
        bl = QLabel(tr("preview.bg")); bl.setObjectName("hint"); top.addWidget(bl)
        self.bg_group = QButtonGroup(self._owner); self.bg_btns = {}
        for key in BACKGROUNDS:
            # Icon-only swatches: language-independent width, the name lives in the tooltip.
            b = QPushButton(); b.setObjectName("seg"); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.setIcon(bg_swatch(key, 18, self.devicePixelRatioF())); b.setIconSize(QSize(18, 18)); b.setFixedSize(36, 30)
            b.setToolTip(tr(f"bg.{key}")); b.setAccessibleName(tr(f"bg.{key}"))
            b.clicked.connect(lambda _=False, k=key: self._set_bg(k)); self.bg_group.addButton(b); top.addWidget(b)
            self.bg_btns[key] = b; self._glow(b)
        v.addLayout(top)
        self.preview = Preview()
        self.preview.moved.connect(self._drag_move); self.preview.scaled.connect(self._wheel_scale)
        self.preview.dropped.connect(self._dropped)
        v.addWidget(self.preview, 1)
        hb = QHBoxLayout(); hb.setSpacing(6)
        self.drag_hint = ElidedLabel("", Qt.ElideRight); self.drag_hint.setObjectName("hint")
        hb.addWidget(self.drag_hint, 1)
        self.target_lbl = QLabel(tr("preview.move")); self.target_lbl.setObjectName("hint"); hb.addWidget(self.target_lbl)
        self.target_group = QButtonGroup(self._owner); self.target_btns = {}
        for key, name in (("png", tr("preview.png")), ("capa", tr("preview.cover"))):
            bt = QPushButton(name); bt.setObjectName("seg"); bt.setCheckable(True); bt.setCursor(Qt.PointingHandCursor)
            bt.setToolTip(tr("preview.move_tip"))
            self.target_group.addButton(bt); hb.addWidget(bt); self.target_btns[key] = bt
        self.target_btns["png"].setChecked(True)
        v.addLayout(hb)
        self.strip = SizeStrip(); v.addWidget(self.strip)
        return v

    def _set_bg(self, k):
        self.preview.set_bg(k); self.settings["preview_bg"] = k; self.settings.save()

    # ---------------------------------------------------------------- right panel
    def _panel(self):
        outer = QFrame(); outer.setObjectName("panel"); outer.setFixedWidth(370)
        ov = QVBoxLayout(outer); ov.setContentsMargins(6, 8, 6, 12); ov.setSpacing(8)
        sc = VScroll(); self.panel_scroll = sc
        inner = QWidget(); v = QVBoxLayout(inner); v.setContentsMargins(8, 4, 8, 4); v.setSpacing(10)
        sc.setWidget(inner); ov.addWidget(sc, 1)
        W = self.w = {}

        # Fill
        s = Section(tr("fill.title"))
        segf = QHBoxLayout(); segf.setSpacing(6)
        self.fill_group = QButtonGroup(self._owner); W["fill_btns"] = {}
        for key, name, tip in (("cor", tr("fill.color"), tr("fill.color_tip")), ("imagem", tr("fill.image"), tr("fill.image_tip"))):
            bt = QPushButton(name); bt.setObjectName("seg"); bt.setCheckable(True); bt.setToolTip(tip); bt.setCursor(Qt.PointingHandCursor)
            bt.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            bt.clicked.connect(lambda _=False, k=key: self.set("fill", k)); self.fill_group.addButton(bt); segf.addWidget(bt)
            W["fill_btns"][key] = bt; self._glow(bt)
        s.addLayout(segf)
        cv = QWidget(); self.cover_box = cv
        cl = QVBoxLayout(cv); cl.setContentsMargins(0, 2, 0, 6); cl.setSpacing(8)
        r1 = QHBoxLayout(); r1.setSpacing(8)
        self.cover_thumb = Thumb(64, 44); r1.addWidget(self.cover_thumb)
        cvv = QVBoxLayout(); cvv.setSpacing(4)
        self.cover_name = ElidedLabel(""); self.cover_name.setObjectName("hint"); cvv.addWidget(self.cover_name)
        bc = QPushButton(icon("image", theme.GOLD_LIGHT, 16), " " + tr("cover.choose")); bc.setCursor(Qt.PointingHandCursor); bc.clicked.connect(self.pick_cover)
        bc.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed); cvv.addWidget(bc)
        r1.addLayout(cvv, 1); cl.addLayout(r1)
        lx = QLabel(tr("cover.examples")); lx.setObjectName("hint"); cl.addWidget(lx)
        cg = QGridLayout(); cg.setSpacing(6)
        for i, key in enumerate(COVERS):
            path = asset("covers", f"{key}.jpg")
            bt = QPushButton(); bt.setObjectName("sticker"); bt.setToolTip(tr(f"texture.{key}")); bt.setCursor(Qt.PointingHandCursor)
            bt.setIcon(QIcon(path)); bt.setIconSize(QSize(70, 40)); bt.setFixedHeight(48)
            bt.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed); bt.setMinimumWidth(40)
            bt.clicked.connect(lambda _=False, p=path: self._load_cover_file(p))
            cg.addWidget(bt, i // 3, i % 3)
        cl.addLayout(cg)
        W["cover_area"] = combo([("toda", tr("cover.area_all")), ("frente", tr("cover.area_front"))])
        W["cover_area"].currentIndexChanged.connect(lambda i: self.set("cover_area", W["cover_area"].itemData(i)))
        cl.addLayout(row(tr("cover.apply_to"), W["cover_area"]))
        segc = QHBoxLayout(); segc.setSpacing(6); W["fit_btns"] = {}; self.fit_group = QButtonGroup(self._owner)
        for key, _name in fc.COVER_FITS:
            bt = QPushButton(tr(f"fit.{key}")); bt.setObjectName("seg"); bt.setCheckable(True); bt.setCursor(Qt.PointingHandCursor)
            bt.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            bt.clicked.connect(lambda _=False, k=key: self.set("cover_fit", k)); self.fit_group.addButton(bt); segc.addWidget(bt)
            W["fit_btns"][key] = bt
        cl.addLayout(segc)
        for key, label, lo, hi, suf in (("cover_zoom", "cover.zoom", 10, 400, "%"), ("cover_x", "cover.x", -100, 100, ""),
                                         ("cover_y", "cover.y", -100, 100, ""), ("cover_back_dark", "cover.back_dark", 0, 100, "%"),
                                         ("cover_tint", "cover.tint", 0, 100, "%")):
            r = SliderRow(tr(label), lo, hi, int(self.P[key]), suf); r.changed.connect(lambda val, k=key: self.set(k, val))
            cl.addWidget(r); W[key] = r
        W["cover_blend"] = combo([(k, tr(f"blend.{k}")) for k, _ in fc.COVER_BLENDS])
        W["cover_blend"].currentIndexChanged.connect(lambda i: self.set("cover_blend", W["cover_blend"].itemData(i)))
        cl.addLayout(row(tr("cover.blend"), W["cover_blend"]))
        s.add(cv)
        self.color_hint = QLabel(tr("cover.color_hint")); self.color_hint.setObjectName("hint"); self.color_hint.setWordWrap(True); s.add(self.color_hint)
        W["color1"] = ColorButton(self.P["color1"], tr("color.main")); W["color1"].changed.connect(self.set_color1)
        s.addLayout(row(tr("color.main"), W["color1"]))
        W["gradient"] = QCheckBox(tr("color.gradient")); W["gradient"].toggled.connect(lambda b: self.set("gradient", b)); s.add(W["gradient"])
        W["color2"] = ColorButton(self.P["color2"], tr("color.second")); W["color2"].changed.connect(self.set_color2)
        s.addLayout(row(tr("color.second"), W["color2"]))
        W["grad_angle"] = self._slider(s, "grad_angle", tr("color.angle"), 0, 180, "°")
        s.add(self._palette_widget())
        v.addWidget(s)

        # Light
        s = Section(tr("light.title"))
        self._slider(s, "light", tr("light.intensity"), 0, 100, "%")
        self._slider(s, "light_dir", tr("light.dir"), -100, 100, "", tr("light.dir_tip"))
        self._slider(s, "gloss", tr("light.gloss"), 0, 100, "%", tr("light.gloss_tip"))
        self._slider(s, "glow", tr("light.glow"), 0, 100, "%")
        W["glow_color"] = ColorButton(self.P["glow_color"], tr("light.glow_color")); W["glow_color"].changed.connect(lambda c: self.set("glow_color", c))
        s.addLayout(row(tr("light.glow_color"), W["glow_color"]))
        v.addWidget(s)

        # Shadow
        s = Section(tr("shadow.title"))
        self._slider(s, "shadow", tr("shadow.drop"), 0, 100, "%")
        self._slider(s, "shadow_dist", tr("shadow.dist"), 0, 100, "")
        self._slider(s, "shadow_blur", tr("shadow.blur"), 0, 100, "")
        self._slider(s, "inner", tr("shadow.inner"), 0, 100, "%", tr("shadow.inner_tip"))
        v.addWidget(s)

        # Details
        s = Section(tr("details.title"))
        for key, label in (("papers", "details.papers"), ("mirror", "details.mirror"), ("glass", "details.glass"), ("border", "details.border")):
            W[key] = QCheckBox(tr(label)); W[key].toggled.connect(lambda b, k=key: self.set(k, b)); s.add(W[key])
        self._slider(s, "glass_amount", tr("details.glass_amount"), 0, 100, "%")
        W["border_color"] = ColorButton(self.P["border_color"], tr("details.border_color")); W["border_color"].changed.connect(lambda c: self.set("border_color", c))
        s.addLayout(row(tr("details.border_color"), W["border_color"]))
        self._slider(s, "border_width", tr("details.border_width"), 0, 100, "")
        v.addWidget(s)

        # PNG image
        s = Section(tr("png.title"))
        seg = QHBoxLayout(); seg.setSpacing(6)
        self.mode_group = QButtonGroup(self._owner); W["mode_btns"] = {}
        for key, name, tip in (("nenhum", tr("png.none"), tr("png.none_tip")), ("dentro", tr("png.inside"), tr("png.inside_tip")),
                               ("frente", tr("png.front"), tr("png.front_tip"))):
            b = QPushButton(name); b.setObjectName("seg"); b.setCheckable(True); b.setToolTip(tip); b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _=False, k=key: self.set("overlay_mode", k)); self.mode_group.addButton(b); seg.addWidget(b)
            W["mode_btns"][key] = b; self._glow(b)
        s.addLayout(seg)
        lb = QHBoxLayout(); lb.setSpacing(6)
        bload = QPushButton(icon("image", theme.GOLD_LIGHT, 16), " " + tr("png.load")); bload.setCursor(Qt.PointingHandCursor); bload.clicked.connect(self.pick_overlay)
        bcent = QPushButton(tr("png.center")); bcent.setCursor(Qt.PointingHandCursor); bcent.clicked.connect(self.center_overlay)
        bload.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        lb.addWidget(bload, 1); lb.addWidget(bcent); s.addLayout(lb)
        ro = QHBoxLayout(); ro.setSpacing(8)
        self.ov_thumb = Thumb(44, 44); ro.addWidget(self.ov_thumb)
        self.ov_name = ElidedLabel(""); self.ov_name.setObjectName("hint"); ro.addWidget(self.ov_name, 1)
        s.addLayout(ro)
        sl = QLabel(tr("png.examples")); sl.setObjectName("hint"); s.add(sl)
        sg = QGridLayout(); sg.setSpacing(6)
        for i, key in enumerate(STICKERS):
            path = asset("stickers", key + ".png")
            b = QPushButton(); b.setObjectName("sticker"); b.setToolTip(tr(f"sticker.{key}")); b.setCursor(Qt.PointingHandCursor)
            b.setIcon(QIcon(path)); b.setIconSize(QSize(32, 32)); b.setFixedHeight(46)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.clicked.connect(lambda _=False, p=path: self._load_overlay_file(p))
            sg.addWidget(b, i // 5, i % 5)
        s.addLayout(sg)
        self._slider(s, "ov_x", tr("png.x"), -100, 100, "")
        self._slider(s, "ov_y", tr("png.y"), -100, 100, "")
        self._slider(s, "ov_scale", tr("png.scale"), 10, 250, "%")
        self._slider(s, "ov_rot", tr("png.rot"), -180, 180, "°")
        W["ov_shadow"] = QCheckBox(tr("png.shadow")); W["ov_shadow"].toggled.connect(lambda b: self.set("ov_shadow", b)); s.add(W["ov_shadow"])
        W["emblem_style"] = combo([(k, tr(f"emblem.{k}")) for k in ("original", "gravado", "branco")])
        W["emblem_style"].currentIndexChanged.connect(lambda i: self.set("emblem_style", W["emblem_style"].itemData(i)))
        s.addLayout(row(tr("png.emblem_style"), W["emblem_style"]))
        v.addWidget(s)
        v.addStretch(1)

        # Export (pinned at the bottom)
        ex = QVBoxLayout(); ex.setContentsMargins(8, 6, 8, 0); ex.setSpacing(8)
        bi = QPushButton(icon("export", "#FFFFFF", 18), " " + tr("export.ico")); bi.setObjectName("primary"); bi.setCursor(Qt.PointingHandCursor)
        bi.setIconSize(QSize(18, 18)); bi.clicked.connect(self.export_ico); self.b_export = bi
        self._glow(bi, color=theme.VIOLET, radius=28, always=True)
        ex.addWidget(bi)
        h = QHBoxLayout(); h.setSpacing(6)
        self.png_size = combo([(sz, f"PNG {sz}px") for sz in (256, 512, 1024)])
        set_combo_data(self.png_size, self.settings["png_size"])
        bp = QPushButton(tr("export.png")); bp.setCursor(Qt.PointingHandCursor); bp.clicked.connect(self.export_png)
        bp.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        h.addWidget(self.png_size); h.addWidget(bp, 1); ex.addLayout(h); self._glow(bp)
        ba = QPushButton(icon("folder_plus", theme.GOLD_LIGHT, 16), " " + tr("export.apply")); ba.setCursor(Qt.PointingHandCursor); ba.clicked.connect(self.apply_to_folder)
        ba.setToolTip(tr("export.apply_tip_win") if IS_WINDOWS else tr("export.apply_tip_linux"))
        br = QPushButton(icon("folder_minus", theme.MUTED, 16), " " + tr("export.remove")); br.setObjectName("ghost"); br.setCursor(Qt.PointingHandCursor); br.clicked.connect(self.remove_from_folder)
        for b in (ba, br):
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed); ex.addWidget(b); self._glow(b)
        ov.addLayout(ex)
        return outer

    def _palette_widget(self):
        box = QWidget(); v = QVBoxLayout(box); v.setContentsMargins(0, 2, 0, 0); v.setSpacing(6)
        hint = ElidedLabel(tr("color.palette"), Qt.ElideRight); hint.setObjectName("hint"); v.addWidget(hint)
        pg = QGridLayout(); pg.setSpacing(6)
        for i, c in enumerate(theme.PALETTE):
            bt = QPushButton(); bt.setObjectName("swatch"); bt.setCursor(Qt.PointingHandCursor); bt.setToolTip(c)
            bt.setStyleSheet(f"QPushButton#swatch {{ background: {c}; border: 1px solid rgba(255,255,255,0.22); }}"
                             f"QPushButton#swatch:hover {{ border: 2px solid {theme.GOLD_LIGHT}; }}")
            bt.clicked.connect(lambda _=False, c=c: self.set_color1(c))
            bt.setContextMenuPolicy(Qt.CustomContextMenu)
            bt.customContextMenuRequested.connect(lambda _p, c=c: self.set_color2(c))
            pg.addWidget(bt, i // 8, i % 8)
        v.addLayout(pg)
        return box

    def _slider(self, section, key, label, lo, hi, suffix="", tip=""):
        r = SliderRow(label, lo, hi, int(self.P[key]), suffix, tip)
        r.changed.connect(lambda val, k=key: self.set(k, val))
        section.add(r); self.w[key] = r
        return r

    def _shortcuts(self):
        for seq, slot in (("Ctrl+E", self.export_ico), ("Ctrl+Shift+E", self.export_png), ("Ctrl+O", self.load_preset),
                          ("Ctrl+S", self.save_preset), ("Ctrl+R", self.randomize), ("Ctrl+F", lambda: (self.search.setFocus(), self.search.selectAll())),
                          ("Ctrl+,", self.open_settings), ("F1", self.open_help), ("Ctrl+Q", self.close)):
            QShortcut(QKeySequence(seq), self, activated=slot)

    # ================================================================ state
    def set(self, key, val):
        if self.P.get(key) == val:
            return
        self.P[key] = val
        if key in ("overlay_mode", "gradient", "glass", "border", "style", "fill", "cover_area", "cover_fit"):
            self._sync_enabled()
            if key in ("overlay_mode", "style", "fill", "cover_fit"):
                self._sync_ui()
        self._crossfade = key == "style"
        self.refresh()

    def set_color1(self, c):
        self.P["color1"] = c; self.w["color1"].set(c); self.refresh()

    def set_color2(self, c):
        self.P["color2"] = c; self.w["color2"].set(c)
        if not self.P["gradient"]:
            self.P["gradient"] = True; self._sync_ui()
        self.refresh()

    def _sync_ui(self):
        if not self.ui_ready:
            return
        P = self.P; W = self.w
        for k, wdg in W.items():
            if isinstance(wdg, SliderRow):
                wdg.set(P[k])
            elif isinstance(wdg, QCheckBox):
                wdg.blockSignals(True); wdg.setChecked(bool(P[k])); wdg.blockSignals(False)
            elif isinstance(wdg, ColorButton):
                wdg.set(P[k])
        W["mode_btns"][P["overlay_mode"]].setChecked(True)
        W["fill_btns"][P["fill"]].setChecked(True)
        W["fit_btns"].get(P["cover_fit"], W["fit_btns"]["cobrir"]).setChecked(True)
        for k in ("cover_area", "cover_blend", "emblem_style"):
            set_combo_data(W[k], P[k])
        sel = self.style_btns.get(P["style"], self.style_btns["moderna"])
        if not sel.isChecked():
            sel.setChecked(True)
        if P["style"] not in self._visible_ids():
            self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
            self.cat_btns["all"].setChecked(True); self._apply_filter()
        QTimer.singleShot(0, lambda: self.shape_scroll.ensureWidgetVisible(sel, 0, 20) if self.ui_ready else None)
        self._sync_enabled()
        for g in self.glows:
            g.refresh()

    def _sync_enabled(self):
        P = self.P; W = self.w
        W["color2"].setEnabled(P["gradient"]); W["grad_angle"].setEnabled(P["gradient"])
        W["glass_amount"].setEnabled(P["glass"])
        W["border_color"].setEnabled(P["border"]); W["border_width"].setEnabled(P["border"])
        has = P["overlay_mode"] != "nenhum"
        for k in ("ov_x", "ov_y", "ov_scale", "ov_rot", "ov_shadow"):
            W[k].setEnabled(has)
        W["emblem_style"].setEnabled(P["overlay_mode"] == "frente")
        ov_img = fc.load_overlay(P["overlay_path"]) if P["overlay_path"] else None
        cv_img = fc.load_image(P["cover_path"]) if P["cover_path"] else None
        is_img = P["fill"] == "imagem"
        self.cover_box.setVisible(is_img); self.color_hint.setVisible(is_img)
        W["cover_back_dark"].setEnabled(P["cover_area"] == "toda")
        can_png = has and ov_img is not None
        can_cover = is_img and cv_img is not None
        self.preview.interactive = can_png or can_cover
        both = can_png and can_cover
        self.target_lbl.setVisible(both)
        for bt in self.target_btns.values():
            bt.setVisible(both)
        key = "hint.both" if both else "hint.png" if can_png else "hint.cover" if can_cover else "hint.none"
        self.drag_hint.setText(tr(key))
        self.ov_name.setText(self._nice_name(P["overlay_path"]) if ov_img is not None else tr("png.empty"))
        self.ov_thumb.set_image(ov_img)
        self.cover_name.setText(self._nice_name(P["cover_path"]) if cv_img is not None else tr("cover.none"))
        self.cover_thumb.set_image(cv_img)

    def refresh(self):
        self.t_main.start(); self.t_slow.start()

    def _render_main(self):
        dpr = self.preview.devicePixelRatioF()
        side = int(self.preview.icon_rect().width() * dpr)
        side = max(128, min(side, 1240))
        self.preview.set_image(fc.render(self.P, side), crossfade=self._crossfade)
        self._crossfade = False

    def _render_slow(self):
        ims = fc.render_sizes(self.P, SizeStrip.SIZES, base=512)
        self.strip.set_images([QPixmap.fromImage(fc.pil_to_qimage(i)) for i in ims])
        self.thumb_stale = set(self.style_btns)
        self.t_thumbs.start()

    def _update_strip_visibility(self):
        self.strip.setVisible(self.height() >= 700)   # short screens: hide the size strip

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.ui_ready:
            self._update_strip_visibility()
            self.t_main.start()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == e.Type.WindowStateChange:
            clock().set_visible(not self.isMinimized())

    def showEvent(self, e):
        super().showEvent(e); clock().set_visible(not self.isMinimized())

    def hideEvent(self, e):
        super().hideEvent(e); clock().set_visible(False)

    @staticmethod
    def _nice_name(path):
        if not path:
            return ""
        if path.startswith("embedded:"):
            return tr("msg.embedded")
        n = os.path.basename(path)
        if is_asset(path):
            key = os.path.splitext(n)[0]
            sub = os.path.basename(os.path.dirname(path))
            n = tr(f"sticker.{key}") if sub == "stickers" else tr(f"texture.{key}") if sub == "covers" else n
            return tr("msg.example", name=n)
        return n

    # ---------------------------------------------------------------- images
    def _img_filter(self):
        return f"{tr('dlg.images')} ({IMG_EXT})"

    def pick_cover(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("dlg.pick_cover"), "", self._img_filter())
        if f:
            self._load_cover_file(f)

    def _load_cover_file(self, f):
        if fc.load_image(f) is None:
            QMessageBox.warning(self, APP_NAME, tr("msg.cant_open_image")); return
        self.P["cover_path"] = f; self.P["fill"] = "imagem"
        self.target_btns["capa"].setChecked(True)
        self._sync_ui(); self.refresh()

    def _dropped(self, f):
        if f.lower().endswith(".json"):
            self._open_preset_path(f); return
        if self.P["fill"] == "imagem" and self.target_btns["capa"].isChecked() and self.target_btns["capa"].isVisible():
            self._load_cover_file(f)
        elif self.P["fill"] == "imagem" and self.P["overlay_mode"] == "nenhum":
            self._load_cover_file(f)
        else:
            self._load_overlay_file(f)

    def _target(self, shift):
        P = self.P
        can_png = P["overlay_mode"] != "nenhum" and fc.load_overlay(P["overlay_path"]) is not None
        can_cover = P["fill"] == "imagem" and fc.load_image(P["cover_path"]) is not None
        if can_png and can_cover:
            t = "capa" if self.target_btns["capa"].isChecked() else "png"
            if shift:
                t = "png" if t == "capa" else "capa"
            return t
        return "png" if can_png else ("capa" if can_cover else None)

    def pick_overlay(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("dlg.pick_png"), "", self._img_filter())
        if f:
            self._load_overlay_file(f)

    def _load_overlay_file(self, f):
        if fc.load_overlay(f) is None:
            QMessageBox.warning(self, APP_NAME, tr("msg.cant_open_image")); return
        self.P["overlay_path"] = f
        if self.P["overlay_mode"] == "nenhum":
            self.P["overlay_mode"] = "dentro"
        self.target_btns["png"].setChecked(True)
        self._sync_ui(); self.refresh()

    def center_overlay(self):
        for k, v in (("ov_x", 0), ("ov_y", 0), ("ov_scale", 100), ("ov_rot", 0)):
            self.P[k] = v
        self._sync_ui(); self.refresh()

    def _drag_move(self, dx, dy, shift=False):
        t = self._target(shift)
        if t is None:
            return
        if t == "capa":
            kx, ky = "cover_x", "cover_y"
            lx, ly = fc.cover_limits(self.P)
            self.P[kx] = max(-lx, min(lx, self.P[kx] + dx * 0.95))
            self.P[ky] = max(-ly, min(ly, self.P[ky] + dy * 1.25))
        else:
            kx, ky = "ov_x", "ov_y"
            self.P[kx] = max(-100, min(100, self.P[kx] + dx))
            self.P[ky] = max(-100, min(100, self.P[ky] + dy))
        self.w[kx].set(round(self.P[kx])); self.w[ky].set(round(self.P[ky]))
        self.refresh()

    def _wheel_scale(self, d, shift=False):
        t = self._target(shift)
        if t == "capa":
            self.P["cover_zoom"] = max(10, min(400, self.P["cover_zoom"] + d)); self.w["cover_zoom"].set(self.P["cover_zoom"])
        elif t == "png":
            self.P["ov_scale"] = max(10, min(250, self.P["ov_scale"] + d)); self.w["ov_scale"].set(self.P["ov_scale"])
        self.refresh()

    # ---------------------------------------------------------------- presets
    def _clean_params(self):
        P = dict(self.P)
        for k in ("ov_x", "ov_y", "cover_x", "cover_y"):
            P[k] = round(P[k], 2)
        return P

    def preset_data(self):
        """Preset dict with the PNG and cover images embedded (works on any PC)."""
        P = self._clean_params()
        for pk, bk in (("overlay_path", "overlay_png_base64"), ("cover_path", "cover_img_base64")):
            img = fc.load_image(P[pk]) if P[pk] else None
            if img is not None:
                ba = QByteArray(); buf = QBuffer(ba); buf.open(QIODevice.WriteOnly)
                if img.hasAlphaChannel():
                    img.save(buf, "PNG")
                else:
                    img.save(buf, "JPG", 92)
                P[bk] = base64.b64encode(bytes(ba)).decode("ascii")
        return {"app": APP_NAME, "format": 1, "version": __version__, "params": P}

    def save_preset(self):
        f, _ = QFileDialog.getSaveFileName(self, tr("dlg.save_preset"), os.path.join(presets_dir(), tr("dlg.preset_default_name") + ".dosye.json"),
                                           f"{tr('dlg.preset_filter')} (*.dosye.json)")
        if not f:
            return
        if not f.lower().endswith(".json"):
            f += ".dosye.json"
        try:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(self.preset_data(), fh, ensure_ascii=False, indent=1)
        except OSError as ex:
            QMessageBox.warning(self, APP_NAME, f"{tr('msg.preset_save_fail')}\n\n{ex}"); return
        self.toast.show_message(tr("msg.preset_saved"), f)

    def load_preset(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("dlg.open_preset"), presets_dir(), f"{tr('dlg.preset_filter')} ({PRESET_EXT})")
        if f:
            self._open_preset_path(f)

    def _open_preset_path(self, f):
        try:
            self.load_preset_file(f)
            self.toast.show_message(tr("msg.preset_loaded"), f)
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"{tr('msg.preset_open_fail')}\n\n{ex}")

    def load_preset_file(self, f):
        """Opens presets from Dosye and from Gerador de Pastas v1–v3 (.pasta.json). Unknown keys are ignored."""
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        raw = data.get("params", {}) if isinstance(data, dict) else {}
        P = fc.default_params(); P.update({k: v for k, v in raw.items() if k in fc.DEFAULTS})
        if P.get("style") not in fc.STYLE_IDS:
            P["style"] = "moderna"
        for k, allowed in (("overlay_mode", ("nenhum", "dentro", "frente")), ("fill", ("cor", "imagem")),
                           ("cover_area", ("toda", "frente")), ("cover_fit", [x for x, _ in fc.COVER_FITS]),
                           ("cover_blend", [x for x, _ in fc.COVER_BLENDS]), ("emblem_style", ("original", "gravado", "branco"))):
            if P.get(k) not in allowed:
                P[k] = fc.DEFAULTS[k]
        for pk, bk in (("overlay_path", "overlay_png_base64"), ("cover_path", "cover_img_base64")):
            b64 = raw.get(bk)
            if b64:
                img = QImage(); img.loadFromData(base64.b64decode(b64))
                if not img.isNull():
                    key = f"embedded:{pk}:{os.path.basename(f)}:{time.time()}"
                    fc.set_overlay_image(key, img); P[pk] = key
        self.P = P; self._sync_ui(); self.refresh()

    def reset(self):
        self.P = start_design(); self._sync_ui(); self.refresh()

    def randomize(self):
        combos = [("#3F3FE0", "#8B5CFF"), ("#F7B733", "#FC4A1A"), ("#8B7BFF", "#4FC3F7"), ("#F43F5E", "#F59E0B"),
                  ("#22C55E", "#14B8A6"), ("#FF7EB3", "#C084FC"), ("#3B82F6", "#22D3EE"), ("#475569", "#1F2937"),
                  ("#F97316", "#EF4444"), ("#06B6D4", "#6366F1"), ("#A3E635", "#22C55E"), ("#FDE68A", "#F59E0B"),
                  ("#E879F9", "#6366F1"), ("#B7794A", "#7C4A2D")]
        c1, c2 = random.choice(combos)
        self.P.update(style=random.choice(fc.STYLE_IDS), color1=c1, color2=c2, gradient=random.random() < 0.6,
                      grad_angle=random.choice([45, 60, 90, 120, 135]), light=random.randint(30, 80), gloss=random.randint(10, 60),
                      glow=random.choice([0, 0, 0, 35, 55]), glow_color=QColor(c1).lighter(130).name(),
                      shadow=random.randint(30, 65), papers=random.random() < 0.5, glass=random.random() < 0.2,
                      mirror=random.random() < 0.25)
        self._crossfade = True
        self._sync_ui(); self.refresh()

    # ---------------------------------------------------------------- export
    def _export_dir(self):
        for d in (self.last_dir, self.settings["export_dir"], pictures_dir()):
            if d and os.path.isdir(d):
                return d
        return os.path.expanduser("~")

    def _ask_save(self, title, name, filt):
        f, _ = QFileDialog.getSaveFileName(self, title, os.path.join(self._export_dir(), name), filt)
        if f:
            self.last_dir = os.path.dirname(f)
        return f

    def export_ico(self):
        f = self._ask_save(tr("dlg.export_ico"), tr("dlg.icon_default_name") + ".ico", f"{tr('dlg.ico_filter')} (*.ico)")
        if not f:
            return
        if not f.lower().endswith(".ico"):
            f += ".ico"
        sizes = self.settings["ico_sizes"]
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            fc.export_ico(self.P, f, sizes)
        except OSError as ex:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, APP_NAME, f"{tr('msg.save_fail')}\n\n{ex}"); return
        QApplication.restoreOverrideCursor()
        self.toast.show_message(tr("msg.ico_done", n=len(sizes), sizes=", ".join(map(str, sizes))), f)

    def export_png(self):
        sz = self.png_size.currentData()
        f = self._ask_save(tr("dlg.export_png"), f"{tr('dlg.icon_default_name')}_{sz}.png", f"{tr('dlg.png_filter')} (*.png)")
        if not f:
            return
        if not f.lower().endswith(".png"):
            f += ".png"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            fc.export_png(self.P, f, sz)
        except OSError as ex:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, APP_NAME, f"{tr('msg.save_fail')}\n\n{ex}"); return
        QApplication.restoreOverrideCursor()
        self.toast.show_message(tr("msg.png_done", s=sz), f)

    def _png_bytes(self, size=512):
        buf = io.BytesIO(); fc.render_size(self.P, size).save(buf, "PNG"); return buf.getvalue()

    def apply_folder_icon(self, d):
        """Applies the current icon to folder d. Returns the method string (see system.folders.apply)."""
        return folders.apply(d, lambda: fc.ico_bytes(fc.render_sizes(self.P, fc.ICO_SIZES)), self._png_bytes)

    def apply_to_folder(self):
        if not folders.supported():
            QMessageBox.information(self, APP_NAME, tr("msg.unsupported", desk=sys.platform)); return
        d = QFileDialog.getExistingDirectory(self, tr("dlg.pick_folder_apply"), self._export_dir())
        if not d:
            return
        try:
            how = self.apply_folder_icon(d)
        except folders.Unsupported as ex:
            QMessageBox.information(self, APP_NAME, tr("msg.unsupported", desk=str(ex))); return
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"{tr('msg.apply_fail')}\n\n{ex}"); return
        if how == "windows":
            self.toast.show_message(tr("msg.apply_done_win"), d)
        else:
            names = {"gio": tr("folder.how_gio"), "kde": tr("folder.how_kde")}
            self.toast.show_message(tr("msg.apply_done_linux", how=", ".join(names.get(m, m) for m in how.split("+"))), d)

    def remove_from_folder(self):
        if not folders.supported():
            QMessageBox.information(self, APP_NAME, tr("msg.unsupported", desk=sys.platform)); return
        d = QFileDialog.getExistingDirectory(self, tr("dlg.pick_folder_remove"), self._export_dir())
        if not d:
            return
        try:
            ok = folders.remove(d)
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"{tr('msg.remove_fail')}\n\n{ex}"); return
        self.toast.show_message(tr("msg.remove_done") if ok else tr("msg.remove_none"), d)

    # ---------------------------------------------------------------- dialogs
    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec():
            self.apply_settings(dlg.result_values)

    def apply_settings(self, values):
        old_lang = self.settings["language"]
        self.settings.data.update(values); self.settings.save()
        from .. import app as app_mod
        app_mod.apply_theme(QApplication.instance(), self.settings)
        set_combo_data(self.png_size, self.settings["png_size"])
        if values.get("language", old_lang) != old_lang:
            self.build_ui()
        else:
            for g in self.glows:
                g.refresh()
            self.header.update(); self.preview.update()
            for b in self.style_btns.values():
                b.update()

    def open_help(self):
        HelpDialog(self).exec()

    def open_about(self):
        AboutDialog(self).exec()

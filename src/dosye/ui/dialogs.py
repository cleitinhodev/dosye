"""Settings, Help and About dialogs."""
import html
import sys

from PySide6.QtCore import Qt, QUrl, QRectF, QPointF
from PySide6.QtGui import QDesktopServices, QIcon, QPainter, QRadialGradient, QColor, QPixmap
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QCheckBox,
                               QTextBrowser, QFileDialog, QWidget, QFrame)

from .. import __version__, APP_NAME, URL_SITE, URL_PROJECT, URL_DONATE, URL_LICENSE, URL_ISSUES
from ..i18n import tr, LANGUAGES, detect_system_language, native_name
from ..paths import asset, pictures_dir
from ..settings import DEFAULTS, ICO_SIZES_ALL
from ..system import windows
from . import theme
from .effects import FX
from .icons import icon
from .widgets import combo, set_combo_data, SliderRow, Section, row, ElidedLabel, GradientTitle

SHORTCUTS = [("Ctrl+E", "act.export_ico"), ("Ctrl+Shift+E", "act.export_png"), ("Ctrl+O", "act.open_preset"),
             ("Ctrl+S", "act.save_preset"), ("Ctrl+R", "act.surprise"), ("Ctrl+F", "act.search"),
             ("Ctrl+,", "act.settings"), ("F1", "act.help"), ("Ctrl+Q", "act.quit")]


class DosyeDialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(asset("icons", "dosye_favicon.ico")))
        self.setObjectName("dialog")

    def showEvent(self, e):
        super().showEvent(e)
        windows.dark_title_bar(self)


class GlowIcon(QWidget):
    """The Dosye icon with a soft golden/violet halo behind it."""

    def __init__(self, path, size):
        super().__init__()
        self.pm = QPixmap(path); self.s = size
        self.setFixedSize(size + 40, size + 40)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        c = QPointF(self.width() / 2, self.height() / 2)
        if FX.glow:
            g = QRadialGradient(c, self.width() / 2)
            g.setColorAt(0, QColor(139, 92, 255, 120)); g.setColorAt(0.55, QColor(255, 201, 60, 40)); g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen); p.setBrush(g); p.drawEllipse(c, self.width() / 2, self.height() / 2)
        p.drawPixmap(QRectF(20, 20, self.s, self.s), self.pm, QRectF(self.pm.rect()))


# ------------------------------------------------------------------ settings

class SettingsDialog(DosyeDialog):
    def __init__(self, parent, settings):
        super().__init__(parent, tr("settings.title"))
        self.settings = settings
        self.setMinimumWidth(520)
        v = QVBoxLayout(self); v.setContentsMargins(22, 20, 22, 18); v.setSpacing(14)
        hh = QHBoxLayout(); hh.setSpacing(10)
        ic = QLabel(); ic.setPixmap(icon("gear", theme.GOLD_LIGHT, 26).pixmap(26, 26)); hh.addWidget(ic)
        t = QLabel(tr("settings.title")); t.setObjectName("dlgTitle"); hh.addWidget(t); hh.addStretch(1)
        v.addLayout(hh)

        s = Section(tr("settings.language"))
        auto = detect_system_language()
        items = [("auto", tr("settings.lang_auto", lang=native_name(auto)))]
        items += [(c, n if n == en else f"{n} — {en}") for c, n, en in LANGUAGES]
        self.lang = combo(items); set_combo_data(self.lang, settings["language"])
        s.add(self.lang)
        note = QLabel(tr("settings.lang_note")); note.setObjectName("hint"); note.setWordWrap(True); s.add(note)
        v.addWidget(s)

        s = Section(tr("settings.appearance"))
        self.anim = QCheckBox(tr("settings.animations")); self.anim.setChecked(settings["animations"]); self.anim.setToolTip(tr("settings.animations_tip"))
        self.reduce = QCheckBox(tr("settings.reduce")); self.reduce.setChecked(settings["reduce_effects"]); self.reduce.setToolTip(tr("settings.reduce_tip"))
        self.reduce.toggled.connect(lambda b: self.anim.setEnabled(not b)); self.anim.setEnabled(not settings["reduce_effects"])
        self.intensity = SliderRow(tr("settings.intensity"), 0, 100, settings["intensity"], "%")
        s.add(self.anim); s.add(self.reduce); s.add(self.intensity)
        v.addWidget(s)

        s = Section(tr("settings.export"))
        self.export_dir = settings["export_dir"]
        rr = QHBoxLayout(); rr.setSpacing(8)
        self.dir_lbl = ElidedLabel("", Qt.ElideMiddle); self.dir_lbl.setObjectName("rowLabel"); rr.addWidget(self.dir_lbl, 1)
        b = QPushButton(tr("settings.choose")); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(self._choose); rr.addWidget(b)
        b2 = QPushButton(tr("settings.clear")); b2.setObjectName("ghost"); b2.setCursor(Qt.PointingHandCursor); b2.clicked.connect(self._clear); rr.addWidget(b2)
        lab = QLabel(tr("settings.export_dir")); lab.setObjectName("rowLabel"); s.add(lab); s.addLayout(rr)
        self._upd_dir()
        self.png = combo([(sz, f"{sz} × {sz} px") for sz in (256, 512, 1024)]); set_combo_data(self.png, settings["png_size"])
        s.addLayout(row(tr("settings.png_size"), self.png))
        lab = QLabel(tr("settings.ico_sizes")); lab.setObjectName("rowLabel"); s.add(lab)
        grid = QGridLayout(); grid.setSpacing(6); self.sizes = {}
        for i, sz in enumerate(ICO_SIZES_ALL):
            cb = QCheckBox(f"{sz}"); cb.setObjectName("plain"); cb.setChecked(sz in settings["ico_sizes"])
            if sz == 256:
                cb.setToolTip(tr("settings.ico_256_tip"))
            grid.addWidget(cb, i // 5, i % 5); self.sizes[sz] = cb
        s.addLayout(grid)
        v.addWidget(s)

        bb = QHBoxLayout(); bb.setSpacing(8)
        rd = QPushButton(tr("settings.restore")); rd.setObjectName("ghost"); rd.clicked.connect(self._restore)
        cancel = QPushButton(tr("common.cancel")); cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("common.save")); ok.setObjectName("primary"); ok.clicked.connect(self._save); ok.setDefault(True)
        for x in (rd, cancel, ok):
            x.setCursor(Qt.PointingHandCursor)
        bb.addWidget(rd); bb.addStretch(1); bb.addWidget(cancel); bb.addWidget(ok)
        v.addLayout(bb)

    def _upd_dir(self):
        self.dir_lbl.setText(self.export_dir or tr("settings.export_dir_default", path=pictures_dir()))

    def _choose(self):
        d = QFileDialog.getExistingDirectory(self, tr("settings.export_dir"), self.export_dir or pictures_dir())
        if d:
            self.export_dir = d; self._upd_dir()

    def _clear(self):
        self.export_dir = ""; self._upd_dir()

    def _restore(self):
        set_combo_data(self.lang, DEFAULTS["language"])
        self.anim.setChecked(DEFAULTS["animations"]); self.reduce.setChecked(DEFAULTS["reduce_effects"])
        self.intensity.set(DEFAULTS["intensity"]); self.export_dir = DEFAULTS["export_dir"]; self._upd_dir()
        set_combo_data(self.png, DEFAULTS["png_size"])
        for sz, cb in self.sizes.items():
            cb.setChecked(sz in DEFAULTS["ico_sizes"])

    def values(self):
        sizes = [sz for sz, cb in self.sizes.items() if cb.isChecked()] or list(DEFAULTS["ico_sizes"])
        return {"language": self.lang.currentData(), "animations": self.anim.isChecked(),
                "reduce_effects": self.reduce.isChecked(), "intensity": self.intensity.s.value(),
                "export_dir": self.export_dir, "png_size": int(self.png.currentData()), "ico_sizes": sizes}

    def _save(self):
        self.result_values = self.values()
        self.accept()


# ------------------------------------------------------------------ help

HELP_SECTIONS = ["start", "shapes", "fill", "png", "effects", "export", "folder", "presets"]


def help_html():
    css = (f"body {{ color: {theme.TEXT}; }} h1 {{ color: #FFFFFF; font-size: 17pt; margin: 0 0 4px 0; }}"
           f"h2 {{ color: {theme.GOLD_LIGHT}; font-size: 12pt; margin: 18px 0 4px 0; }}"
           f"p, li {{ color: {theme.MUTED}; line-height: 140%; }} b {{ color: {theme.TEXT}; }}"
           f"a {{ color: {theme.CYAN}; }} td {{ padding: 3px 12px 3px 0; color: {theme.MUTED}; }}"
           f".key {{ color: {theme.GOLD_LIGHT}; font-weight: 700; }}")
    out = [f"<html><head><style>{css}</style></head><body>"]
    out.append(f"<p>{tr('help.intro')}</p>")
    for sec in HELP_SECTIONS:
        out.append(f"<h2>{html.escape(tr(f'help.{sec}.title'))}</h2><p>{tr(f'help.{sec}.body')}</p>")
    out.append(f"<h2>{html.escape(tr('help.shortcuts.title'))}</h2><table>")
    for key, act in SHORTCUTS:
        k = key.replace("Ctrl", "⌘" if sys.platform == "darwin" else "Ctrl")
        out.append(f"<tr><td class='key'>{k}</td><td>{html.escape(tr(act))}</td></tr>")
    out.append("</table>")
    out.append(f"<h2>{html.escape(tr('help.more.title'))}</h2><p>{tr('help.more.body', site=URL_SITE, project=URL_PROJECT, issues=URL_ISSUES)}</p>")
    out.append("</body></html>")
    return "".join(out)


class HelpDialog(DosyeDialog):
    def __init__(self, parent):
        super().__init__(parent, tr("help.title"))
        self.resize(720, 640)
        v = QVBoxLayout(self); v.setContentsMargins(22, 18, 22, 18); v.setSpacing(10)
        hh = QHBoxLayout(); hh.setSpacing(12)
        lg = QLabel(); pm = QPixmap(asset("icons", "dosye_icon.png"))
        dpr = self.devicePixelRatioF(); pm = pm.scaled(int(56 * dpr), int(56 * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation); pm.setDevicePixelRatio(dpr)
        lg.setPixmap(pm); hh.addWidget(lg)
        col = QVBoxLayout(); col.setSpacing(0)
        t = QLabel(tr("help.title")); t.setObjectName("dlgTitle"); col.addWidget(t)
        st = QLabel(tr("help.subtitle")); st.setObjectName("dlgSub"); col.addWidget(st)
        hh.addLayout(col, 1); v.addLayout(hh)
        card = QFrame(); card.setObjectName("sectionCard"); cl = QVBoxLayout(card); cl.setContentsMargins(16, 8, 8, 8)
        self.browser = QTextBrowser(); self.browser.setOpenExternalLinks(True); self.browser.setHtml(help_html())
        cl.addWidget(self.browser); v.addWidget(card, 1)
        bb = QHBoxLayout(); bb.addStretch(1)
        ok = QPushButton(tr("common.close")); ok.setObjectName("primary"); ok.setCursor(Qt.PointingHandCursor); ok.clicked.connect(self.accept)
        bb.addWidget(ok); v.addLayout(bb)


# ------------------------------------------------------------------ about

class AboutDialog(DosyeDialog):
    LINKS = [("about.site", URL_SITE, "globe"), ("about.project", URL_PROJECT, "github"), ("about.donate", URL_DONATE, "heart")]

    def __init__(self, parent):
        super().__init__(parent, tr("about.title", app=APP_NAME))
        self.setFixedWidth(560)
        v = QVBoxLayout(self); v.setContentsMargins(26, 18, 26, 20); v.setSpacing(6)
        top = QHBoxLayout(); top.setSpacing(16)
        top.addWidget(GlowIcon(asset("icons", "dosye_icon.png"), 128), 0, Qt.AlignTop)
        col = QVBoxLayout(); col.setSpacing(4)
        col.addSpacing(18)
        col.addWidget(GradientTitle(APP_NAME, 26))
        ver = QLabel(tr("about.version", v=__version__)); ver.setObjectName("count"); ver.setFixedHeight(22)
        hv = QHBoxLayout(); hv.addWidget(ver); hv.addStretch(1); col.addLayout(hv)
        d = QLabel(tr("about.desc")); d.setWordWrap(True); d.setObjectName("dlgSub"); col.addWidget(d)
        m = QLabel(tr("about.meaning")); m.setWordWrap(True); m.setObjectName("hint"); col.addWidget(m)
        col.addStretch(1)
        top.addLayout(col, 1); v.addLayout(top)

        card = QFrame(); card.setObjectName("sectionCard"); cl = QVBoxLayout(card); cl.setContentsMargins(14, 10, 14, 10); cl.setSpacing(4)
        self.link_buttons = []
        for key, url, ic in self.LINKS:
            h = QHBoxLayout(); h.setSpacing(10)
            b = QPushButton(icon(ic, theme.PINK if ic == "heart" else theme.GOLD_LIGHT, 18), "  " + tr(key))
            b.setObjectName("heart" if ic == "heart" else "ghost"); b.setCursor(Qt.PointingHandCursor); b.setMinimumWidth(190)
            b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            lk = QPushButton(url.replace("https://", "")); lk.setObjectName("link"); lk.setCursor(Qt.PointingHandCursor)
            lk.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u))); lk.setToolTip(url)
            h.addWidget(b); h.addWidget(lk, 1); cl.addLayout(h)
            self.link_buttons.append((b, url))
        v.addSpacing(8); v.addWidget(card)

        lic = QHBoxLayout(); lic.setSpacing(8)
        li = QLabel(); li.setPixmap(icon("scale", theme.MUTED, 16).pixmap(16, 16)); lic.addWidget(li)
        ll = QLabel(f"{html.escape(tr('about.license'))} — <a style='color:{theme.CYAN}' href='{URL_LICENSE}'>GNU GPL v3</a>")
        ll.setOpenExternalLinks(True); ll.setObjectName("rowLabel"); lic.addWidget(ll); lic.addStretch(1)
        v.addSpacing(6); v.addLayout(lic)
        tn = QLabel(tr("about.translations")); tn.setWordWrap(True); tn.setObjectName("hint"); v.addWidget(tn)
        cp = QLabel(tr("about.copyright", year="2026")); cp.setObjectName("hint"); v.addWidget(cp)
        bb = QHBoxLayout(); bb.addStretch(1)
        ok = QPushButton(tr("common.close")); ok.setObjectName("primary"); ok.setCursor(Qt.PointingHandCursor); ok.clicked.connect(self.accept)
        bb.addWidget(ok); v.addSpacing(6); v.addLayout(bb)

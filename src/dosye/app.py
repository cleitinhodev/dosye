"""Application bootstrap: QApplication, theme, language, window icons."""
import argparse
import os
import sys

from . import __version__, APP_NAME, APP_ID, WIN_APP_USER_MODEL_ID
from .paths import asset
from .settings import Settings
from . import i18n
from .system import windows


def apply_theme(app, settings):
    from .ui import theme
    from .ui.effects import FX, clock
    FX.glow = settings.glow_on
    FX.animations = settings.animations_on
    FX.intensity = settings["intensity"] / 100.0
    app.setStyleSheet(theme.stylesheet(i18n.font_families(i18n.current()), FX.intensity, FX.glow))
    clock().set_enabled(FX.animations)


# Qt's own strings (standard dialog buttons, colour picker, context menus) come from the
# qtbase_*.qm catalogues shipped with PySide6. French-based creoles fall back to French.
_QT_CATALOG = {"ht": "fr", "gcf": "fr", "mfe": "fr"}
_qt_translator = None


def _install_qt_translator(code):
    global _qt_translator
    from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
    app = QCoreApplication.instance()
    if app is None:
        return False
    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)
        _qt_translator = None
    name = _QT_CATALOG.get(code, code)
    if name == "en":
        return True
    t = QTranslator(app)
    if t.load(f"qtbase_{name}", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(t); _qt_translator = t
        return True
    return False


def resolve_language(settings, forced=None):
    """Activate the UI language (forced > saved setting > system) and Qt's matching catalogue."""
    code = forced or settings["language"]
    if code == "auto" or code not in i18n.CODES:
        code = i18n.detect_system_language()
    code = i18n.set_language(code)
    _install_qt_translator(code)
    return code


def _palette(app):
    from PySide6.QtGui import QPalette, QColor
    pal = QPalette()
    for role, col in ((QPalette.Window, "#0C0F30"), (QPalette.WindowText, "#ECEBFF"), (QPalette.Base, "#11154A"),
                      (QPalette.AlternateBase, "#161A50"), (QPalette.Text, "#ECEBFF"), (QPalette.Button, "#1B2060"),
                      (QPalette.ButtonText, "#ECEBFF"), (QPalette.Highlight, "#5B3FD8"), (QPalette.HighlightedText, "#FFFFFF"),
                      (QPalette.ToolTipBase, "#161A50"), (QPalette.ToolTipText, "#ECEBFF"), (QPalette.PlaceholderText, "#7076AE"),
                      (QPalette.Link, "#6FC3FF"), (QPalette.LinkVisited, "#C084FC")):
        pal.setColor(role, QColor(col))
    app.setPalette(pal)


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    ap = argparse.ArgumentParser(prog="dosye", add_help=True)
    ap.add_argument("--selftest", metavar="DIR", help="run the automated self-test and write a report to DIR")
    ap.add_argument("--lang", help="force a UI language for this run (e.g. ht, pt_BR, ja)")
    ap.add_argument("--screenshot", metavar="PNG", help="save a screenshot of the main window and quit")
    ap.add_argument("--size", metavar="WxH", help="initial window size (testing)")
    ap.add_argument("--repair", metavar="DIR", help="restore every Dosye folder icon inside DIR and its subfolders, then exit")
    ap.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    args, qt_args = ap.parse_known_args(argv[1:])

    if args.repair:        # headless: no window, usable from scripts / a terminal
        from .system import foldericon
        r = foldericon.repair_tree(args.repair)
        lines = [f"{st:6} {d}" + (f"  ({err})" if err else "") for d, st, err in r["folders"]]
        lines.append(f"scanned={r['scanned']} found={r['found']} fixed={r['fixed']} ok={r['ok']} failed={r['failed']}")
        try:
            print("\n".join(lines)); sys.stdout.flush()
        except Exception:
            pass
        sys.exit(1 if r["failed"] else 0)

    windows.set_app_user_model_id(WIN_APP_USER_MODEL_ID)
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon, QGuiApplication
    from PySide6.QtWidgets import QApplication
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication([argv[0]] + qt_args)
    app.setApplicationName(APP_NAME); app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__); app.setOrganizationName("Bugzinho")
    app.setDesktopFileName(APP_ID)          # Linux: taskbar/dock uses dosye.desktop (main icon)
    app.setStyle("Fusion")
    _palette(app)
    # The favicon (mascot face) is the title-bar icon of every window; the main icon is the
    # exe/taskbar/desktop-file icon (on Windows we also push it as the window's "big" icon).
    app.setWindowIcon(QIcon(asset("icons", "dosye_favicon.ico")))

    settings = Settings()
    resolve_language(settings, args.lang)
    apply_theme(app, settings)

    from .ui.main_window import MainWindow
    w = MainWindow(settings)
    w.setWindowIcon(QIcon(asset("icons", "dosye_favicon.ico")))
    if args.size:
        sw, sh = (int(x) for x in args.size.lower().split("x"))
        w.setWindowState(Qt.WindowNoState); w.resize(sw, sh)
    w.show()
    windows.dark_title_bar(w)
    windows.set_window_icons(w, asset("icons", "dosye_favicon.ico"), asset("icons", "dosye_icon.ico"))

    if args.selftest:
        from .selftest import run
        QTimer.singleShot(900, lambda: run(w, app, args.selftest))
    elif args.screenshot:
        QTimer.singleShot(1500, lambda: (w.grab().save(args.screenshot), app.quit()))
    ret = app.exec()
    try:
        sys.stdout and sys.stdout.flush()
    except Exception:
        pass
    os._exit(ret)    # skip slow interpreter teardown with large images in memory


if __name__ == "__main__":
    main()

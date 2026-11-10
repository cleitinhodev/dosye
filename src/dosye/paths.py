"""Filesystem locations (resources bundled with the app and per-user folders).

Works the same from a source checkout, an installed package and a PyInstaller
bundle (PyInstaller keeps the package layout under sys._MEIPASS).
"""
import os
import sys

from . import APP_NAME, APP_ID

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(PACKAGE_DIR, "assets")
LOCALES_DIR = os.path.join(PACKAGE_DIR, "i18n", "locales")


def asset(*parts):
    """Absolute path of a bundled asset, e.g. asset("icons", "dosye_icon.png")."""
    return os.path.join(ASSETS_DIR, *parts)


def is_asset(path):
    try:
        return os.path.commonpath([os.path.abspath(path), ASSETS_DIR]) == ASSETS_DIR
    except ValueError:          # different drives on Windows
        return False


def config_dir():
    """Per-user configuration folder (created on demand).

    Windows: %APPDATA%\\Dosye   macOS: ~/Library/Application Support/Dosye
    Linux/BSD: $XDG_CONFIG_HOME/dosye (default ~/.config/dosye)
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
        d = os.path.join(base, APP_NAME)
    elif sys.platform == "darwin":
        d = os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        d = os.path.join(base, APP_ID)
    os.makedirs(d, exist_ok=True)
    return d


def presets_dir():
    d = os.path.join(config_dir(), "presets")
    os.makedirs(d, exist_ok=True)
    return d


def pictures_dir():
    """The user's Pictures folder (falls back to home)."""
    try:
        from PySide6.QtCore import QStandardPaths
        p = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        if p and os.path.isdir(p):
            return p
    except Exception:
        pass
    home = os.path.expanduser("~")
    for name in ("Pictures", "Imagens", "Images"):
        if os.path.isdir(os.path.join(home, name)):
            return os.path.join(home, name)
    return home

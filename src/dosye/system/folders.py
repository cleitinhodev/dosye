"""Facade used by the UI: apply / remove / repair folder icons (see foldericon.py)."""
import sys

from . import IS_WINDOWS, IS_LINUX
from . import foldericon
from .foldericon import Result, repair_tree, iter_repair, repair_folder, is_dosye_folder  # noqa: F401


class Unsupported(Exception):
    """Raised when this OS has no known way to set a folder icon."""


def supported():
    return IS_WINDOWS or IS_LINUX


def apply(folder, make_ico, make_png):
    """make_ico()/make_png() return bytes (rendered lazily). Every format is always written,
    whatever the current OS, so the icon travels with the folder. Returns a foldericon.Result."""
    if not supported():
        raise Unsupported(sys.platform)
    return foldericon.apply(folder, make_ico(), make_png())


def remove(folder):
    if not supported():
        raise Unsupported(sys.platform)
    return foldericon.remove(folder)

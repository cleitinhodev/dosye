"""Cross-platform "apply icon to a folder" facade used by the UI."""
import sys

from . import IS_WINDOWS, IS_LINUX
from . import windows, linux


class Unsupported(Exception):
    """Raised when this OS / desktop has no known way to set a folder icon."""


def supported():
    return IS_WINDOWS or IS_LINUX


def apply(folder, make_ico, make_png):
    """make_ico()/make_png() are callables returning bytes (rendered lazily).

    Returns a short machine-readable description of what was done:
    "windows" | "gio" | "kde" | "gio+kde".
    """
    if IS_WINDOWS:
        windows.apply_folder_icon(folder, make_ico())
        return "windows"
    if IS_LINUX:
        methods = linux.apply_folder_icon(folder, make_png())
        if not methods:
            raise Unsupported(linux.desktop_name())
        return "+".join(methods)
    raise Unsupported(sys.platform)


def remove(folder):
    if IS_WINDOWS:
        return windows.remove_folder_icon(folder)
    if IS_LINUX:
        return linux.remove_folder_icon(folder)
    raise Unsupported(sys.platform)

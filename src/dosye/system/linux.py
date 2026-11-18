"""Linux desktop helpers. Folder icons live in foldericon.py (cross-OS) since 1.1.0."""
import os

from .foldericon import gio_available, _gio  # noqa: F401  (kept for older imports)


def desktop_name():
    return os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "?"

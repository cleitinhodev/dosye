"""Linux folder icons.

* GNOME Files (Nautilus), Nemo, Caja and other GIO-based file managers read the
  ``metadata::custom-icon`` attribute (set with ``gio set``).
* KDE Dolphin reads ``Icon=`` from a ``.directory`` file inside the folder.

We store the picture as a hidden PNG inside the folder itself, so the icon keeps
working if Dosye is removed, and we do both methods so it works on either desktop.
"""
import os
import shutil
import subprocess
import time
from urllib.parse import quote

ICON_PREFIX = ".dosye_icon_"
DIRECTORY_FILE = ".directory"


def desktop_name():
    return os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "?"


def _file_uri(path):
    return "file://" + quote(os.path.abspath(path))


def _gio(*args):
    gio = shutil.which("gio")
    if not gio:
        return None
    try:
        r = subprocess.run([gio, *args], capture_output=True, text=True, timeout=10)
        return r
    except (OSError, subprocess.SubprocessError):
        return None


def _our_pngs(folder):
    return [n for n in os.listdir(folder) if n.startswith(ICON_PREFIX) and n.endswith(".png")]


def _remove_pngs(folder):
    for n in _our_pngs(folder):
        try:
            os.remove(os.path.join(folder, n))
        except OSError:
            pass


def _read_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def _write_directory_icon(folder, icon_path):
    """Sets Icon= in [Desktop Entry] of .directory, preserving everything else."""
    path = os.path.join(folder, DIRECTORY_FILE)
    lines = _read_lines(path)
    out, in_entry, done, has_entry = [], False, False, False
    for ln in lines:
        s = ln.strip()
        if s.startswith("["):
            if in_entry and not done:
                out.append("Icon=" + icon_path); done = True
            in_entry = s == "[Desktop Entry]"; has_entry |= in_entry
        elif in_entry and s.startswith("Icon="):
            if not done:
                out.append("Icon=" + icon_path); done = True
            continue
        out.append(ln)
    if in_entry and not done:
        out.append("Icon=" + icon_path); done = True
    if not has_entry:
        out = ["[Desktop Entry]", "Icon=" + icon_path] + ([""] + out if out else [])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def _clear_directory_icon(folder):
    path = os.path.join(folder, DIRECTORY_FILE)
    lines = _read_lines(path)
    if not lines:
        return False
    out, in_entry, removed = [], False, False
    for ln in lines:
        s = ln.strip()
        if s.startswith("["):
            in_entry = s == "[Desktop Entry]"
        elif in_entry and s.startswith("Icon=") and ICON_PREFIX in s:
            removed = True
            continue
        out.append(ln)
    if not removed:
        return False
    meaningful = [l for l in out if l.strip() and l.strip() != "[Desktop Entry]"]
    if meaningful:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
    else:
        os.remove(path)
    return True


def apply_folder_icon(folder, png_bytes):
    """Returns the list of methods that worked, e.g. ["gio", "kde"]. Raises on I/O errors."""
    folder = os.path.abspath(folder)
    _remove_pngs(folder)
    icon_path = os.path.join(folder, f"{ICON_PREFIX}{int(time.time())}.png")
    with open(icon_path, "wb") as fh:
        fh.write(png_bytes)
    methods = []
    r = _gio("set", folder, "metadata::custom-icon", _file_uri(icon_path))
    if r is not None and r.returncode == 0:
        methods.append("gio")
    try:
        _write_directory_icon(folder, icon_path)
        methods.append("kde")
    except OSError:
        pass
    try:
        os.utime(folder, None)       # nudges file managers to refresh the folder
    except OSError:
        pass
    return methods


def remove_folder_icon(folder):
    folder = os.path.abspath(folder)
    had = bool(_our_pngs(folder))
    r = _gio("info", "-a", "metadata::custom-icon", folder)
    if r is not None and r.returncode == 0 and (ICON_PREFIX in r.stdout or ".icone_pasta_" in r.stdout):
        _gio("set", "-t", "unset", folder, "metadata::custom-icon")
        had = True
    try:
        had |= _clear_directory_icon(folder)
    except OSError:
        pass
    _remove_pngs(folder)
    try:
        os.utime(folder, None)
    except OSError:
        pass
    return had


def gio_available():
    return shutil.which("gio") is not None

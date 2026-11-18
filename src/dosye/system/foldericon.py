"""Portable folder icons: one set of files inside the folder that works on Windows and Linux.

When an icon is applied (on any OS) the folder receives::

    .dosye_icon_<ts>.ico   hidden icon for Windows Explorer (new name each time = no stale cache)
    .dosye_icon_<ts>.png   the same picture as PNG for Linux file managers
    desktop.ini            [.ShellClassInfo] IconResource=<relative .ico>,0   (UTF-16, CRLF)
    .directory             [Desktop Entry] Icon=./<relative .png>             (KDE, PCManFM-Qt)

plus, where the file system allows it, the DOS attributes Windows needs (folder Read-only,
files Hidden+System) -- set from Windows *or* from Linux on FAT32/exFAT/NTFS -- and the GIO
``metadata::custom-icon`` attribute used by GNOME Files, Nemo, Caja and Thunar (that one is
stored per user on the local machine, so it never travels with the folder).

Because every path is relative and every piece can be rebuilt from either picture,
:func:`repair_tree` restores icons on another computer after a copy that lost the folder
attribute (Explorer copies, zip files, cloud sync, Linux->Windows) or the GIO metadata.
Folders made by Dosye 1.0.0 and Gerador de Pastas (``.icone_pasta_*``) are recognised too.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import quote

from . import dosattr

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

ICON_PREFIX = ".dosye_icon_"
LEGACY_PREFIXES = (ICON_PREFIX, ".icone_pasta_")
DESKTOP_INI = "desktop.ini"
DIRECTORY_FILE = ".directory"
_ICON_KEYS = ("iconresource", "iconfile", "iconindex")
_SKIP_DIRS = {"$recycle.bin", "system volume information", "$windows.~bt", "$windows.~ws", "lost+found",
              "node_modules", ".git", ".cache", ".trash", ".local"}
# Only skipped when they sit at the top of a drive / the file system root.
_SKIP_TOP = {"proc", "sys", "dev", "run", "snap", "windows", "program files", "program files (x86)", "programdata",
             "$sysreset", "recovery"}
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


class Result:
    """What apply()/repair_folder() achieved in one folder."""

    def __init__(self, folder):
        self.folder = folder
        self.files = []            # names written
        self.win_attr = False      # folder carries the attribute Windows needs (or we're not able to tell)
        self.win_attr_possible = False
        self.gio = False           # GIO metadata set (GNOME Files, Nemo, Caja, Thunar)
        self.changed = False

    @property
    def methods(self):
        m = ["windows" if self.win_attr else "windows-files", "kde"]
        if self.gio:
            m.append("gio")
        return m

    def __repr__(self):
        return f"Result({self.folder!r}, win_attr={self.win_attr}, gio={self.gio}, changed={self.changed})"


# ------------------------------------------------------------------ helpers
def _is_ours(name):
    return name.startswith(LEGACY_PREFIXES) and name.lower().endswith((".ico", ".png"))


def our_files(folder):
    try:
        return sorted(n for n in os.listdir(folder) if _is_ours(n))
    except OSError:
        return []


def is_dosye_folder(folder):
    return bool(our_files(folder))


def _stamp(name):
    m = re.search(r"_(\d+)\.(ico|png)$", name, re.I)
    return int(m.group(1)) if m else 0


def _remove(path):
    if not os.path.lexists(path):
        return
    dosattr.clear(path)
    try:
        os.remove(path)
    except OSError:
        pass


def _write_bytes(path, data):
    if os.path.exists(path):
        dosattr.clear(path)            # Windows: can't overwrite a hidden/system file
    with open(path, "wb") as fh:
        fh.write(data)


def _decode_ini(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("mbcs" if IS_WINDOWS else "cp1252", errors="replace")


def _read_ini_lines(path):
    try:
        with open(path, "rb") as fh:
            return _decode_ini(fh.read()).splitlines()
    except OSError:
        return []


def _ini_without_icon(lines):
    """Drops our icon keys from [.ShellClassInfo]; keeps every other key and section."""
    out, in_sci = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith("["):
            in_sci = s.lower() == "[.shellclassinfo]"
            out.append(ln); continue
        if in_sci and s.split("=", 1)[0].strip().lower() in _ICON_KEYS:
            continue
        out.append(ln)
    return out


def _drop_empty_sections(lines):
    out, pending = [], None
    for ln in lines:
        s = ln.strip()
        if s.startswith("["):
            pending = [ln]; continue
        if pending is not None:
            if not s:
                continue
            if out:
                out.append("")
            out.extend(pending); pending = None
        if s or (out and out[-1].strip()):
            out.append(ln)
    return out


def _ini_meaningful(lines):
    return [l for l in lines if l.strip() and not l.strip().startswith((";", "["))]


def desktop_ini_text(ico_name, existing_lines=()):
    keep = _ini_without_icon(existing_lines)
    icon = [f"IconResource={ico_name},0", f"IconFile={ico_name}", "IconIndex=0"]
    out, done = [], False
    for ln in keep:
        out.append(ln)
        if not done and ln.strip().lower() == "[.shellclassinfo]":
            out.extend(icon); done = True
    if not done:
        out = ["[.ShellClassInfo]"] + icon + ([""] + out if out else [])
    while out and not out[-1].strip():
        out.pop()
    return "\r\n".join(out) + "\r\n"


def _write_desktop_ini(folder, ico_name):
    path = os.path.join(folder, DESKTOP_INI)
    text = desktop_ini_text(ico_name, _read_ini_lines(path))
    # UTF-16 LE with BOM is what Explorer itself writes; written in binary so CRLF stays CRLF.
    _write_bytes(path, b"\xff\xfe" + text.encode("utf-16-le"))
    return path


def _clear_desktop_ini(folder):
    path = os.path.join(folder, DESKTOP_INI)
    lines = _read_ini_lines(path)
    if not lines:
        return False
    ours = any(s.split("=", 1)[0].strip().lower() in _ICON_KEYS and any(p in s for p in LEGACY_PREFIXES)
               for s in (l.strip() for l in lines))
    if not ours:
        return False
    rest = _drop_empty_sections(_ini_without_icon(lines))
    if _ini_meaningful(rest):
        _write_bytes(path, b"\xff\xfe" + ("\r\n".join(rest).rstrip() + "\r\n").encode("utf-16-le"))
        dosattr.change(path, add=dosattr.HIDDEN | dosattr.SYSTEM)
    else:
        _remove(path)
    return True


def _read_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def directory_text(icon_value, existing_lines=()):
    """Sets Icon= in [Desktop Entry] of a .directory file, preserving everything else."""
    out, in_entry, done, has_entry = [], False, False, False
    for ln in existing_lines:
        s = ln.strip()
        if s.startswith("["):
            if in_entry and not done:
                out.append("Icon=" + icon_value); done = True
            in_entry = s == "[Desktop Entry]"; has_entry |= in_entry
        elif in_entry and s.startswith("Icon="):
            if not done:
                out.append("Icon=" + icon_value); done = True
            continue
        out.append(ln)
    if in_entry and not done:
        out.append("Icon=" + icon_value)
    if not has_entry:
        out = ["[Desktop Entry]", "Icon=" + icon_value] + ([""] + out if out else [])
    return "\n".join(out) + "\n"


def _write_directory(folder, png_name):
    path = os.path.join(folder, DIRECTORY_FILE)
    _write_bytes(path, directory_text("./" + png_name, _read_lines(path)).encode("utf-8"))
    return path


def _clear_directory(folder):
    path = os.path.join(folder, DIRECTORY_FILE)
    lines = _read_lines(path)
    if not lines:
        return False
    out, in_entry, removed = [], False, False
    for ln in lines:
        s = ln.strip()
        if s.startswith("["):
            in_entry = s == "[Desktop Entry]"
        elif in_entry and s.startswith("Icon=") and any(p in s for p in LEGACY_PREFIXES):
            removed = True
            continue
        out.append(ln)
    if not removed:
        return False
    if [l for l in out if l.strip() and l.strip() != "[Desktop Entry]"]:
        _write_bytes(path, ("\n".join(out) + "\n").encode("utf-8"))
    else:
        _remove(path)
    return True


# ------------------------------------------------------------------ GIO (GNOME Files, Nemo, Caja, Thunar)
def gio_available():
    return IS_LINUX and shutil.which("gio") is not None


def _gio(*args):
    gio = shutil.which("gio") if IS_LINUX else None
    if not gio:
        return None
    try:
        return subprocess.run([gio, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None


def _file_uri(path):
    return "file://" + quote(os.path.abspath(path))


def gio_get(folder):
    r = _gio("info", "-a", "metadata::custom-icon", folder)
    if r is None or r.returncode != 0:
        return None
    for ln in r.stdout.splitlines():
        if "metadata::custom-icon:" in ln:
            return ln.split("metadata::custom-icon:", 1)[1].strip()
    return ""


def _gio_set(folder, png_path):
    if not gio_available():
        return False
    want = _file_uri(png_path)
    if gio_get(folder) == want:
        return True
    r = _gio("set", folder, "metadata::custom-icon", want)
    return r is not None and r.returncode == 0


def _gio_unset_ours(folder):
    cur = gio_get(folder)
    if cur and any(p in cur for p in LEGACY_PREFIXES):
        _gio("set", "-t", "unset", folder, "metadata::custom-icon")
        return True
    return False


# ------------------------------------------------------------------ attributes
def _set_attributes(folder, names, res):
    """Hidden(+System) on our files, Read-only on the folder -- written last on purpose."""
    for n in names:
        dosattr.change(os.path.join(folder, n), add=dosattr.HIDDEN | dosattr.SYSTEM)
    a = dosattr.change(folder, add=dosattr.READONLY)
    if a is not None and not a & dosattr.READONLY:
        # Explorer accepts Read-only *or* System on the folder; some file systems / Wine
        # won't keep Read-only on a directory, so fall back to System.
        a = dosattr.change(folder, add=dosattr.SYSTEM)
    res.win_attr_possible = a is not None
    res.win_attr = bool(a is not None and a & (dosattr.READONLY | dosattr.SYSTEM))


def _notify(folder):
    if not IS_WINDOWS:
        try:
            os.utime(folder, None)       # nudges Linux file managers to re-read the folder
        except OSError:
            pass
        return
    try:
        import ctypes
        sh = ctypes.windll.shell32
        sh.SHChangeNotify(0x00002000, 0x0005, ctypes.c_wchar_p(folder), None)   # SHCNE_UPDATEITEM | SHCNF_PATHW
        sh.SHChangeNotify(0x00001000, 0x0005, ctypes.c_wchar_p(folder), None)   # SHCNE_UPDATEDIR
        sh.SHChangeNotify(0x08000000, 0x0000, None, None)                        # SHCNE_ASSOCCHANGED
    except Exception:
        pass


# ------------------------------------------------------------------ image conversion (for repair)
def png_to_ico(png_bytes):
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    buf = io.BytesIO()
    sizes = [(s, s) for s in ICO_SIZES if s <= max(im.size)] or [(16, 16)]
    im.save(buf, "ICO", sizes=sizes)
    return buf.getvalue()


def ico_to_png(ico_bytes, size=256):
    from PIL import Image
    im = Image.open(io.BytesIO(ico_bytes))
    try:
        best = max(im.info.get("sizes") or [im.size])
        im.size = best
    except Exception:
        pass
    im = im.convert("RGBA")
    if max(im.size) > size:
        im = im.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------ public API
def _install(folder, base, ico_bytes, png_bytes, res):
    """Writes the files for icon *base* (name without extension) and sets attributes/metadata."""
    ico_name, png_name = base + ".ico", base + ".png"
    dosattr.change(folder, remove=dosattr.READONLY)     # exFAT/vfat 'rodir': keep the folder writable meanwhile
    try:
        if ico_bytes is not None:
            _write_bytes(os.path.join(folder, ico_name), ico_bytes); res.files.append(ico_name)
        if png_bytes is not None:
            _write_bytes(os.path.join(folder, png_name), png_bytes); res.files.append(png_name)
        _write_desktop_ini(folder, ico_name)
        _write_directory(folder, png_name)
    finally:
        _set_attributes(folder, [ico_name, png_name, DESKTOP_INI, DIRECTORY_FILE], res)
    res.gio = _gio_set(folder, os.path.join(folder, png_name))
    _notify(folder)


def apply(folder, ico_bytes, png_bytes):
    """Applies a new icon to *folder* in every format. Raises OSError if the folder isn't writable."""
    folder = os.path.abspath(folder)
    res = Result(folder)
    dosattr.change(folder, remove=dosattr.READONLY)
    for n in our_files(folder):
        _remove(os.path.join(folder, n))
    ts = int(time.time())
    base = f"{ICON_PREFIX}{ts}"
    _install(folder, base, ico_bytes, png_bytes, res)
    res.changed = True
    return res


def remove(folder):
    """Removes every Dosye format (1.1, 1.0 and Gerador de Pastas). Returns True if anything was ours."""
    folder = os.path.abspath(folder)
    had = bool(our_files(folder))
    had |= _gio_unset_ours(folder)
    was_ro = dosattr.get(folder)
    dosattr.change(folder, remove=dosattr.READONLY | dosattr.SYSTEM)
    ini_gone = False
    try:
        if _clear_desktop_ini(folder):
            had = True
        ini_gone = not os.path.exists(os.path.join(folder, DESKTOP_INI))
        had |= _clear_directory(folder)
        for n in our_files(folder):
            _remove(os.path.join(folder, n))
    finally:
        # Keep the folder attribute if some other desktop.ini content still needs it.
        if was_ro is not None and not (had and ini_gone):
            dosattr.change(folder, add=was_ro & (dosattr.READONLY | dosattr.SYSTEM))
    _notify(folder)
    return had


def _expected_state_ok(folder, base):
    ini = "\n".join(_read_ini_lines(os.path.join(folder, DESKTOP_INI)))
    ini_ok = f"IconResource={base}.ico,0" in ini
    dot_ok = f"Icon=./{base}.png" in _read_lines(os.path.join(folder, DIRECTORY_FILE))
    return ini_ok and dot_ok


def repair_folder(folder):
    """Rebuilds whatever is missing in one folder that has Dosye icon files. Returns a Result, or None."""
    folder = os.path.abspath(folder)
    names = our_files(folder)
    if not names:
        return None
    res = Result(folder)
    newest = max(names, key=lambda n: (_stamp(n), n))
    base = newest.rsplit(".", 1)[0]
    ico_p, png_p = os.path.join(folder, base + ".ico"), os.path.join(folder, base + ".png")
    ico = png = None
    if not os.path.exists(ico_p) or not os.path.exists(png_p):
        src = ico_p if os.path.exists(ico_p) else png_p
        with open(src, "rb") as fh:
            data = fh.read()
        if src == ico_p:
            png = ico_to_png(data)
        else:
            ico = png_to_ico(data)
    stale = [n for n in names if n.rsplit(".", 1)[0] != base]
    attrs = dosattr.get(folder)
    attr_ok = attrs is None or bool(attrs & (dosattr.READONLY | dosattr.SYSTEM))
    gio_ok = not gio_available() or gio_get(folder) == _file_uri(png_p)
    if ico is None and png is None and not stale and attr_ok and gio_ok and _expected_state_ok(folder, base):
        res.win_attr = attrs is not None; res.win_attr_possible = attrs is not None
        res.gio = gio_available()
        return res
    dosattr.change(folder, remove=dosattr.READONLY)
    for n in stale:
        _remove(os.path.join(folder, n))
    _install(folder, base, ico, png, res)
    res.changed = True
    return res


def _is_top(d):
    return os.path.dirname(d) == d          # "/" or "C:\\"


def _skip_dir(entry, parent_is_top):
    n = entry.name.lower()
    if n in _SKIP_DIRS or n.startswith(".trash-") or (parent_is_top and n in _SKIP_TOP):
        return True
    try:
        if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
            return True
    except OSError:
        return True
    return False


def iter_repair(root, cancelled=lambda: False):
    """Walks *root* and its subfolders, repairing every Dosye folder found.

    Yields ``(scanned_count, folder, result_or_None)`` for each folder visited, so a UI can show
    progress and stop early. Symlinks are not followed; unreadable folders are skipped.
    """
    root = os.path.abspath(root)
    stack, scanned = [root], 0
    while stack:
        if cancelled():
            return
        d = stack.pop()
        scanned += 1
        res = None
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            yield scanned, d, None
            continue
        if any(e.is_file(follow_symlinks=False) and _is_ours(e.name) for e in entries):
            try:
                res = repair_folder(d)
            except Exception as ex:      # keep going; report the folder as failed
                res = ex
        yield scanned, d, res
        top = _is_top(d)
        subs = []
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False) and not _skip_dir(e, top):
                    subs.append(e.path)
            except OSError:
                pass
        stack.extend(sorted(subs, reverse=True))


def repair_tree(root, cancelled=lambda: False):
    """Synchronous helper. Returns dict(scanned, found, fixed, ok, failed, folders=[...])."""
    out = {"scanned": 0, "found": 0, "fixed": 0, "ok": 0, "failed": 0, "folders": []}
    for scanned, d, res in iter_repair(root, cancelled):
        out["scanned"] = scanned
        if res is None:
            continue
        out["found"] += 1
        if isinstance(res, Exception):
            out["failed"] += 1; out["folders"].append((d, "failed", str(res)))
        elif res.changed:
            out["fixed"] += 1; out["folders"].append((d, "fixed", ""))
        else:
            out["ok"] += 1; out["folders"].append((d, "ok", ""))
    return out

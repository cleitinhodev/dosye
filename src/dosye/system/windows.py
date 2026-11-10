"""Windows-only helpers. Importing this module is safe anywhere; functions no-op off Windows."""
import ctypes
import os
import sys
import time

IS_WINDOWS = sys.platform == "win32"

# Our hidden icon files inside the target folder. Older Gerador de Pastas builds used ".icone_pasta_".
ICON_PREFIX = ".dosye_icon_"
LEGACY_PREFIXES = (ICON_PREFIX, ".icone_pasta_")

FILE_ATTRIBUTE_READONLY, FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_SYSTEM, FILE_ATTRIBUTE_NORMAL = 0x1, 0x2, 0x4, 0x80


def set_app_user_model_id(app_id):
    """Groups our windows under our own taskbar button (and its icon) instead of python.exe's."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def dark_title_bar(widget):
    """Asks DWM for a dark title bar (Windows 10 1809+ / 11)."""
    if not IS_WINDOWS:
        return
    try:
        hwnd = int(widget.winId())
        v = ctypes.c_int(1)
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (new / pre-20H1)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), 4) == 0:
                break
        # Windows 11: caption colour matching the header (COLORREF = 0x00BBGGRR)
        cap = ctypes.c_int(0x00240C0B)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(cap), 4)
    except Exception:
        pass


def set_window_icons(widget, small_ico, big_ico):
    """Title bar uses the small icon (favicon); taskbar / Alt+Tab use the big one (main icon)."""
    if not IS_WINDOWS:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        hwnd = ctypes.c_void_p(int(widget.winId()))
        IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x0080
        try:
            dpi = user32.GetDpiForWindow(hwnd)
        except Exception:
            dpi = 96
        sm = max(16, round(16 * dpi / 96)); bg = max(32, round(32 * dpi / 96))
        h_small = user32.LoadImageW(None, small_ico, IMAGE_ICON, sm, sm, LR_LOADFROMFILE)
        h_big = user32.LoadImageW(None, big_ico, IMAGE_ICON, bg, bg, LR_LOADFROMFILE)
        if h_small:
            user32.SendMessageW(hwnd, WM_SETICON, ctypes.c_void_p(0), ctypes.c_void_p(h_small))
        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ctypes.c_void_p(1), ctypes.c_void_p(h_big))
        return bool(h_small and h_big)
    except Exception:
        return False


# ------------------------------------------------------------ folder icons (desktop.ini)

def _setattr(path, attr):
    ctypes.windll.kernel32.SetFileAttributesW(str(path), attr)


def _getattr(path):
    return ctypes.windll.kernel32.GetFileAttributesW(str(path))


def _notify(folder):
    try:
        sh = ctypes.windll.shell32
        sh.SHChangeNotify(0x00002000, 0x0005, ctypes.c_wchar_p(folder), None)   # SHCNE_UPDATEITEM
        sh.SHChangeNotify(0x08000000, 0x0000, None, None)                        # SHCNE_ASSOCCHANGED
    except Exception:
        pass


def _our_icons(folder):
    return [n for n in os.listdir(folder) if n.startswith(LEGACY_PREFIXES) and n.endswith(".ico")]


def _remove_old_icons(folder):
    for n in _our_icons(folder):
        p = os.path.join(folder, n)
        _setattr(p, FILE_ATTRIBUTE_NORMAL)
        try:
            os.remove(p)
        except OSError:
            pass


def apply_folder_icon(folder, ico):
    """Writes a hidden .ico + desktop.ini (keeps other desktop.ini sections)."""
    folder = os.path.abspath(folder)
    _remove_old_icons(folder)
    name = f"{ICON_PREFIX}{int(time.time())}.ico"   # new name every time defeats the icon cache
    icon_path = os.path.join(folder, name)
    with open(icon_path, "wb") as f:
        f.write(ico)
    _setattr(icon_path, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    ini = os.path.join(folder, "desktop.ini")
    lines = []
    if os.path.exists(ini):
        _setattr(ini, FILE_ATTRIBUTE_NORMAL)
        try:
            raw = open(ini, "rb").read()
            txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("mbcs", errors="ignore")
            skip = False
            for ln in txt.splitlines():
                s = ln.strip()
                if s.startswith("["):
                    skip = s.lower() == "[.shellclassinfo]"
                if not skip and s:
                    lines.append(ln)
        except Exception:
            lines = []
    content = "[.ShellClassInfo]\r\nIconResource=" + name + ",0\r\n" + "\r\n".join(lines) + ("\r\n" if lines else "")
    with open(ini, "w", encoding="utf-16") as f:
        f.write(content)
    _setattr(ini, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    a = _getattr(folder)
    if a != 0xFFFFFFFF:
        _setattr(folder, a | FILE_ATTRIBUTE_READONLY)
    _notify(folder)


def remove_folder_icon(folder):
    folder = os.path.abspath(folder)
    ini = os.path.join(folder, "desktop.ini")
    had = bool(_our_icons(folder))
    _remove_old_icons(folder)
    if had and os.path.exists(ini):
        _setattr(ini, FILE_ATTRIBUTE_NORMAL)
        try:
            os.remove(ini)
        except OSError:
            pass
        a = _getattr(folder)
        if a != 0xFFFFFFFF:
            _setattr(folder, a & ~FILE_ATTRIBUTE_READONLY)
    _notify(folder)
    return had

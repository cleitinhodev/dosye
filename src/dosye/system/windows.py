"""Windows-only helpers. Importing this module is safe anywhere; functions no-op off Windows."""
import ctypes
import sys

IS_WINDOWS = sys.platform == "win32"


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

# Folder icons moved to foldericon.py (cross-OS) and dosattr.py (attributes) in 1.1.0.

"""Read/write the DOS attributes (Read-only, Hidden, System) that Windows uses to decide
whether a folder's desktop.ini is honoured -- from Windows *and* from Linux.

Backends, tried in order on Linux:

* FAT32 / exFAT (vfat, exfat drivers): ``FAT_IOCTL_GET/SET_ATTRIBUTES``.  exFAT supports
  them since Linux 6.7.  Setting the *System* bit may be refused (exFAT needs
  CAP_LINUX_IMMUTABLE; vfat with ``sys_immutable``), so we retry without it -- Windows only
  needs the folder's Read-only bit.
* NTFS (ntfs-3g and the kernel ntfs3 driver): the ``system.ntfs_attrib_be`` extended
  attribute (32-bit big-endian FILE_ATTRIBUTE_* mask).
* Anything else (ext4, btrfs, xfs, ...) stores no DOS attributes: functions return False.

Every function is best-effort and never raises.
"""
import os
import sys

IS_WINDOWS = sys.platform == "win32"

READONLY, HIDDEN, SYSTEM, ARCHIVE = 0x01, 0x02, 0x04, 0x20
_MASK = READONLY | HIDDEN | SYSTEM

# linux/msdos_fs.h: _IOR('r', 0x10, __u32) / _IOW('r', 0x11, __u32)
FAT_IOCTL_GET_ATTRIBUTES = 0x80047210
FAT_IOCTL_SET_ATTRIBUTES = 0x40047211
_NTFS_XATTR = "system.ntfs_attrib_be"


# ------------------------------------------------------------------ Windows
def _win_get(path):
    import ctypes
    a = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    return None if a == 0xFFFFFFFF else a


def _win_set(path, value):
    import ctypes
    return bool(ctypes.windll.kernel32.SetFileAttributesW(str(path), value or 0x80))   # 0x80 = NORMAL


# ------------------------------------------------------------------ Linux FAT/exFAT
def _fat_open(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _fat_get(path):
    try:
        import fcntl, struct
        fd = _fat_open(path)
        try:
            buf = fcntl.ioctl(fd, FAT_IOCTL_GET_ATTRIBUTES, b"\0\0\0\0")
            return struct.unpack("I", buf)[0]
        finally:
            os.close(fd)
    except (OSError, ImportError):
        return None


def _fat_set(path, value):
    try:
        import fcntl, struct
        fd = _fat_open(path)
        try:
            fcntl.ioctl(fd, FAT_IOCTL_SET_ATTRIBUTES, struct.pack("I", value))
            return True
        finally:
            os.close(fd)
    except (OSError, ImportError):
        return False


# ------------------------------------------------------------------ Linux NTFS
def _ntfs_get(path):
    try:
        raw = os.getxattr(path, _NTFS_XATTR, follow_symlinks=False)
        return int.from_bytes(raw[:4], "big")
    except (OSError, AttributeError):
        return None


def _ntfs_set(path, value):
    try:
        os.setxattr(path, _NTFS_XATTR, int(value).to_bytes(4, "big"), follow_symlinks=False)
        return True
    except (OSError, AttributeError):
        return False


_BACKENDS = ((_win_get, _win_set),) if IS_WINDOWS else ((_fat_get, _fat_set), (_ntfs_get, _ntfs_set))


def get(path):
    """Returns the attribute mask, or None when the file system keeps no DOS attributes."""
    for g, _s in _BACKENDS:
        v = g(path)
        if v is not None:
            return v
    return None


def supported(path):
    return get(path) is not None


def change(path, add=0, remove=0):
    """Sets/clears bits. Returns the bits actually set afterwards, or None if impossible.

    If the System bit is refused (exFAT/vfat without privileges), retries without it.
    """
    for g, s in _BACKENDS:
        cur = g(path)
        if cur is None:
            continue
        want = (cur | add) & ~remove
        if want == cur:
            return cur & _MASK
        if s(path, want):
            v = g(path)
            return (want if v is None else v) & _MASK
        if add & SYSTEM and s(path, want & ~SYSTEM):
            v = g(path)
            return ((want & ~SYSTEM) if v is None else v) & _MASK
        return None
    return None


def clear(path):
    """Removes Read-only/Hidden/System so the file can be rewritten or deleted (Windows refuses
    to overwrite a hidden/system file with CREATE_ALWAYS and to delete a read-only one)."""
    return change(path, remove=_MASK)

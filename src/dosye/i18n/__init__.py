"""Tiny translation system.

* One flat JSON file per language in ``locales/<code>.json`` (``"key": "text"``).
* ``tr(key, **fmt)`` looks the key up in the current language, then English,
  then returns the key itself, and applies ``str.format(**fmt)``.
* Languages can be switched at runtime (the UI rebuilds itself).

Adding a language: copy ``locales/en.json`` to ``locales/<code>.json``, translate the
values, and add the code to LANGUAGES below. ``python -m dosye.i18n`` prints missing keys.
"""
import json
import os

from ..paths import LOCALES_DIR

FALLBACK = "en"

# (code, native name, english name) — order shown in Settings.
LANGUAGES = [
    ("ht", "Kreyòl ayisyen", "Haitian Creole"),
    ("fr", "Français", "French"),
    ("gcf", "Kréyòl Gwadloup / Matnik", "Antillean Creole"),
    ("mfe", "Kreol Morisien", "Mauritian Creole"),
    ("en", "English", "English"),
    ("pt_BR", "Português (Brasil)", "Portuguese (Brazil)"),
    ("es", "Español", "Spanish"),
    ("de", "Deutsch", "German"),
    ("it", "Italiano", "Italian"),
    ("pl", "Polski", "Polish"),
    ("tr", "Türkçe", "Turkish"),
    ("ru", "Русский", "Russian"),
    ("ja", "日本語", "Japanese"),
    ("zh_CN", "中文 (简体)", "Chinese (Simplified)"),
    ("ko", "한국어", "Korean"),
]
CODES = [c for c, _, _ in LANGUAGES]

_tables = {}
_current = FALLBACK


def _load(code):
    if code not in _tables:
        path = os.path.join(LOCALES_DIR, f"{code}.json")
        try:
            with open(path, encoding="utf-8") as fh:
                _tables[code] = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
        except (OSError, ValueError):
            _tables[code] = {}
    return _tables[code]


def set_language(code):
    global _current
    _current = code if code in CODES else FALLBACK
    _load(_current); _load(FALLBACK)
    return _current


def current():
    return _current


def tr(key, **fmt):
    s = _load(_current).get(key)
    if s is None:
        s = _load(FALLBACK).get(key, key)
    if fmt:
        try:
            s = s.format(**fmt)
        except (KeyError, IndexError, ValueError):
            pass
    return s


def has(key):
    return key in _load(_current) or key in _load(FALLBACK)


def detect_system_language():
    """Best match for the OS locale (e.g. fr_HT -> fr, pt_PT -> pt_BR, zh_TW -> zh_CN)."""
    try:
        from PySide6.QtCore import QLocale
        names = [QLocale.system().name()] + list(QLocale.system().uiLanguages())
    except Exception:
        names = [os.environ.get("LANG", "en")]
    for raw in names:
        n = raw.replace("-", "_").split(".")[0]
        lang = n.split("_")[0].lower()
        if n in CODES:
            return n
        if lang in CODES:
            return lang
        for c in CODES:
            if c.split("_")[0] == lang:
                return c
    return FALLBACK


def missing_keys(code):
    ref = set(_load(FALLBACK))
    return sorted(ref - set(_load(code)))


def extra_keys(code):
    return sorted(set(_load(code)) - set(_load(FALLBACK)))


def bad_placeholders(code):
    """Keys whose {placeholders} differ from English (would break .format)."""
    import re
    rx = re.compile(r"\{(\w+)\}")
    en, t = _load(FALLBACK), _load(code)
    return sorted(k for k in t if k in en and set(rx.findall(en[k])) != set(rx.findall(t[k])))


def native_name(code):
    for c, n, _ in LANGUAGES:
        if c == code:
            return n
    return code


def font_families(code):
    """Preferred UI fonts per script (Windows names first, then Linux Noto)."""
    latin = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans"]
    cjk = {
        "ja": ["Yu Gothic UI", "Meiryo UI", "Noto Sans CJK JP", "Noto Sans JP"],
        "zh_CN": ["Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", "Noto Sans SC", "WenQuanYi Micro Hei"],
        "ko": ["Malgun Gothic", "Noto Sans CJK KR", "Noto Sans KR", "NanumGothic"],
    }
    return (cjk.get(code, []) + latin) if code in cjk else latin + ["Noto Sans CJK JP"]


def tr_in(code, key):
    """Text of key in a specific language (no formatting), falling back to English."""
    return _load(code).get(key) or _load(FALLBACK).get(key, key)

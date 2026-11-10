"""python -m dosye.i18n  -> report missing/extra keys for every language."""
import sys

from . import LANGUAGES, missing_keys, extra_keys, bad_placeholders

# Language names are not ASCII; Windows consoles default to cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = True
for code, name, _ in LANGUAGES:
    m, e, b = missing_keys(code), extra_keys(code), bad_placeholders(code)
    ok &= not (m or b)
    print(f"{code:6} {name:28} missing={len(m):3} extra={len(e):3} bad_placeholders={len(b)}")
    for k in m[:20]:
        print("    missing:", k)
    for k in b:
        print("    placeholder mismatch:", k)
raise SystemExit(0 if ok else 1)

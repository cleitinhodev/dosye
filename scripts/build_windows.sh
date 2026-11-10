#!/usr/bin/env bash
# Build the single-file Windows executable dist/Dosye-<version>-windows-x64.exe
#
# Works in two environments:
#   * natively on Windows (Git Bash / GitHub Actions windows-latest): uses `python`
#   * on Linux through Wine, with a Windows CPython installed in the Wine prefix
#     (set WINE_PYTHON, default 'C:\Python312\python.exe')
#
# Requirements (in that Python): pip install -r requirements-dev.txt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="$(sed -n 's/^__version__ *= *"\(.*\)".*/\1/p' src/dosye/__init__.py)"
OUT="dist/Dosye-${VERSION}-windows-x64.exe"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    PY=(python)
    winpath() { cygpath -w "$1"; } ;;
  *)
    export WINEDEBUG=-all
    PY=(wine "${WINE_PYTHON:-C:\\Python312\\python.exe}")
    winpath() { printf 'Z:%s' "${1//\//\\}"; } ;;
esac

W_ROOT="$(winpath "$ROOT")"
rm -rf build/windows dist/windows
"${PY[@]}" -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name Dosye \
  --icon "$W_ROOT\\src\\dosye\\assets\\icons\\dosye_icon.ico" \
  --version-file "$W_ROOT\\packaging\\windows\\version_info.txt" \
  --paths "$W_ROOT\\src" \
  --add-data "$W_ROOT\\src\\dosye\\assets;dosye\\assets" \
  --add-data "$W_ROOT\\src\\dosye\\i18n\\locales;dosye\\i18n\\locales" \
  --collect-submodules dosye \
  --exclude-module numpy --exclude-module tkinter --exclude-module PySide6.QtNetwork \
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtOpenGL \
  --exclude-module cv2 --exclude-module pygame --exclude-module torch \
  --workpath "$W_ROOT\\build\\windows" --distpath "$W_ROOT\\dist\\windows" --specpath "$W_ROOT\\build\\windows" \
  "$W_ROOT\\packaging\\dosye_launcher.py"

mkdir -p dist
cp -f dist/windows/Dosye.exe "$OUT"
ls -la "$OUT"

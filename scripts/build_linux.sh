#!/usr/bin/env bash
# Build the Linux x86_64 artifacts:
#   dist/Dosye-<v>-linux-x86_64            single-file binary (PyInstaller --onefile)
#   dist/Dosye-<v>-linux-x86_64.tar.gz     binary + .desktop + icon + install.sh
#   dist/Dosye-<v>-x86_64.AppImage         (skipped with NO_APPIMAGE=1)
#
# Requirements: python3 with `pip install -r requirements-dev.txt` (set PYTHON to choose one).
# For maximum compatibility build on the oldest distro you support (CI uses Ubuntu 22.04).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
VERSION="$(sed -n 's/^__version__ *= *"\(.*\)".*/\1/p' src/dosye/__init__.py)"
NAME="Dosye-${VERSION}-linux-x86_64"

rm -rf build/linux dist/linux
"$PY" -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name dosye \
  --paths src \
  --add-data "$ROOT/src/dosye/assets:dosye/assets" \
  --add-data "$ROOT/src/dosye/i18n/locales:dosye/i18n/locales" \
  --collect-submodules dosye \
  --exclude-module numpy --exclude-module tkinter --exclude-module PySide6.QtNetwork \
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtOpenGL \
  --exclude-module cv2 --exclude-module pygame --exclude-module torch \
  --workpath build/linux --distpath dist/linux --specpath build/linux \
  packaging/dosye_launcher.py

mkdir -p dist
cp -f dist/linux/dosye "dist/$NAME"

# ---- tar.gz -------------------------------------------------------------
STAGE="build/linux/stage/dosye-${VERSION}"
rm -rf "build/linux/stage"; mkdir -p "$STAGE"
cp dist/linux/dosye "$STAGE/dosye"
cp packaging/linux/dosye.desktop packaging/linux/install.sh "$STAGE/"
cp src/dosye/assets/icons/dosye_icon.png "$STAGE/dosye.png"
cp LICENSE "$STAGE/"
cat > "$STAGE/README.txt" <<TXT
Dosye ${VERSION} for Linux x86_64

  ./dosye               run it directly
  ./install.sh          install for the current user (~/.local/bin + menu entry)
  ./install.sh --uninstall

Project: https://github.com/cleitinhodev/dosye  ·  https://www.bugzinho.com/
License: GPL-3.0-or-later (see LICENSE)
TXT
tar -C build/linux/stage -czf "dist/$NAME.tar.gz" "dosye-${VERSION}"

# ---- AppImage -----------------------------------------------------------
if [ "${NO_APPIMAGE:-0}" != "1" ]; then
  TOOL="build/appimagetool-x86_64.AppImage"
  if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$TOOL"
  fi
  APPDIR="build/linux/Dosye.AppDir"
  rm -rf "$APPDIR"; mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/applications"
  cp dist/linux/dosye "$APPDIR/usr/bin/dosye"
  cp src/dosye/assets/icons/dosye_icon.png "$APPDIR/dosye.png"
  cp src/dosye/assets/icons/dosye_icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/dosye.png"
  cp packaging/linux/dosye.desktop "$APPDIR/dosye.desktop"
  cp packaging/linux/dosye.desktop "$APPDIR/usr/share/applications/dosye.desktop"
  cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/dosye" "$@"
RUN
  chmod +x "$APPDIR/AppRun"
  ARCH=x86_64 "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "dist/Dosye-${VERSION}-x86_64.AppImage"
fi
ls -la dist/

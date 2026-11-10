#!/bin/sh
# Install Dosye for the current user (no root needed).
#   ./install.sh            install to ~/.local
#   ./install.sh --uninstall
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"

if [ "$1" = "--uninstall" ]; then
    rm -f "$BIN/dosye" "$APPS/dosye.desktop" "$ICONS/dosye.png"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
    echo "Dosye removed."
    exit 0
fi

mkdir -p "$BIN" "$APPS" "$ICONS"
install -m 755 "$HERE/dosye" "$BIN/dosye"
install -m 644 "$HERE/dosye.png" "$ICONS/dosye.png"
sed "s|^Exec=.*|Exec=\"$BIN/dosye\" %F|" "$HERE/dosye.desktop" > "$APPS/dosye.desktop"
chmod 644 "$APPS/dosye.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q "${ICONS%/256x256/apps}" >/dev/null 2>&1 || true
echo "Dosye installed: $BIN/dosye (menu entry: Graphics > Dosye)"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Note: $BIN is not in your PATH." ;; esac

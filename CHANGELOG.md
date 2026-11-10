# Changelog

All notable changes to Dosye are documented here. Dates are in America/Sao_Paulo time.

## [1.0.0] — 2026-11-10

The first release under the name **Dosye** (Haitian Creole for “folder”), rebuilt as a real project from
*Gerador de Pastas* 3.0.

### Added
- New name, new identity: Dosye icon (app, executable, taskbar, desktop file, About/Help) and the
  mascot favicon in every window title bar; Windows AppUserModelID so the taskbar groups correctly.
- Night-sky **neon theme** taken from the icon: navy/indigo background, violet-blue gradients, golden-moon
  accent; glowing focus and selection, glowing primary button, twinkling header stars, smooth tab and shape
  animations, starry-night preview background, toast notifications with “Show folder”.
- Efficient animations: one shared 10 fps clock that stops when animations are off, the window is minimized
  or hidden, or the app is inactive; only small dirty regions are repainted.
- **Settings** dialog (saved per user): language, neon animations on/off, reduce effects, theme intensity,
  default export folder, default PNG size and the sizes inside the `.ico` (now also 20 and 40 px).
- **15 languages** with runtime switching and auto-detection: Kreyòl ayisyen, Français, Kréyòl
  Gwadloup/Matnik, Kreol Morisien, English, Português (Brasil), Español, Deutsch, Italiano, Polski, Türkçe,
  Русский, 日本語, 中文 (简体), 한국어 — every string, shape name, tooltip, dialog and help page.
  CJK fonts are picked automatically. (Machine translations — contributions welcome.)
- **Help** dialog (how to use every feature, keyboard shortcuts) and **About** dialog with links to the
  official site, the project and donations, plus the license.
- **Linux support**: apply/remove folder icons for GNOME Files, Nemo and Caja (GIO `metadata::custom-icon`)
  and KDE Dolphin (`.directory`); `.desktop` file, `install.sh`, AppImage and tar.gz builds.
- New sample emblem: golden moon. Background swatches in the preview header.
- Keyboard shortcuts: Ctrl+E, Ctrl+Shift+E, Ctrl+O, Ctrl+S, Ctrl+R, Ctrl+F, Ctrl+Comma, F1, Ctrl+Q.
- Presets are saved as `.dosye.json`; `.pasta.json` presets from every Gerador de Pastas version still open.
- `--selftest DIR` command-line check (exports all shapes, all languages, presets, folder icons, animations,
  layout at 1366×768 and 125 % scaling), `--lang`, `--version`.
- Clean package layout (`src/dosye/core|ui|i18n|system|assets`), `pyproject.toml`, build scripts for Windows
  (native or Wine) and Linux, and a GitHub Actions workflow that builds both on every tag.
- Licensed under the **GNU GPL v3.0 or later**.

### Changed
- Default design is now the indigo→violet “Modern” folder with the golden-moon emblem.
- Folder icon files written by Dosye are named `.dosye_icon_*` (old `.icone_pasta_*` files are still
  recognized when removing an icon).

## Gerador de Pastas 3.0

- 44 new shapes (51 in total) in six categories — Classic, Modern, Retro, Office, Fun, Special —
  with category tabs and accent-insensitive search; thumbnails use your colours and render progressively.
- Every shape works with colour/gradient, image cover, light, gloss, shadows, outline, frosted glass, papers,
  mirrored tab, PNG coming out and emblem.
- Quick palette moved into the Fill section; “Surprise me” includes the new shapes; v1/v2 presets keep working.

## Gerador de Pastas 2.0

- Image cover: any photo or one of six sample textures, on the whole folder or the front only, with
  fill / fit / tile, zoom, position, tint and blend modes, darker back; drag it in the preview
  (Shift switches between PNG and cover).
- Fixed: the right panel no longer stretches with long file names or huge images.
- The window fits smaller screens such as 1366×768.

## Gerador de Pastas 1.0

- First version: 7 folder shapes (Classic, Modern, Mac style, Wide with tab, Open 3D, Minimal, Chubby).
- Colour and gradient, quick palette, light intensity/direction, gloss, outer glow, drop shadow, inner shading,
  papers, mirrored tab, frosted glass, outline.
- PNG image coming out of the folder or as an emblem (original, embossed, white silhouette), drag & wheel in the preview.
- Export `.ico` (16–256 px) and PNG (256/512/1024 px), apply the icon to a Windows folder and remove it,
  presets (`.pasta.json`) with embedded images.

[1.0.0]: https://github.com/cleitinhodev/dosye/releases/tag/v1.0.0

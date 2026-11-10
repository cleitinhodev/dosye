"""User settings, persisted as JSON in the per-user config folder."""
import json
import os

from .paths import config_dir

ICO_SIZES_ALL = [16, 20, 24, 32, 40, 48, 64, 128, 256]

DEFAULTS = {
    "language": "auto",          # "auto" or a locale code from i18n.LANGUAGES
    "animations": True,          # neon pulses, twinkling stars, transitions
    "reduce_effects": False,     # also disables glows (best for slow PCs / remote desktop)
    "intensity": 70,             # theme glow/gradient intensity 0..100
    "export_dir": "",            # "" = Pictures folder
    "png_size": 512,
    "ico_sizes": [16, 24, 32, 48, 64, 128, 256],
    "preview_bg": "parede",
}


class Settings:
    def __init__(self, path=None):
        self.path = path or os.path.join(config_dir(), "settings.json")
        self.data = dict(DEFAULTS)
        self.first_run = not os.path.exists(self.path)
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return
        for k, v in raw.items():
            if k in DEFAULTS and type(v) is type(DEFAULTS[k]):
                self.data[k] = v
        sizes = [s for s in self.data["ico_sizes"] if s in ICO_SIZES_ALL]
        self.data["ico_sizes"] = sorted(set(sizes)) or list(DEFAULTS["ico_sizes"])
        self.data["intensity"] = max(0, min(100, int(self.data["intensity"])))

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    @property
    def animations_on(self):
        return self.data["animations"] and not self.data["reduce_effects"]

    @property
    def glow_on(self):
        return not self.data["reduce_effects"]

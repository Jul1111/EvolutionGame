"""Settings presets: the values of the Paramètres panel (and the species) saved under saves/presets/, to start an
experiment again with exactly the same settings. One JSON file per preset, named by date."""
import json
import os
import time

import config


def presets_dir():
    return os.path.join(config.SAVE_DIR, "presets")


class PresetBrowser:
    """Saved presets, browsed with ◀ ▶ in the settings panel."""

    def __init__(self):
        self.index = 0
        self.files = []
        self.refresh()

    def refresh(self):
        folder = presets_dir()
        self.files = sorted(f for f in os.listdir(folder) if f.endswith(".json")) if os.path.isdir(folder) else []
        self.index = min(self.index, max(0, len(self.files) - 1))

    def label(self):
        if not self.files:
            return "aucun préréglage"
        name = self.files[self.index][:-5]
        return f"{name}  ({self.index + 1}/{len(self.files)})"

    def move(self, step):
        if self.files:
            self.index = (self.index + step) % len(self.files)

    def load(self):
        """Values of the current preset ({config name: value}), or None."""
        if not self.files:
            return None
        try:
            with open(os.path.join(presets_dir(), self.files[self.index]), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def save(self, values):
        """Writes a new preset and selects it. Returns its file name."""
        os.makedirs(presets_dir(), exist_ok=True)
        name = "preset_" + time.strftime("%Y%m%d_%H%M%S") + ".json"
        with open(os.path.join(presets_dir(), name), "w", encoding="utf-8") as f:
            json.dump(values, f, ensure_ascii=False, indent=1)
        self.refresh()
        self.index = self.files.index(name) if name in self.files else 0
        return name

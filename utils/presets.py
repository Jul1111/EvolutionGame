"""Settings presets: the values of the Paramètres panel (and the species) saved under saves/presets/, to start an
experiment again with exactly the same settings. One JSON file per preset, named by date.

Built-in presets (presets/ at the root of the project, versioned) come first: Facile, Équitable, Dur, Compliqué, chosen
from the settings map (docs/experiences.md). They only set some settings (not the world size nor the species); their
"_nom" is the name shown and keys starting with "_" are not settings."""
import json
import os
import time

import config


BUILTIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets")


def presets_dir(cfg=config):
    return os.path.join(cfg.SAVE_DIR, "presets")


def json_files(folder):
    return sorted(f for f in os.listdir(folder) if f.endswith(".json")) if os.path.isdir(folder) else []


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


class PresetBrowser:
    """Saved presets, browsed with ◀ ▶ in the settings panel."""

    def __init__(self, cfg=config):
        self.cfg = cfg   # Settings in force (see config.Settings): where the presets are kept
        self.index = 0
        self.files = []   # Paths: the built-in presets, then the saved ones
        self.refresh()

    def refresh(self):
        saved = presets_dir(self.cfg)
        self.files = [os.path.join(BUILTIN_DIR, f) for f in json_files(BUILTIN_DIR)] + \
                     [os.path.join(saved, f) for f in json_files(saved)]
        self.index = min(self.index, max(0, len(self.files) - 1))

    def label(self):
        if not self.files:
            return "aucun préréglage"
        path = self.files[self.index]
        name = os.path.basename(path)[:-5]
        if os.path.dirname(path) == BUILTIN_DIR:
            name = (read_json(path) or {}).get("_nom", name)
        return f"{name}  ({self.index + 1}/{len(self.files)})"

    def move(self, step):
        if self.files:
            self.index = (self.index + step) % len(self.files)

    def load(self):
        """Values of the current preset ({config name: value}), or None."""
        if not self.files:
            return None
        values = read_json(self.files[self.index])
        return {k: v for k, v in values.items() if not k.startswith("_")} if isinstance(values, dict) else None

    def save(self, values):
        """Writes a new preset and selects it. Returns its file name."""
        os.makedirs(presets_dir(self.cfg), exist_ok=True)
        name = "preset_" + time.strftime("%Y%m%d_%H%M%S") + ".json"
        with open(os.path.join(presets_dir(self.cfg), name), "w", encoding="utf-8") as f:
            json.dump(values, f, ensure_ascii=False, indent=1)
        self.refresh()
        path = os.path.join(presets_dir(self.cfg), name)
        self.index = self.files.index(path) if path in self.files else 0
        return name

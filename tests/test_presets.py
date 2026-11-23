import json
import os

import config
from app.settings import PARAMS
from brain.profiles import PROFILES
from utils.presets import BUILTIN_DIR, PresetBrowser


def test_builtin_presets_come_first_then_saved_ones(tmp_path):
    cfg = config.Settings(SAVE_DIR=str(tmp_path))
    browser = PresetBrowser(cfg)
    names = []
    for _ in browser.files:
        names.append(browser.label().split("  ")[0])
        browser.move(1)
    assert names == ["Facile", "Équitable", "Dur", "Compliqué", "Niches", "Prédateurs"]
    saved = browser.save({"FOOD_COUNT": 30})
    assert browser.index == 6 and browser.label().startswith(saved[:-5])
    assert browser.load() == {"FOOD_COUNT": 30}


def test_builtin_presets_hold_menu_values_only():
    known = {name: steps for name, steps, _ in PARAMS.values()}
    for f in sorted(os.listdir(BUILTIN_DIR)):
        with open(os.path.join(BUILTIN_DIR, f), encoding="utf-8") as fh:
            values = json.load(fh)
        for key, value in values.items():
            if key.startswith("_"):
                continue
            if key == "ACTIVE_PROFILES":
                assert value and set(value) <= set(PROFILES), (f, value)
                continue
            assert key in known and value in known[key], (f, key, value)
    browser = PresetBrowser(config.Settings(SAVE_DIR="/nonexistent"))
    assert all(not k.startswith("_") for k in browser.load())

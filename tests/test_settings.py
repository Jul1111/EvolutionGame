import json

import config
from utils import settings


def test_settings_keep_only_differences():
    settings.save_settings({"FOOD_COUNT": config.FOOD_COUNT, "POISON_COUNT": config.POISON_COUNT + 1})
    with open(settings._path(config), encoding="utf-8") as f:
        assert json.load(f) == {"POISON_COUNT": config.POISON_COUNT + 1}


def test_settings_load_and_save_on_a_copy(tmp_path):
    """load_settings / save_settings work on the cfg they are given: the config module is not touched."""
    own = config.Settings(SAVE_DIR=str(tmp_path / "own"), POISON_COUNT=config.POISON_COUNT + 3)
    settings.save_settings({"POISON_COUNT": own.POISON_COUNT, "FOOD_COUNT": own.FOOD_COUNT}, own)
    other = config.Settings(SAVE_DIR=own.SAVE_DIR)
    changed = settings.load_settings({"POISON_COUNT", "FOOD_COUNT"}, other)
    assert other.POISON_COUNT == config.POISON_COUNT + 3 and set(changed) == {"POISON_COUNT"}
    assert config.POISON_COUNT == type(config.POISON_COUNT)(config.POISON_COUNT)   # Module value unchanged
    assert not (tmp_path / "saves" / "settings.json").exists()

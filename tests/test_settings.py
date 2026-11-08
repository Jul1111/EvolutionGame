import json

import config
from utils import settings


def test_settings_keep_only_differences():
    settings.save_settings({"FOOD_COUNT": config.FOOD_COUNT, "POISON_COUNT": config.POISON_COUNT + 1})
    with open(settings._path(), encoding="utf-8") as f:
        assert json.load(f) == {"POISON_COUNT": config.POISON_COUNT + 1}

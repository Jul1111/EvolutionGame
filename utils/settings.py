import json
import os

import config


def _path():
    return os.path.join(config.SAVE_DIR, "settings.json")


def load_settings(names):
    """Applies the settings saved from the menu to `config`. Only the constants in `names` are read, and a value
    of the wrong type is ignored. Returns {name: (value in config.py, saved value)} for those that differ."""
    if not config.LOAD_SETTINGS:
        return {}
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    changed = {}
    for name in names:
        if name not in data:
            continue
        default, value = getattr(config, name), data[name]
        if isinstance(default, bool):
            if not isinstance(value, bool):
                continue
        elif isinstance(default, list):
            if not isinstance(value, list):
                continue
            from brain.profiles import PROFILES
            value = [v for v in value if v in PROFILES]   # Unknown names are dropped (a profile was removed)
            if not value:
                continue
        elif isinstance(default, str):
            if not isinstance(value, str):
                continue
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        else:
            value = type(default)(value)
        if value != default:
            changed[name] = (default, value)
            setattr(config, name, value)
    return changed


def save_settings(values):
    """Writes {config name: value} to saves/settings.json (temporary file then replace: never half written)."""
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2)
    os.replace(tmp, _path())

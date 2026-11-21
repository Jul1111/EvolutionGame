import json
import os

import config

# Values of config.py before anything changes them: settings.json only keeps what differs from these,
# so config.py stays the reference (a value not overridden follows config.py, even after it is edited)
DEFAULTS = {name: getattr(config, name) for name in dir(config) if name.isupper()}


# Text settings: the values accepted from settings.json (anything else is ignored)
ALLOWED = {"SIZE_MODE": ("fixe", "neutre", "actif")}


def _path(cfg):
    return os.path.join(cfg.SAVE_DIR, "settings.json")


def load_settings(names, cfg=config):
    """Applies the settings saved from the menu to `cfg` (the live module by default). Only the constants in `names`
    are read, and a value of the wrong type is ignored. Returns {name: (value in config.py, saved value)} for those
    that differ."""
    if not cfg.LOAD_SETTINGS:
        return {}
    try:
        with open(_path(cfg), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    changed = {}
    for name in names:
        if name not in data:
            continue
        default, value = getattr(cfg, name), data[name]
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
            if not isinstance(value, str) or value not in ALLOWED.get(name, (value,)):
                continue
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        else:
            value = type(default)(value)
        if value != default:
            changed[name] = (default, value)
            setattr(cfg, name, value)
    return changed


def overrides(values):
    """Only the values that differ from config.py."""
    return {name: value for name, value in values.items()
            if name not in DEFAULTS or _plain(DEFAULTS[name]) != _plain(value)}


def _plain(value):
    return list(value) if isinstance(value, tuple) else value


def save_settings(values, cfg=config):
    """Writes the values of {config name: value} that differ from config.py to saves/settings.json
    (temporary file then replace: never half written). Nothing differs: an empty {}."""
    os.makedirs(cfg.SAVE_DIR, exist_ok=True)
    tmp = _path(cfg) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(overrides(values), f, indent=2, ensure_ascii=False)
    os.replace(tmp, _path(cfg))

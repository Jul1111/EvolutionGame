import csv
import json
import os
import time

import config
from brain.profiles import paths, config_values

# Measures of the generation, computed by main.py
BASE_HEADER = ["generation", "ticks", "alive", "best_age", "mean_food", "max_food", "mean_speed",
               "food_count", "total_food", "blind_frac", "blind_speed", "blind_turn", "mean_energy",
               "mean_poison", "total_poison", "obstacle_frac"]

# Every constant of config.py is logged too (column = its name in lower case), so a CSV says which settings produced it.
# Machine-specific paths are left out.
CONFIG_EXCLUDED = {"SAVE_DIR", "GENOMES_FILE", "STATS_FILE"}

# Columns of the first version of the settings logging, renamed to the config name
OLD_NAMES = {"parents": "parents_count", "respawn_delay": "food_respawn_delay",
             "max_eats": "food_max_eats", "fixed_positions": "food_fixed_positions"}


def _config_names():
    # A constant whose lower-case name is already a measure column (FOOD_COUNT / food_count) is not duplicated
    return [n for n in sorted(dir(config))
            if n.isupper() and n not in CONFIG_EXCLUDED and n.lower() not in BASE_HEADER
            and isinstance(getattr(config, n), (int, float, bool, str, tuple, list))]


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (tuple, list)):
        return json.dumps(value, ensure_ascii=False)   # e.g. colours, label lists
    return value


def _names(profile):
    """Names of the logged constants: those of config.py, then the ones describing the profile's network."""
    return _config_names() + sorted(config_values(profile))


def _header(profile):
    return BASE_HEADER + [n.lower() for n in _names(profile)]


def _value(profile, name):
    own = config_values(profile)
    return own[name] if name in own else getattr(config, name)


def _migrate_or_set_aside(file, header):
    """Existing CSV with other columns: if every old column still exists, rewrite the file with the new
    columns (empty for the old rows, we do not know their values); else set it aside (timestamped)."""
    with open(file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        old_header = next(reader, None)
        rows = list(reader)
    if old_header == header:
        return
    renamed = [OLD_NAMES.get(name, name) for name in old_header or []]
    if old_header and all(name in header for name in renamed):
        tmp = file + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in rows:
                by_name = dict(zip(renamed, row))
                writer.writerow([by_name.get(name, "") for name in header])
        os.replace(tmp, file)
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    os.replace(file, file.replace(".csv", f"_ancien_{stamp}.csv"))


def log_generation(profile, stats):
    """Ajoute une ligne au CSV du profil. `stats` : dict avec les clés de BASE_HEADER (None = case vide).
    Les réglages de config.py sont ajoutés tels qu'ils sont à cet instant (ceux de la génération qui vient de finir)."""
    file = paths(profile)[1]
    os.makedirs(os.path.dirname(file), exist_ok=True)
    header = _header(profile)
    if os.path.exists(file):
        _migrate_or_set_aside(file, header)
    new_file = not os.path.exists(file)  # À tester AVANT d'ouvrir le fichier
    row = []
    for key in BASE_HEADER:
        value = stats[key]
        row.append(round(value, 3) if isinstance(value, float) else _cell(value))
    row += [_cell(_value(profile, n)) for n in _names(profile)]
    with open(file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(header)
        writer.writerow(row)


def archive_stats(profile):
    """Fresh start: set aside the existing CSV of the profile (timestamped) so generations are not mixed."""
    file = paths(profile)[1]
    if os.path.exists(file):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        os.replace(file, file.replace(".csv", f"_ancien_{stamp}.csv"))

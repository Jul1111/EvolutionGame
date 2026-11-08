import csv
import json
import os
import time

import config

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


def _header():
    return BASE_HEADER + [n.lower() for n in _config_names()]


def _migrate_or_set_aside(header):
    """Existing stats.csv with other columns: if every old column still exists, rewrite the file with the new
    columns (empty for the old rows, we do not know their values); else set it aside (timestamped)."""
    with open(config.STATS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        old_header = next(reader, None)
        rows = list(reader)
    if old_header == header:
        return
    renamed = [OLD_NAMES.get(name, name) for name in old_header or []]
    if old_header and all(name in header for name in renamed):
        tmp = config.STATS_FILE + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in rows:
                by_name = dict(zip(renamed, row))
                writer.writerow([by_name.get(name, "") for name in header])
        os.replace(tmp, config.STATS_FILE)
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    os.replace(config.STATS_FILE, config.STATS_FILE.replace(".csv", f"_ancien_{stamp}.csv"))


def log_generation(stats):
    """Ajoute une ligne à saves/stats.csv. `stats` : dict avec les clés de BASE_HEADER (None = case vide).
    Les réglages de config.py sont ajoutés tels qu'ils sont à cet instant (ceux de la génération qui vient de finir)."""
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    header = _header()
    if os.path.exists(config.STATS_FILE):
        _migrate_or_set_aside(header)
    new_file = not os.path.exists(config.STATS_FILE)  # À tester AVANT d'ouvrir le fichier
    row = []
    for key in BASE_HEADER:
        value = stats[key]
        row.append(round(value, 3) if isinstance(value, float) else _cell(value))
    row += [_cell(getattr(config, n)) for n in _config_names()]
    with open(config.STATS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(header)
        writer.writerow(row)


def archive_stats():
    """Fresh start: set aside an existing stats.csv (timestamped) so generations are not mixed."""
    if os.path.exists(config.STATS_FILE):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        os.replace(config.STATS_FILE, config.STATS_FILE.replace(".csv", f"_ancien_{stamp}.csv"))

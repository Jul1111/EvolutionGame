import csv
import os
import time

import config

HEADER = ["generation", "ticks", "alive", "best_age", "mean_food", "max_food", "mean_speed",
          "food_count", "total_food", "blind_frac", "blind_speed", "blind_turn", "mean_energy",
          # Settings in effect during the generation (they can change from the menu between two generations)
          "mutation_std", "parents", "food_energy", "respawn_delay", "max_eats", "fixed_positions"]


def log_generation(stats):
    """Ajoute une ligne à saves/stats.csv. `stats` : dict avec les clés de HEADER (None = case vide)."""
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    # Old file with different columns: set it aside (timestamped) instead of mixing two formats
    if os.path.exists(config.STATS_FILE):
        with open(config.STATS_FILE, newline="", encoding="utf-8") as f:
            first_row = next(csv.reader(f), None)
        if first_row != HEADER:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            os.replace(config.STATS_FILE, config.STATS_FILE.replace(".csv", f"_ancien_{stamp}.csv"))
    new_file = not os.path.exists(config.STATS_FILE)  # À tester AVANT d'ouvrir le fichier
    with open(config.STATS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(HEADER)
        row = []
        for key in HEADER:
            value = stats[key]
            if value is None:
                value = ""
            elif isinstance(value, float):
                value = round(value, 3)
            row.append(value)
        writer.writerow(row)


def archive_stats():
    """Fresh start: set aside an existing stats.csv (timestamped) so generations are not mixed."""
    if os.path.exists(config.STATS_FILE):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        os.replace(config.STATS_FILE, config.STATS_FILE.replace(".csv", f"_ancien_{stamp}.csv"))

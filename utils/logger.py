import csv
import os

import config

HEADER = ["generation", "ticks", "alive", "best_age", "mean_food", "max_food", "mean_speed",
          "food_count", "total_food", "blind_frac", "blind_speed", "blind_turn"]


def log_generation(stats):
    """Ajoute une ligne à saves/stats.csv. `stats` : dict avec les clés de HEADER (None = case vide)."""
    os.makedirs(config.SAVE_DIR, exist_ok=True)
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

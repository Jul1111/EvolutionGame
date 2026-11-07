import csv
import os

import config

HEADER = ["generation", "ticks", "alive", "best_age", "mean_food", "max_food", "mean_speed"]


def log_generation(generation, ticks, alive, best_age, mean_food, max_food, mean_speed):
    """Ajoute une ligne de statistiques (âges en ticks) à saves/stats.csv."""
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    new_file = not os.path.exists(config.STATS_FILE)  # À tester AVANT d'ouvrir le fichier
    with open(config.STATS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(HEADER)
        writer.writerow([generation, ticks, alive, best_age,
                         round(mean_food, 2), max_food, round(mean_speed, 3)])

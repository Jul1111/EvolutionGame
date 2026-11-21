"""The curves of the timeline: reading timeline.csv, the list of series that can be shown, and their pre-rendering."""
import csv

import pygame

import config
from rendering.ui.draw import VALUE, LABEL, MINT, AMBER, CORAL, BLUE, Ctx, _panel, _text, _clip
from utils.timefmt import format_time

def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None  # Empty cell (e.g. blind_speed when no tick was blind) or missing column


def load_timeline(path):
    """Read timeline.csv (evolution/continuous.py). List of dicts, values are floats or None. Empty if missing."""
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append({k: _to_float(v) for k, v in row.items()})
    except OSError:
        return []
    return rows


def _col(name):
    return lambda row: row.get(name)


# Curves that can be shown: (key, label, colour, value(row), fixed maximum or None = largest value seen, text format).
# One point per line of timeline.csv. Each curve is scaled to its own range.
SERIES = [
    ("population", "Population", (204, 172, 132), _col("population"), None, lambda v: f"{v:.0f}"),
    ("births", "Naissances (par relevé)", MINT, _col("births"), None, lambda v: f"{v:.0f}"),
    ("deaths_hunger", "Morts de faim (par relevé)", CORAL, _col("deaths_hunger"), None, lambda v: f"{v:.0f}"),
    ("deaths_age", "Morts de vieillesse (par relevé)", (150, 164, 178), _col("deaths_age"), None, lambda v: f"{v:.0f}"),
    ("food_rate", "Repas / 1000 ticks de vie", (90, 200, 110), _col("food_rate"), None, lambda v: f"{v:.2f}"),
    ("poison_rate", "Poisons / 1000 ticks de vie", (176, 96, 214), _col("poison_rate"), None, lambda v: f"{v:.2f}"),
    ("mean_speed", "Vitesse moy.", BLUE, _col("mean_speed"), lambda: config.CREATURE_MAX_SPEED, lambda v: f"{v:.2f}"),
    ("mean_energy", "Énergie moy.", AMBER, _col("mean_energy"), None, lambda v: f"{v:.0f}"),
    ("mean_lineage_gen", "Génération de lignée moy.", (160, 190, 255), _col("mean_lineage_gen"), None,
     lambda v: f"{v:.1f}"),
    ("mean_age_at_death", "Âge moyen à la mort", (236, 142, 72), _col("mean_age_at_death"), lambda: config.AGE_MAX or None,
     format_time),
    ("food_sources", "Sources de nourriture", (120, 210, 150), _col("food_sources"), None, lambda v: f"{v:.0f}"),
    ("food_available", "Nourritures disponibles", (178, 224, 120), _col("food_available"), None, lambda v: f"{v:.0f}"),
    ("mean_size", "Taille moy.", (236, 200, 120), _col("mean_size"), lambda: config.SIZE_MAX, lambda v: f"{v:.2f}"),
    ("size_std", "Écart de taille", (200, 170, 110), _col("size_std"), None, lambda v: f"{v:.2f}"),
    ("blind_frac", "Part du temps sans nourriture en vue", CORAL, _col("blind_frac"), lambda: 1.0, lambda v: f"{v:.0%}"),
    ("blind_speed", "Vitesse sans nourriture en vue", (132, 132, 236), _col("blind_speed"),
     lambda: config.CREATURE_MAX_SPEED, lambda v: f"{v:.2f}"),
    ("blind_turn", "Virage sans nourriture en vue", (236, 142, 72), _col("blind_turn"), lambda: 1.0, lambda v: f"{v:.2f}"),
    ("cap_blocked", "Naissances bloquées (plafond)", (230, 122, 182), _col("cap_blocked"), None, lambda v: f"{v:.0f}"),
]
SERIES_BY_KEY = {s[0]: s for s in SERIES}
DEFAULT_SERIES = ("population", "food_rate", "mean_speed", "blind_speed")


def _legend(surf, fonts, entries, area, c, values):
    """Colour dot, label and (when there is room) last value, in one or two columns inside `area`.
    entries: [(label, colour, last text)]. Entries that do not fit are replaced by a '+N' note."""
    small = fonts["small"]
    line_h = small.get_height() + c.x(2)
    per_col = max(1, area.h // line_h)
    cols = 1 if len(entries) <= per_col else 2
    capacity = per_col * cols
    shown = entries[:capacity]
    hidden = len(entries) - len(shown)
    if hidden:
        shown = entries[:capacity - 1]
        hidden = len(entries) - len(shown)
    col_w = area.w // cols
    for i, (label, color, last) in enumerate(shown):
        cx = area.x + (i // per_col) * col_w
        cy = area.y + (i % per_col) * line_h
        pygame.draw.circle(surf, color, (cx + c.x(6), cy + small.get_height() // 2), max(3, c.x(4)))
        value_w = small.size(last)[0]
        with_value = small.size(label)[0] + value_w + c.x(34) <= col_w
        _text(surf, small, label if with_value else _clip(small, label, col_w - c.x(24)), cx + c.x(16), cy, LABEL)
        if with_value:
            _text(surf, small, last, cx + col_w - c.x(8), cy, VALUE, right=True)
    if hidden:
        k = len(shown)
        x = area.x + (k // per_col) * col_w + c.x(16)
        _text(surf, small, _clip(small, f"+ {hidden} autres (voir le bandeau)", area.right - x), x,
              area.y + (k % per_col) * line_h, LABEL)


def build_chart(fonts, stats, width, height, u, wide, keys, species=None):
    """Pre-render the per-generation curves for the series in `keys`. Each curve is scaled to its own range.
    wide=False: plot on top, legend below (side bar). wide=True: plot on the left, legend on the right (strip)."""
    c = Ctx(u)
    surf = _panel(width, height, u)
    pad = c.x(14)
    _text(surf, fonts["base"], "Courbes dans le temps", pad, c.x(7), VALUE)
    _text(surf, fonts["small"], (species + "  ·  " if species else "") + "échelles propres", width - pad, c.x(9), LABEL,
          right=True)
    selected = [SERIES_BY_KEY[k] for k in (s[0] for s in SERIES) if k in keys]
    line_h = fonts["small"].get_height() + c.x(2)

    if wide:
        plot = pygame.Rect(pad, c.x(30), int(width * 0.60), height - c.x(30) - pad)
        legend_area = pygame.Rect(plot.right + c.x(20), plot.top, width - plot.right - c.x(20) - pad, plot.height)
    else:
        legend_h = min(len(selected), 4) * line_h if selected else 0
        plot_h = max(c.x(30), height - c.x(28) - legend_h - c.x(16))
        plot = pygame.Rect(pad, c.x(28), width - 2 * pad, plot_h)
        legend_area = pygame.Rect(pad, plot.bottom + c.x(6), width - 2 * pad, height - plot.bottom - c.x(6) - c.x(6))
    pygame.draw.rect(surf, (255, 255, 255, 14), plot, border_radius=max(3, c.x(6)))
    if not stats or not selected:
        text = "Pas encore de données" if not stats else "Aucune courbe choisie (menu Courbes)"
        msg = fonts["small"].render(text, True, LABEL)
        surf.blit(msg, (plot.centerx - msg.get_width() // 2, plot.centery - msg.get_height() // 2))
        return surf

    n = len(stats)
    margin = c.x(3)
    entries = []
    for key, label, color, value, fixed_max, fmt in selected:
        values = [value(r) for r in stats]
        seen = [v for v in values if v is not None]
        vmax = (fixed_max() if fixed_max else None) or (max(seen) * 1.05 if seen else 1.0)
        vmax = vmax if vmax > 1e-9 else 1.0
        pts = []
        for j, v in enumerate(values):
            if v is None:
                continue
            px = plot.left + (plot.width * j / (n - 1) if n > 1 else plot.width / 2)
            py = plot.bottom - margin - max(0.0, min(v / vmax, 1.0)) * (plot.height - 2 * margin)
            pts.append((px, py))
        if len(pts) > 1:
            pygame.draw.aalines(surf, color, False, pts)
        elif pts:
            pygame.draw.circle(surf, color, (int(pts[0][0]), int(pts[0][1])), max(2, c.x(3)))
        last = next((v for v in reversed(values) if v is not None), None)
        entries.append((label, color, fmt(last) if last is not None else "n/a"))
    _legend(surf, fonts, entries, legend_area, c, True)
    return surf

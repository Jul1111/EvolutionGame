import csv

import pygame
import config
from rendering.scene import energy_color

PANEL_W, PANEL_H = 250, 186
CHART_W, CHART_H = 320, 172
MARGIN = 12


def create_font():
    """Fonts used by the HUD."""
    return {
        "title": pygame.font.SysFont("arial", 22, bold=True),
        "base": pygame.font.SysFont("arial", 15),
        "small": pygame.font.SysFont("arial", 13),
    }


def format_time(ticks):
    """Convert a number of ticks to a mm:ss string (simulated time)."""
    seconds = ticks / config.TICKS_PER_SECOND
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"


def load_stats():
    """Read saves/stats.csv. Returns a list of dicts of floats, empty if the file is missing."""
    rows = []
    try:
        with open(config.STATS_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append({k: float(v) for k, v in row.items()})
    except (OSError, ValueError):
        return []
    return rows


def _panel(width, height):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(surf, config.HUD_PANEL_COLOR, surf.get_rect(), border_radius=12)
    pygame.draw.rect(surf, (255, 255, 255, 28), surf.get_rect(), width=1, border_radius=12)
    return surf


def _bar(surf, x, y, w, h, fraction, color):
    fraction = max(0.0, min(1.0, fraction))
    pygame.draw.rect(surf, (255, 255, 255, 25), (x, y, w, h), border_radius=h // 2)
    if fraction > 0:
        pygame.draw.rect(surf, color, (x, y, max(h, int(w * fraction)), h), border_radius=h // 2)


def _row(surf, fonts, y, label, value):
    lab = fonts["base"].render(label, True, config.HUD_LABEL_COLOR)
    val = fonts["base"].render(value, True, config.HUD_VALUE_COLOR)
    surf.blit(lab, (14, y))
    surf.blit(val, (PANEL_W - 14 - val.get_width(), y))


def build_chart(fonts, stats):
    """Pre-render the per-generation curves. Each curve uses its own scale (0 to its max)."""
    surf = _panel(CHART_W, CHART_H)
    title = fonts["base"].render("Courbes par génération", True, config.HUD_VALUE_COLOR)
    surf.blit(title, (14, 8))
    note = fonts["small"].render("échelles propres", True, config.HUD_LABEL_COLOR)
    surf.blit(note, (CHART_W - 14 - note.get_width(), 10))

    plot = pygame.Rect(14, 32, CHART_W - 28, 78)
    pygame.draw.rect(surf, (255, 255, 255, 14), plot, border_radius=6)
    if not stats:
        msg = fonts["small"].render("Pas encore de données", True, config.HUD_LABEL_COLOR)
        surf.blit(msg, (plot.centerx - msg.get_width() // 2, plot.centery - msg.get_height() // 2))
        return surf

    food_max = max(max(r["mean_food"] for r in stats), 1.0)
    series = [
        ("Meilleur âge", (240, 196, 92), lambda r: r["best_age"] / config.GEN_MAX_TICKS,
         format_time(stats[-1]["best_age"])),
        ("Nourriture moy.", config.FOOD_COLOR, lambda r: r["mean_food"] / food_max,
         f"{stats[-1]['mean_food']:.0f}"),
        ("Vitesse moy.", (110, 180, 235), lambda r: r["mean_speed"] / config.CREATURE_MAX_SPEED,
         f"{stats[-1]['mean_speed']:.2f}"),
    ]
    n = len(stats)
    for i, (label, color, norm, last) in enumerate(series):
        pts = []
        for j, row in enumerate(stats):
            px = plot.left + (plot.width * j / (n - 1) if n > 1 else plot.width / 2)
            py = plot.bottom - 4 - norm(row) * (plot.height - 8)
            pts.append((px, py))
        if n > 1:
            pygame.draw.aalines(surf, color, False, pts)
        else:
            pygame.draw.circle(surf, color, (int(pts[0][0]), int(pts[0][1])), 3)
        ly = 118 + i * 16
        pygame.draw.circle(surf, color, (20, ly + 8), 4)
        surf.blit(fonts["small"].render(label, True, config.HUD_LABEL_COLOR), (30, ly))
        val = fonts["small"].render(last, True, config.HUD_VALUE_COLOR)
        surf.blit(val, (CHART_W - 14 - val.get_width(), ly))
    return surf


class Hud:
    """Info panel (top left), curves (bottom right), key hints (bottom left)."""

    def __init__(self):
        self.fonts = create_font()
        self.show_chart = True
        self.panel_bg = _panel(PANEL_W, PANEL_H)
        self.hint = self.fonts["small"].render(
            "Haut/Bas : vitesse   D : debug   G : courbes   Échap : quitter",
            True, (110, 122, 128))
        self.reload_stats()

    def reload_stats(self):
        """Call after a generation has been logged."""
        self.stats = load_stats()
        self.chart = build_chart(self.fonts, self.stats)

    def draw(self, screen, world, fps, speed, generation, debug_mode):
        creatures = world.creatures
        total = len(creatures)
        alive = sum(1 for c in creatures if c.alive)
        best_age = max((c.age for c in creatures), default=0)
        zero_food = sum(1 for c in creatures if c.food_eaten == 0)
        over = world.is_over()

        p = self.panel_bg.copy()
        p.blit(self.fonts["title"].render(f"Génération {generation}", True, config.HUD_VALUE_COLOR), (14, 10))
        status_color = (235, 110, 95) if over else (120, 224, 176)
        status = self.fonts["small"].render("Terminé" if over else "En cours", True, status_color)
        p.blit(status, (PANEL_W - 14 - status.get_width(), 16))
        pygame.draw.circle(p, status_color, (PANEL_W - 14 - status.get_width() - 10, 24), 4)

        _row(p, self.fonts, 46, "Vivantes", f"{alive}/{total}")
        _bar(p, 14, 68, PANEL_W - 28, 6, alive / total if total else 0, energy_color(0.85))
        _row(p, self.fonts, 82, "Temps", f"{format_time(world.tick)} / {format_time(config.GEN_MAX_TICKS)}")
        _bar(p, 14, 104, PANEL_W - 28, 6, world.tick / config.GEN_MAX_TICKS, energy_color(0.5))
        _row(p, self.fonts, 118, "Meilleur âge", format_time(best_age))
        _row(p, self.fonts, 138, "Sans nourriture", str(zero_food))

        debug_label = ("off", "meilleure", "toutes")[debug_mode]
        p.blit(self.fonts["small"].render(f"x{speed}  ·  {fps:.0f} FPS", True, config.HUD_LABEL_COLOR), (14, 162))
        dbg = self.fonts["small"].render(f"debug : {debug_label}", True, config.HUD_LABEL_COLOR)
        p.blit(dbg, (PANEL_W - 14 - dbg.get_width(), 162))
        screen.blit(p, (MARGIN, MARGIN))

        if self.show_chart:
            screen.blit(self.chart, (screen.get_width() - CHART_W - MARGIN,
                                     screen.get_height() - CHART_H - MARGIN))
        screen.blit(self.hint, (MARGIN, screen.get_height() - self.hint.get_height() - MARGIN))

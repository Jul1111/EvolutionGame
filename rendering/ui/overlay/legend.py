"""Legend panel: what the colours and shapes of the world mean."""
import math

import pygame

from core.food import kind_position
from rendering import theme
from rendering.backend.glass import frost
from rendering.ui.draw import VALUE
from rendering.ui.overlay.widgets import PANEL
from rendering.world.obstacles import PALETTES
from rendering.world.scene import body_color


def legend_entries(label, kinds=1):
    """Rows of the legend: (icon kind, colour, text), for the colour mode `label`. kinds: FOOD_TYPES."""
    entries = [("dot", theme.FOOD_COLOR, "Nourriture : redonne de l'énergie")] if kinds < 2 else [
        ("dot", theme.FOOD_KIND_COLORS[k],
         f"Nourriture {theme.FOOD_KIND_NAMES[k]} : nourrit les régimes proches de {kind_position(k, kinds):.2g}")
        for k in range(kinds)]
    entries += [("diamond", theme.POISON_COLOR, "Poison : retire de l'énergie"),
               ("anemone", None, "Anémone : obstacle infranchissable")]
    low, high = {"énergie": ("vide", "pleine"), "vitesse": ("à l'arrêt", "vitesse max"),
                 "nourriture": ("rien mangé", "le plus mangé"),
                 "régime": ("mange le vert", "mange le " + ("jaune", "bleu", "rose")[max(0, kinds - 2)]),
                 }.get(label, ("bas", "haut"))
    entries += [("gradient", None, f"Couleur d'une créature = {label}  ({low} → {high})")
                if label not in ("lignée", "espèce") else
                ("ring", (230, 236, 244), "Couleur d'une créature = sa " + label),
                ("cone", theme.DEBUG_VISION_COLOR, "Cône de vision (touche D)"),
                ("ring", (255, 255, 255), "Créature sélectionnée")]
    return entries


class Legend:
    def __init__(self, ctx, scene, minimap):
        self.ctx, self.scene, self.minimap = ctx, scene, minimap
        self.open = False
        self.rect = None      # Where it was drawn last (None when hidden): for clicks
        self._cache = {}

    def relayout(self):
        self._cache.clear()

    def contains(self, x, y):
        return self.open and self.rect is not None and self.rect.collidepoint(x, y)

    def draw(self, window):
        ctx = self.ctx
        u, f, w = ctx.u, ctx.fonts, ctx.area
        label = self.scene.color_label()
        kinds = self.scene.cfg.FOOD_TYPES
        key = ("legend", label, kinds)
        if key not in self._cache:
            row_h, pad, icon_w = round(24 * u), round(12 * u), round(40 * u)
            entries = legend_entries(label, kinds)
            text_w = max(f["small"].size(t)[0] for _, _, t in entries)
            size = (pad * 2 + icon_w + text_w, pad * 2 + row_h * len(entries) - round(4 * u))
            surf = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (*PANEL, 50), surf.get_rect(), border_radius=round(10 * u))   # Over frosted glass
            for i, (kind, color, text) in enumerate(entries):
                cy = pad + i * row_h + row_h // 2 - round(2 * u)
                cx = pad + icon_w // 2
                if kind == "dot":
                    pygame.draw.circle(surf, color, (cx, cy), round(5 * u))
                elif kind == "diamond":
                    r = round(6 * u)
                    pygame.draw.polygon(surf, color, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])
                elif kind == "anemone":
                    mat, tent, tip = PALETTES[0]
                    rad = round(9 * u)
                    pygame.draw.circle(surf, mat, (cx, cy), rad)
                    pygame.draw.circle(surf, tent, (cx, cy), rad, 1)
                    for a in range(8):
                        ang = a * math.pi / 4
                        pygame.draw.line(surf, tip, (cx + math.cos(ang) * rad * 0.25, cy + math.sin(ang) * rad * 0.25),
                                         (cx + math.cos(ang) * rad * 0.8, cy + math.sin(ang) * rad * 0.8),
                                         max(1, round(1.5 * u)))
                elif kind == "gradient":
                    gw = icon_w - round(4 * u)
                    for k in range(gw):
                        pygame.draw.line(surf, body_color(k / max(gw - 1, 1)), (cx - gw // 2 + k, cy - round(4 * u)),
                                         (cx - gw // 2 + k, cy + round(4 * u)))
                elif kind == "cone":
                    r = round(11 * u)
                    a = math.radians(40)
                    o = (cx - r // 2, cy)
                    pts = [(o[0] + r * math.cos(-a + 2 * a * j / 6), o[1] + r * math.sin(-a + 2 * a * j / 6))
                           for j in range(7)]
                    pygame.draw.lines(surf, color, False, [pts[0], o, pts[-1]], 1)
                    pygame.draw.lines(surf, color, False, pts, 1)
                elif kind == "ring":
                    pygame.draw.circle(surf, color, (cx, cy), round(7 * u), max(1, round(1.5 * u)))
                    pygame.draw.circle(surf, (240, 200, 80), (cx, cy), round(3.5 * u))
                img = f["small"].render(text, True, VALUE)
                surf.blit(img, (pad + icon_w, cy - img.get_height() // 2))
            self._cache[key] = surf
        surf = self._cache[key]
        bottom = self.minimap.rect.top if (self.minimap.enabled and self.minimap.rect) else w.bottom
        rect = surf.get_rect(bottomleft=(w.x + round(12 * u), bottom - round(10 * u)))
        frost(window, rect, round(10 * u))
        window.blit(surf, rect.topleft)
        self.rect = rect

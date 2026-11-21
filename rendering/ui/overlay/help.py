"""Help panel: keys and mouse."""
import pygame

from rendering.backend.glass import frost
from rendering.ui.draw import VALUE, LABEL, MINT, AMBER
from rendering.ui.overlay.texts import (HELP_KEYS,
                                        HELP_MOUSE)
from rendering.ui.overlay.widgets import PANEL


class HelpMixin:
    def _draw_help(self, window):
        u, f, w = self.u, self.fonts, self.area
        if "help" not in self._cache:
            pad, row_h, col_gap = round(22 * u), round(23 * u), round(28 * u)
            half = (len(HELP_KEYS) + 1) // 2
            cols = (HELP_KEYS[:half], HELP_KEYS[half:])
            key_w = max(f["base"].size(k)[0] for k, _ in HELP_KEYS) + round(14 * u)
            col_w = key_w + max(f["small"].size(d)[0] for _, d in HELP_KEYS)
            mouse_w = max(f["small"].size(t)[0] for t in HELP_MOUSE)
            width = max(pad * 2 + 2 * col_w + col_gap, pad * 2 + mouse_w)
            height = pad * 2 + f["title"].get_height() + round(12 * u) + row_h * half \
                + round(16 * u) + f["base"].get_height() + round(6 * u) + round(row_h * 0.85) * len(HELP_MOUSE)
            surf = pygame.Surface((width, round(height)), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*PANEL, 60), surf.get_rect(), border_radius=round(12 * u))
            y = pad
            surf.blit(f["title"].render("Aide et raccourcis", True, VALUE), (pad, y))
            y += f["title"].get_height() + round(12 * u)
            for ci, col in enumerate(cols):
                x0 = pad + ci * (col_w + col_gap)
                for i, (k, d) in enumerate(col):
                    surf.blit(f["base"].render(k, True, MINT), (x0, y + i * row_h))
                    surf.blit(f["small"].render(d, True, VALUE), (x0 + key_w, y + i * row_h + round(2 * u)))
            y += row_h * half + round(16 * u)
            surf.blit(f["base"].render("Souris", True, AMBER), (pad, y))
            y += f["base"].get_height() + round(6 * u)
            for t in HELP_MOUSE:
                surf.blit(f["small"].render(t, True, LABEL), (pad, y))
                y += round(row_h * 0.85)
            self._cache["help"] = surf
        surf = self._cache["help"]
        window.blit(self.veil, (0, 0))
        rect = surf.get_rect(center=w.center)
        frost(window, rect, round(12 * u), alpha=185)
        window.blit(surf, rect.topleft)
        self._rects["help"] = rect

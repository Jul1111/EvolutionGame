"""Hover tips: side bar labels, creatures, network neurons, tool bar buttons."""
import time

import pygame

import config
from brain.profiles import PROFILES, input_labels, output_labels
from rendering.backend.glass import frost
from rendering.ui.draw import VALUE, LABEL
from rendering.ui.overlay.texts import GEN_TIPS, CREATURE_TIPS, NET_TIPS
from rendering.ui.overlay.widgets import DIM, wrap
from rendering.world.scene import pick_creature


class TipsMixin:

    def _hud_tip(self, x, y, selected):
        hud = self.hud
        if hud.layout is None:
            return None
        sb = hud.layout.sidebar
        if not sb.collidepoint(x, y):
            return None
        lx, ly = x - sb.x, y - sb.y
        u, ky = hud.u, hud.ky
        fmt = dict(size_min=config.SIZE_MIN, size_max=config.SIZE_MAX, pop_max=config.POP_MAX, energy_max=config.ENERGY_MAX, speed_max=config.CREATURE_MAX_SPEED)
        for name, rows in (("gen", GEN_TIPS), ("creature", CREATURE_TIPS)):
            slot = hud.slots.get(name)
            if slot and slot.collidepoint(lx, ly):
                if name == "creature" and selected is None:
                    return None
                for y_log, text in rows:
                    top = slot.y + round(y_log * u * ky)
                    if top - round(2 * u) <= ly < top + round(18 * u * ky):
                        return text.format(**fmt)
                return None
        slot = hud.slots.get("net")
        if slot and slot.collidepoint(lx, ly) and selected is not None and selected.alive:
            labels = input_labels(selected.profile) + output_labels(selected.profile)
            n_in = len(input_labels(selected.profile))
            base = slot.y + (round(36 * u) if not hud.show_graph else round(32 * u) + round(hud.graph_h * u) + round(12 * u))
            for i, label in enumerate(labels):
                top = base + round((i * 15 + (4 if i >= n_in else 0)) * u)
                if top <= ly < top + round(15 * u):
                    tip = NET_TIPS.get(label)
                    return tip.format(hunger=config.HUNGER_SCALE // config.TICKS_PER_SECOND) if tip else None
        return None

    def draw_tips(self, window, world, selected, menu_open):
        """Hover tips, drawn last. Buttons and labels explain themselves after a short rest; a creature gets a summary."""
        if (self.mouse is None or menu_open or self.params_open or self.help_open or self.layout is None
                or self.start is not None):
            return
        x, y = self.mouse
        dwell = time.monotonic() - self.mouse_since
        lines = None
        for rect, action, icon, title, shortcut in self.buttons:
            if rect.collidepoint(x, y) and dwell > 0.3:
                lines = [(title, "base", VALUE)] + ([(f"Raccourci : {shortcut}", "small", DIM)] if shortcut else [])
        if lines is None and self.speed_rect.collidepoint(x, y) and dwell > 0.3:
            lines = [(f"Vitesse demandée : {self.state.get('speed', 1)} ticks par image, réelle : "
                      f"{self.state.get('real_speed', 0):.0f} (en orange quand la machine ne suit pas)", "base", VALUE),
                     ("Flèches haut / bas", "small", DIM)]
        if lines is None and dwell > 0.45:
            text = self._hud_tip(x, y, selected)
            if text:
                lines = [(t, "small", VALUE) for t in wrap(self.fonts["small"], text, round(300 * self.u))]
        over_ui = self.blocks(x, y)
        if lines is None and self.layout.world.collidepoint(x, y) and not over_ui and dwell > 0.08:
            wx, wy = self.scene.screen_to_world(x - self.layout.world.x, y - self.layout.world.y)
            c = pick_creature(world, wx, wy, self.scene.pick_radius())
            if c is not None:
                t = int(c.age / config.TICKS_PER_SECOND)
                lines = [(f"{PROFILES[c.profile]['title']}  ·  taille {c.size:.2f}  ·  gén. {c.lineage_gen}  ·  {c.children} petits" + ("" if c.alive else "  ·  morte"), "base", VALUE),
                         (f"Énergie {max(c.energy, 0):.0f}   Vitesse {c.speed:.1f}", "small", LABEL),
                         (f"Âge {t // 60:02d}:{t % 60:02d}   Nourriture {c.food_eaten}   Poison {c.poison_hits}", "small", LABEL),
                         ("Clic : fiche complète", "small", DIM)]
        if lines is not None:
            self._draw_box(window, lines, x, y)

    def _draw_box(self, window, lines, mx, my):
        u = self.u
        imgs = [self.fonts[k].render(t, True, c) for t, k, c in lines]
        pad = round(8 * u)
        w = max(i.get_width() for i in imgs) + 2 * pad
        h = sum(i.get_height() for i in imgs) + 2 * pad + round(2 * u) * (len(imgs) - 1)
        ww, wh = window.get_size()
        bx = min(mx + round(16 * u), ww - w - 4)
        by = my + round(20 * u)
        if by + h > wh - 4:
            by = my - h - round(10 * u)
        box = pygame.Rect(max(4, bx), max(4, by), w, h)
        frost(window, box, round(6 * u), alpha=205)
        y = box.y + pad
        for img in imgs:
            window.blit(img, (box.x + pad, y))
            y += img.get_height() + round(2 * u)

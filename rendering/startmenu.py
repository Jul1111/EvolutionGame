"""Start menu, shown at launch over the blurred world: Continuer (the population kept when the game was closed),
Charger (a population saved by hand), Nouvelle simulation (settings screen), Quitter.
It only reads the save files and returns action names; main.py runs them."""
import os
import time

import numpy as np
import pygame

from rendering.glass import frost
from rendering.hud import VALUE, LABEL, _clip
from utils.timefmt import format_time

DIM = (110, 122, 128)
MAX_LISTED = 8


def population_info(path):
    """{"creatures", "tick", "saved_at", "species"} read from a population file, or None if unreadable."""
    try:
        with np.load(path) as data:
            keys = [k for k in data.files if k.startswith("genomes__")]
            creatures = sum(int(data[k].shape[0]) for k in keys)
            tick = int(data["tick"]) if "tick" in data.files else 0
            saved_at = str(data["saved_at"]) if "saved_at" in data.files else \
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
            return {"creatures": creatures, "tick": tick, "saved_at": saved_at,
                    "species": [k.split("__", 1)[1] for k in keys]}
    except (OSError, ValueError, KeyError):
        return None


class StartMenu:
    def __init__(self, autosave, snapshots_dir):
        self.view = "main"          # "main" or "load"
        self.autosave = population_info(autosave) if autosave and os.path.exists(autosave) else None
        self.snapshots = []
        if snapshots_dir and os.path.isdir(snapshots_dir):
            files = sorted((f for f in os.listdir(snapshots_dir) if f.endswith(".npz")), reverse=True)
            for f in files[:MAX_LISTED]:
                info = population_info(os.path.join(snapshots_dir, f))
                if info:
                    self.snapshots.append((os.path.join(snapshots_dir, f), info))
        self.count = len([f for f in os.listdir(snapshots_dir) if f.endswith(".npz")]) \
            if snapshots_dir and os.path.isdir(snapshots_dir) else 0
        self._hits = []

    def default_action(self):
        """Enter: continue the kept population if there is one, else a new simulation."""
        if self.view == "load":
            return "start_back"
        return "start_continue" if self.autosave else "start_new"

    def click(self, x, y):
        for rect, action in self._hits:
            if rect.collidepoint(x, y):
                return action
        return None

    # ---------- drawing ----------

    def draw(self, window, layout, fonts, u, mouse):
        self._hits = []
        veil = pygame.Surface(window.get_size(), pygame.SRCALPHA)
        veil.fill((6, 8, 12, 120))
        window.blit(veil, (0, 0))
        if self.view == "load":
            self._draw_load(window, fonts, u, mouse)
        else:
            self._draw_main(window, fonts, u, mouse)

    def _card(self, window, w, h, u):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (window.get_width() // 2, window.get_height() // 2)
        frost(window, rect, round(16 * u), alpha=175)
        return rect

    def _choice(self, window, rect, title, subtitle, action, enabled, accent, fonts, u, mouse):
        hovered = enabled and mouse is not None and rect.collidepoint(mouse)
        bg = (52, 64, 76) if hovered else ((40, 84, 74) if accent and enabled else (30, 37, 45))
        pygame.draw.rect(window, bg, rect, border_radius=round(10 * u))
        pygame.draw.rect(window, (70, 82, 94), rect, width=1, border_radius=round(10 * u))
        pad = round(16 * u)
        t = fonts["title"].render(title, True, VALUE if enabled else DIM)
        window.blit(t, (rect.x + pad, rect.y + round(9 * u)))
        if subtitle:
            s = fonts["small"].render(_clip(fonts["small"], subtitle, rect.w - 2 * pad), True, LABEL if enabled else DIM)
            window.blit(s, (rect.x + pad, rect.y + round(12 * u) + t.get_height()))
        if enabled:
            self._hits.append((rect, action))

    def _draw_main(self, window, fonts, u, mouse):
        w, pad, bh, gap = round(460 * u), round(26 * u), round(62 * u), round(10 * u)
        h = pad * 2 + round(76 * u) + 3 * (bh + gap) + round(40 * u) + round(30 * u)
        card = self._card(window, w, h, u)
        title = fonts["title"].render("Evolution Simulator", True, VALUE)
        window.blit(pygame.transform.smoothscale(title, (round(title.get_width() * 1.35), round(title.get_height() * 1.35))),
                    (card.x + pad, card.y + pad))
        window.blit(fonts["small"].render("Sélection naturelle et évolution continue", True, LABEL),
                    (card.x + pad, card.y + pad + round(42 * u)))
        y = card.y + pad + round(76 * u)
        a = self.autosave
        if a:
            sub = (f"{a['creatures']} créatures  ·  temps {format_time(a['tick'])}  ·  gardée le {a['saved_at']}")
        else:
            sub = "Aucune partie gardée à la dernière fermeture"
        self._choice(window, pygame.Rect(card.x + pad, y, w - 2 * pad, bh), "Continuer", sub, "start_continue",
                     a is not None, a is not None, fonts, u, mouse)
        y += bh + gap
        sub = (f"{self.count} population{'s' if self.count > 1 else ''} sauvegardée{'s' if self.count > 1 else ''}"
               if self.count else "Aucune population sauvegardée (touche S pendant une partie)")
        self._choice(window, pygame.Rect(card.x + pad, y, w - 2 * pad, bh), "Charger une population", sub,
                     "start_load_list", bool(self.snapshots), False, fonts, u, mouse)
        y += bh + gap
        self._choice(window, pygame.Rect(card.x + pad, y, w - 2 * pad, bh), "Nouvelle simulation",
                     "Choisir les réglages, puis une population tirée au hasard", "start_new", True, a is None, fonts, u, mouse)
        y += bh + gap + round(6 * u)
        qw = fonts["small"].size("Quitter")[0] + round(28 * u)
        q = pygame.Rect(card.right - pad - qw, y, qw, round(28 * u))
        hov = mouse is not None and q.collidepoint(mouse)
        pygame.draw.rect(window, (52, 64, 76) if hov else (30, 37, 45), q, border_radius=round(7 * u))
        img = fonts["small"].render("Quitter", True, VALUE)
        window.blit(img, img.get_rect(center=q.center))
        self._hits.append((q, "quit"))
        hint = "Entrée : " + ("continuer" if a else "nouvelle simulation") + "   ·   Échap : quitter"
        window.blit(fonts["small"].render(hint, True, DIM), (card.x + pad, q.centery - fonts["small"].get_height() // 2))

    def _draw_load(self, window, fonts, u, mouse):
        w, pad, rh, gap = round(560 * u), round(26 * u), round(50 * u), round(6 * u)
        n = len(self.snapshots)
        h = pad * 2 + round(64 * u) + max(1, n) * (rh + gap) + round(44 * u)
        card = self._card(window, w, h, u)
        window.blit(fonts["title"].render("Charger une population", True, VALUE), (card.x + pad, card.y + pad))
        note = (f"Les {MAX_LISTED} plus récentes sur {self.count}" if self.count > MAX_LISTED else
                "Sauvegardées pendant les parties (touche S). Les créatures repartent à neuf, seuls les réseaux sont repris.")
        window.blit(fonts["small"].render(_clip(fonts["small"], note, w - 2 * pad), True, LABEL),
                    (card.x + pad, card.y + pad + round(32 * u)))
        y = card.y + pad + round(64 * u)
        for path, info in self.snapshots:
            name = os.path.basename(path)[:-4]
            sub = f"{info['creatures']} créatures  ·  temps {format_time(info['tick'])}  ·  {info['saved_at']}"
            r = pygame.Rect(card.x + pad, y, w - 2 * pad, rh)
            hov = mouse is not None and r.collidepoint(mouse)
            pygame.draw.rect(window, (52, 64, 76) if hov else (30, 37, 45), r, border_radius=round(8 * u))
            window.blit(fonts["base"].render(_clip(fonts["base"], name, r.w - round(24 * u)), True, VALUE),
                        (r.x + round(12 * u), r.y + round(6 * u)))
            window.blit(fonts["small"].render(sub, True, LABEL), (r.x + round(12 * u), r.y + round(27 * u)))
            self._hits.append((r, "start_load:" + path))
            y += rh + gap
        bw = fonts["small"].size("Retour")[0] + round(28 * u)
        back = pygame.Rect(card.right - pad - bw, card.bottom - pad - round(28 * u), bw, round(28 * u))
        hov = mouse is not None and back.collidepoint(mouse)
        pygame.draw.rect(window, (52, 64, 76) if hov else (30, 37, 45), back, border_radius=round(7 * u))
        img = fonts["small"].render("Retour", True, VALUE)
        window.blit(img, img.get_rect(center=back.center))
        self._hits.append((back, "start_back"))
        window.blit(fonts["small"].render("Échap : retour", True, DIM),
                    (card.x + pad, back.centery - fonts["small"].get_height() // 2))

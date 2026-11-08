"""Interface layer drawn on top of the world: tool bar, pause banner, legend, help, hover tips, settings panel and the
large network view. Everything is drawn at the real resolution (sizes multiplied by the scale u), like the rest of the UI.
This module never touches the simulation: it only reads the world and returns action names, main.py runs them."""
import math
import time

import pygame

import config
from brain.profiles import PROFILES, input_labels, output_labels
from rendering.hud import (VALUE, LABEL, MINT, AMBER, CORAL, create_fonts, network_rows,
                           _node, _edge, _clip)
from rendering.obstacles import PALETTES
from rendering.scene import energy_color, body_color, pick_creature
from rendering.glass import frost
from rendering.charts import ChartView
from rendering.minimap import MiniMap

PANEL = (25, 31, 37)
BORDER = (62, 72, 82)
HOVER = (48, 58, 68)
DIM = (110, 122, 128)
ACTIVE_BG = (40, 84, 74)

# Tool bar: (action, icon, title, shortcut). None = separator, "speed" = speed read-out.
TOOLBAR = [
    ("pause", "pause", "Pause / Reprendre", "Espace"),
    ("step", "step", "Avancer d'un tick (en pause)", "→"),
    ("speed_down", "minus", "Ralentir la simulation", "↓"),
    "speed",
    ("speed_up", "plus", "Accélérer la simulation", "↑"),
    None,
    ("debug", "cone", "Debug : cône de vision et cibles (off, sélection, toutes)", "D"),
    ("graph", "net", "Réseau de neurones : masqué, petit, grand", "N"),
    ("chart", "curves", "Courbes : masquées, panneau, grand", "G"),
    None,
    ("best", "kids", "Sélectionner la créature qui a eu le plus de petits (à sa mort : la nouvelle meilleure)", "B"),
    ("follow", "branch", "Suivre la lignée : à la mort de la sélection, son plus jeune descendant (sinon la nouvelle meilleure)", "T"),
    ("cam_follow", "target", "Caméra sur la sélection", "V"),
    None,
    ("params_panel", "sliders", "Paramètres de simulation", "P"),
    ("help", "help", "Aide et raccourcis", "H"),
]

# Label, explanation of every setting of the panel (keys = main.PARAMS)
PARAM_INFO = {
    "mutation": ("Mutation", "Amplitude du bruit ajouté à chaque poids d'un enfant."),
    "repro": ("Seuil de reproduction", "Énergie qu'il faut atteindre pour faire un petit (le parent perd 60, le petit naît avec 50)."),
    "age_max": ("Âge maximal", "Mort de vieillesse. Sans elle, des immortels bloquent le renouvellement."),
    "fov": ("Champ de vision", "Ouverture du cône de vision. Tout autour = 360°."),
    "food": ("Nombre de nourritures", "Sources de nourriture dans le monde."),
    "food_energy": ("Énergie d'une nourriture", "Énergie gagnée à chaque repas."),
    "respawn": ("Délai de réapparition", "Temps avant qu'une nourriture mangée soit de nouveau disponible."),
    "poison_count": ("Nombre de poisons", "Sources de poison dans le monde. 0 = aucun."),
    "poison_energy": ("Dégâts d'un poison", "Énergie perdue au contact d'un poison."),
    "founders": ("Créatures au départ", "Fondateurs aux réseaux tirés au hasard, quelle que soit la taille du monde. Au prochain départ."),
    "size_mode": ("Gène de taille", "Fixe : tous à 1. Neutre : la taille mute sans rien changer (témoin de dérive). Actif : plus grand = touche de plus loin, réserve plus grande, coûte plus. Au prochain départ de zéro."),
    "world_scale": ("Taille du monde", "Côté du monde en écrans. 2×2 = 4 fois plus de surface, de nourriture et de créatures, et environ 4 fois plus lent. Au prochain départ de zéro."),
    "obstacle_count": ("Nombre d'obstacles", "Obstacles (formes et places tirées au hasard). S'applique au prochain départ de zéro. 0 = aucun."),
}

# Explanations shown when the mouse rests on a label of the side bar: (logical y of the row, text)
GEN_TIPS = [
    (38, "Vivantes sur le plafond de calcul ({pop_max} par écran). Au plafond, les naissances sont bloquées : la population n'est plus réglée par la nourriture."),
    (68, "Temps simulé depuis le départ de cette population."),
    (86, "Naissances et morts depuis le départ. Une créature naît quand son parent atteint le seuil d'énergie."),
    (104, "Génération de lignée : nombre d'ancêtres depuis les fondateurs tirés au hasard (0)."),
]
CREATURE_TIPS = [
    (36, "Énergie restante. À 0, la créature meurt. Plafond : {energy_max:g} × taille (si la taille agit)."),
    (66, "Vitesse actuelle, de 0 à {speed_max:g}. Elle change progressivement vers la vitesse demandée par le réseau."),
    (96, "Âge : durée de vie de cette créature (temps simulé)."),
    (114, "Nourritures mangées / poisons touchés depuis sa naissance."),
    (132, "Temps aveugle : part de sa vie passée sans aucune nourriture dans son champ de vision (cône)."),
    (150, "Taille (gène du corps, de {size_min:g} à {size_max:g}), génération de lignée et nombre de petits. Les petits sont la seule chose que la sélection naturelle récompense."),
]
NET_TIPS = {
    "Faim": "Temps depuis la dernière nourriture vue, de 0 à 1 en {hunger} s. Seule entrée qui change quand rien n'est en vue.",
    "Bruit": "Valeur au hasard à chaque tick, entre -1 et 1 : permet une marche aléatoire.",
    "Distance": "Distance à la nourriture visible la plus proche, divisée par la portée. 1 = rien en vue.",
    "Angle": "Direction de cette nourriture par rapport au cap. 0 = droit devant, + = à droite, - = à gauche.",
    "Énergie": "Énergie de la créature, divisée par le maximum.",
    "Vitesse": "Vitesse actuelle, divisée par la vitesse maximale.",
    "Peut manger": "oui = le repas rentrerait en entier dans l'énergie restante. non = la créature est trop pleine.",
    "Dist. poison": "Distance au poison visible le plus proche. 1 = rien en vue.",
    "Angle poison": "Direction de ce poison par rapport au cap (+ = à droite).",
    "Dist. obstacle": "Distance au bord de l'obstacle visible le plus proche. 1 = rien en vue.",
    "Angle obstacle": "Direction de cet obstacle par rapport au cap (+ = à droite).",
    "Virage": "Sortie du réseau : -1 = tourne à gauche à fond, +1 = tourne à droite à fond.",
    "Vit. cible": "Sortie du réseau : vitesse demandée. -1 = à l'arrêt, +1 = vitesse maximale.",
}

HELP_KEYS = [
    ("Espace", "Pause / reprendre"), ("→", "Avancer d'un tick (en pause)"), ("↑  ↓", "Vitesse de simulation"),
    ("D", "Debug : off / sélection / toutes"), ("C", "Couleur : espèce, énergie, vitesse, nourriture, taille, lignée"),
    ("L", "Légende"), ("G", "Courbes : masquées / panneau / grand"), ("N", "Réseau : masqué / petit / grand"),
    ("Tab", "Masquer ou afficher les panneaux"), ("M", "Mini-carte"), ("E", "Naissances et morts dans le monde"),
    ("B", "Sélectionner la créature qui a eu le plus de petits"), ("T", "Suivre la lignée"),
    ("S", "Sauvegarder la population"),
    ("+  -  0  1", "Zoom avant, arrière, toute la carte, échelle d'un écran"), ("V", "Caméra sur la sélection"),
    ("P", "Paramètres"), ("F", "Plein écran"), ("H  ?", "Cette aide"), ("Échap", "Fermer, puis quitter"),
]
# Columns and sections of the settings panel (keys = main.PARAMS). Unknown keys go to «Autres».
PARAM_COLUMNS = (
    (("Évolution", ("mutation", "repro", "age_max", "size_mode")), ("Perception", ("fov",)),
     ("Nourriture", ("food", "food_energy", "respawn"))),
    (("Dangers", ("poison_count", "poison_energy", "obstacle_count")), ("Monde", ("founders", "world_scale"))),
)

HELP_MOUSE = [
    "Molette : zoom sur le pointeur. Glisser dans le monde : déplacer la vue.",
    "Clic sur une créature : fiche, réseau et trajectoire.",
    "Clic dans le vide : désélectionner. Clic sur la mini-carte : y aller.",
    "Glisser le titre du grand réseau : le déplacer.",
    "Survol d'une créature : résumé rapide.",
    "Survol d'un bouton ou d'un libellé : explication.",
]


def wrap(font, text, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.size(trial)[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------- icons (drawn with shapes, so no font has to provide the glyphs) ----------

def _icon(surf, name, rect, color, fonts, u):
    cx, cy = rect.center
    s = rect.w * 0.30                      # Half size of the icon
    w = max(2, round(2 * u))
    if name == "play":
        pygame.draw.polygon(surf, color, [(cx - s * 0.7, cy - s), (cx - s * 0.7, cy + s), (cx + s, cy)])
    elif name == "pause":
        for dx in (-s * 0.55, s * 0.55):
            pygame.draw.rect(surf, color, (cx + dx - s * 0.3, cy - s, s * 0.6, 2 * s))
    elif name == "step":
        pygame.draw.polygon(surf, color, [(cx - s, cy - s), (cx - s, cy + s), (cx + s * 0.5, cy)])
        pygame.draw.rect(surf, color, (cx + s * 0.6, cy - s, s * 0.45, 2 * s))
    elif name in ("minus", "plus"):
        pygame.draw.line(surf, color, (cx - s, cy), (cx + s, cy), w)
        if name == "plus":
            pygame.draw.line(surf, color, (cx, cy - s), (cx, cy + s), w)
    elif name == "cone":
        a0, a1 = math.radians(-60), math.radians(60)
        pts = [(cx - s * 0.9 + s * 2.1 * math.cos(a0 + (a1 - a0) * i / 8) * 0.9 + s * 0.9,
                cy + s * 2.0 * math.sin(a0 + (a1 - a0) * i / 8) * 0.9) for i in range(9)]
        origin = (cx - s * 0.9, cy)
        pygame.draw.lines(surf, color, False, [pts[0], origin, pts[-1]], w)
        pygame.draw.lines(surf, color, False, pts, w)
    elif name == "dots":
        for i, t in enumerate((0.1, 0.5, 0.9)):
            pygame.draw.circle(surf, energy_color(t), (cx + (i - 1) * s * 0.95, cy), max(3, round(s * 0.42)))
    elif name == "info":
        pygame.draw.circle(surf, color, (cx, cy), round(s * 1.15), w)
        img = fonts["small"].render("i", True, color)
        surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
    elif name == "star":
        pts = []
        for i in range(10):
            r = s * 1.25 if i % 2 == 0 else s * 0.55
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(surf, color, pts)
    elif name == "target":
        pygame.draw.circle(surf, color, (cx, cy), round(s * 0.8), w)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(surf, color, (cx + dx * s * 0.8, cy + dy * s * 0.8), (cx + dx * s * 1.35, cy + dy * s * 1.35), w)
    elif name == "net":
        a = [(cx - s, cy - s * 0.8), (cx - s, cy + s * 0.8)]
        b = [(cx, cy - s * 0.9), (cx, cy), (cx, cy + s * 0.9)]
        c = [(cx + s, cy)]
        for p in a:
            for q in b:
                pygame.draw.line(surf, color, p, q, 1)
        for q in b:
            pygame.draw.line(surf, color, q, c[0], 1)
        for p in a + b + c:
            pygame.draw.circle(surf, color, p, max(2, round(s * 0.28)))
    elif name == "sliders":
        for i, k in enumerate((0.3, 0.7, 0.45)):
            y = cy + (i - 1) * s * 0.85
            pygame.draw.line(surf, color, (cx - s, y), (cx + s, y), 1)
            pygame.draw.circle(surf, color, (cx - s + 2 * s * k, y), max(2, round(s * 0.3)))
    elif name == "save":
        body = pygame.Rect(cx - s, cy - s, 2 * s, 2 * s)
        pygame.draw.rect(surf, color, body, w, border_radius=max(1, round(2 * u)))
        pygame.draw.rect(surf, color, (cx - s * 0.5, cy - s, s, s * 0.7))
        pygame.draw.line(surf, color, (cx - s * 0.6, cy + s * 0.35), (cx + s * 0.6, cy + s * 0.35), w)
    elif name == "curves":
        pts = [(cx - s * 1.1, cy + s * 0.7), (cx - s * 0.4, cy - s * 0.2), (cx + s * 0.2, cy + s * 0.3),
               (cx + s * 1.1, cy - s * 0.8)]
        pygame.draw.lines(surf, color, False, pts, w)
        pygame.draw.line(surf, color, (cx - s * 1.2, cy + s * 1.15), (cx + s * 1.2, cy + s * 1.15), 1)
    elif name == "kids":
        pygame.draw.circle(surf, color, (cx, cy - s * 0.45), round(s * 0.55))
        for dx in (-0.8, 0.8):
            pygame.draw.circle(surf, color, (cx + dx * s, cy + s * 0.75), max(2, round(s * 0.34)))
    elif name == "branch":
        pygame.draw.line(surf, color, (cx, cy + s * 1.1), (cx, cy - s * 0.2), w)
        pygame.draw.line(surf, color, (cx, cy + s * 0.25), (cx - s * 0.85, cy - s * 0.7), w)
        pygame.draw.line(surf, color, (cx, cy - s * 0.2), (cx + s * 0.85, cy - s * 0.95), w)
        for p in ((cx - s * 0.85, cy - s * 0.7), (cx + s * 0.85, cy - s * 0.95), (cx, cy - s * 0.2)):
            pygame.draw.circle(surf, color, p, max(2, round(s * 0.26)))
    elif name == "help":
        img = fonts["base"].render("?", True, color)
        surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))


def _button(surf, rect, text, fonts, u, enabled=True, hovered=False, accent=False):
    bg = HOVER if (hovered and enabled) else (ACTIVE_BG if accent and enabled else (34, 41, 48))
    pygame.draw.rect(surf, bg, rect, border_radius=max(3, round(6 * u)))
    pygame.draw.rect(surf, BORDER, rect, width=1, border_radius=max(3, round(6 * u)))
    img = fonts["small"].render(text, True, VALUE if enabled else DIM)
    surf.blit(img, (rect.centerx - img.get_width() // 2, rect.centery - img.get_height() // 2))


class Overlay:
    def __init__(self, hud, scene):
        self.hud, self.scene = hud, scene
        self.layout = None
        self.help_open = False
        self.legend_open = False
        self.params_open = False
        self.net_big = False
        self.toast_text, self.toast_until = None, 0.0   # Short message at the bottom of the world (toast())
        self.setup = None   # Settings screen before a simulation (main.py): {"resume": bool, "cancel": bool} or None
        self.mouse = None
        self.mouse_since = 0.0
        self.state = {}
        self._hits = []           # (rect, action) of the settings panel, rebuilt at each draw
        self._rects = {}          # name → rect of the panels drawn last (for clicks)
        self._cache = {}
        self.start = None             # rendering.startmenu.StartMenu at launch (set by main.py)
        self.chart_big = False        # Large curves view (key G, third press)
        self.charts = ChartView(hud)
        self.minimap = MiniMap()      # Key M
        self.presets = None           # utils.presets.PresetBrowser (set by main.py)
        self.net_pos = None           # Top-left of the large network, once moved
        self._drag = None             # Grab offset while the large network is dragged

    # ---------- state ----------

    def any_modal(self):
        return self.help_open or self.params_open or self.start is not None

    def close_modals(self):
        self.help_open = self.params_open = False

    @property
    def area(self):
        """Free part of the world: not under the menu bar nor under the panels (when shown)."""
        return self.layout.free_area(self.hud.visible)

    def _on_hud(self, x, y):
        hud = self.hud
        if not hud.visible or hud.layout is None:
            return False
        sb = hud.layout.sidebar
        return any(r.move(sb.x, sb.y).collidepoint(x, y) for r in hud.slots.values())

    def blocks(self, x, y):
        """True on a card or a panel: the world under it must neither zoom nor select."""
        if self.any_modal() or self.bar_rect.collidepoint(x, y) or self._on_hud(x, y):
            return True
        if self.minimap.enabled and self.minimap.rect and self.minimap.rect.collidepoint(x, y):
            return True
        if self.chart_big and self.charts.rect and self.charts.rect.collidepoint(x, y):
            return True
        return any(r.collidepoint(x, y) for k, r in self._rects.items() if k in ("legend", "net"))

    def relayout(self, layout):
        self.layout = layout
        u = self.u = layout.scale
        self.fonts = create_fonts(u)
        self._cache.clear()
        w = self.area
        m, pad, bs, gap = round(10 * u), round(6 * u), round(30 * u), round(4 * u)
        x, y = w.x + m + pad, w.y + m + pad
        self.buttons, self.seps, self.speed_rect = [], [], None
        for item in TOOLBAR:
            if item is None:
                self.seps.append(x + round(3 * u))
                x += round(10 * u)
            elif item == "speed":
                self.speed_rect = pygame.Rect(x, y, round(46 * u), bs)
                x += self.speed_rect.w + gap
            else:
                self.buttons.append((pygame.Rect(x, y, bs, bs), *item))
                x += bs + gap
        self.bar_rect = pygame.Rect(w.x + m, w.y + m, x - gap + pad - (w.x + m), bs + 2 * pad)
        bg = pygame.Surface(self.bar_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*PANEL, 40), bg.get_rect(), border_radius=round(10 * u))   # Over frosted glass
        self.bar_bg = bg
        # Pause banner, pre-rendered
        f = self.fonts
        title = f["title"].render("PAUSE", True, AMBER)
        hint = f["small"].render("Espace : reprendre    →  : avancer d'un tick", True, LABEL)
        bw, bh = max(title.get_width(), hint.get_width()) + round(36 * u), title.get_height() + hint.get_height() + round(18 * u)
        banner = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(banner, (*PANEL, 90), banner.get_rect(), border_radius=round(10 * u))
        pygame.draw.rect(banner, (240, 196, 92, 110), banner.get_rect(), width=1, border_radius=round(10 * u))
        banner.blit(title, ((bw - title.get_width()) // 2, round(7 * u)))
        banner.blit(hint, ((bw - hint.get_width()) // 2, round(10 * u) + title.get_height()))
        self.banner = banner
        veil = pygame.Surface(layout.window_size, pygame.SRCALPHA)
        veil.fill((6, 8, 12, 150))
        self.veil = veil

    # ---------- mouse ----------

    def hover(self, x, y):
        if self._drag is not None:   # Dragging the large network by its title
            if pygame.mouse.get_pressed()[0]:
                self.net_pos = (x - self._drag[0], y - self._drag[1])
            else:
                self._drag = None
        if self.mouse is None or abs(x - self.mouse[0]) + abs(y - self.mouse[1]) > 2:
            self.mouse_since = time.monotonic()
        self.mouse = (x, y)

    def click(self, x, y):
        if self.start is not None and not self.params_open:
            return True, self.start.click(x, y)   # Start menu: it takes every click
        """Left click. Returns (consumed, action). The settings panel and the help are modal; the legend and the
        large network only take the clicks that land on them, so another creature can still be picked."""
        if self.help_open:
            self.help_open = False
            return True, None
        if self.params_open:
            for rect, action in self._hits:
                if rect.collidepoint(x, y):
                    return True, action
            panel = self._rects.get("params")
            if not (panel and panel.collidepoint(x, y)) and self.setup is None:
                self.params_open = False   # The setup screen only closes through its buttons
            return True, None
        for rect, action, *_ in self.buttons:
            if rect.collidepoint(x, y):
                return True, action
        if self.bar_rect.collidepoint(x, y):
            return True, None
        if self.chart_big and self.charts.click(x, y):
            return True, None
        if self.minimap.enabled and self.minimap.rect and self.minimap.rect.collidepoint(x, y):
            self.scene.center_on(*self.minimap.to_world(x, y))
            return True, "cam_follow_off"
        net = self._rects.get("net")
        if self.net_big and net and net.collidepoint(x, y) and y < net.y + round(44 * self.u):
            self._drag = (x - net.x, y - net.y)
            return True, None
        if self._on_hud(x, y):
            return True, None
        for name, on in (("legend", self.legend_open), ("net", self.net_big)):
            r = self._rects.get(name)
            if on and r and r.collidepoint(x, y):
                return True, None
        return False, None

    # ---------- drawing ----------

    def toast(self, text, seconds=4.0):
        """Shows `text` at the bottom of the world for a few seconds (saves, extinction...)."""
        self.toast_text, self.toast_until = text, time.monotonic() + seconds

    def draw(self, window, state, world, selected, params):
        """state: paused, speed, debug (0-2), color, follow, graph (0-2). params: rows of the settings panel."""
        self.state = state
        u, f = self.u, self.fonts
        w = self.area
        self._rects = {}

        # Tool bar
        frost(window, self.bar_rect, round(10 * u))
        window.blit(self.bar_bg, self.bar_rect.topleft)
        active = {"pause": state["paused"], "debug": state["debug"] > 0, "legend": self.legend_open,
                  "follow": state["follow"], "graph": state["graph"] > 0, "params_panel": self.params_open,
                  "help": self.help_open, "chart": state.get("chart", 0) > 0, "cam_follow": state.get("cam_follow", False)}
        for rect, action, icon, _, _ in self.buttons:
            on = active.get(action, False)
            hov = self.mouse is not None and rect.collidepoint(self.mouse) and not self.any_modal()
            if on or hov:
                pygame.draw.rect(window, ACTIVE_BG if on else HOVER, rect, border_radius=max(3, round(6 * u)))
            enabled = action != "step" or state["paused"]
            name = "play" if (action == "pause" and state["paused"]) else icon
            _icon(window, name, rect, (MINT if on else (VALUE if enabled else DIM)), f, u)
        for sx in self.seps:
            pygame.draw.line(window, BORDER, (sx, self.bar_rect.y + round(8 * u)), (sx, self.bar_rect.bottom - round(8 * u)))
        limited = state.get("real_speed", 0) and state["real_speed"] < state["speed"] * 0.95 and not state["paused"]
        sp = f["base"].render(f"x{state['real_speed']:.0f}" if limited else f"x{state['speed']}", True,
                              AMBER if limited else VALUE)   # Amber: the machine cannot keep the asked speed
        window.blit(sp, (self.speed_rect.centerx - sp.get_width() // 2, self.speed_rect.centery - sp.get_height() // 2))

        if state["paused"]:
            banner_rect = self.banner.get_rect(midtop=(w.centerx, w.y + round(60 * u)))
            frost(window, banner_rect, round(10 * u))
            window.blit(self.banner, banner_rect.topleft)
        if self.toast_text and time.monotonic() < self.toast_until:
            img = f["base"].render(self.toast_text, True, VALUE)
            box = img.get_rect(midbottom=(w.centerx, w.bottom - round(24 * u))).inflate(round(28 * u), round(14 * u))
            frost(window, box, round(8 * u), alpha=190)
            window.blit(img, img.get_rect(center=box.center))
        if self.minimap.enabled:
            self.minimap.place(w, u)
            self.minimap.draw(window, world, self.scene, u)
        if self.chart_big:
            m = round(12 * u)
            top = self.bar_rect.bottom + m
            self.charts.draw(window, pygame.Rect(w.x + m, top, w.w - 2 * m, w.bottom - top - m), f, u, self.mouse)
        if self.legend_open:
            self._draw_legend(window)
        if self.net_big:
            self._draw_net_big(window, world, selected)
        if self.params_open:
            self._draw_params(window, params)
        if self.help_open:
            self._draw_help(window)
        if self.start is not None and not self.params_open:
            self.start.draw(window, self.layout, f, u, self.mouse)

    def _draw_legend(self, window):
        u, f, w = self.u, self.fonts, self.area
        label = self.scene.color_label()
        key = ("legend", label)
        if key not in self._cache:
            row_h, pad, icon_w = round(24 * u), round(12 * u), round(40 * u)
            entries = [("dot", config.FOOD_COLOR, "Nourriture : redonne de l'énergie"),
                       ("diamond", config.POISON_COLOR, "Poison : retire de l'énergie")]
            if hasattr(config, "OBSTACLE_COLOR"):
                entries.append(("anemone", None, "Anémone : obstacle infranchissable"))
            low, high = {"énergie": ("vide", "pleine"), "vitesse": ("à l'arrêt", "vitesse max"),
                         "nourriture": ("rien mangé", "le plus mangé")}.get(label, ("bas", "haut"))
            entries += [("gradient", None, f"Couleur d'une créature = {label}  ({low} → {high})")
                        if label not in ("lignée", "espèce") else
                        ("ring", (230, 236, 244), "Couleur d'une créature = sa " + label),
                        ("cone", config.DEBUG_VISION_COLOR, "Cône de vision (touche D)"),
                        ("ring", (255, 255, 255), "Créature sélectionnée")]
            text_w = max(f["small"].size(t)[0] for _, _, t in entries)
            surf = pygame.Surface((pad * 2 + icon_w + text_w, pad * 2 + row_h * len(entries) - round(4 * u)), pygame.SRCALPHA)
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
                                         (cx + math.cos(ang) * rad * 0.8, cy + math.sin(ang) * rad * 0.8), max(1, round(1.5 * u)))
                elif kind == "gradient":
                    gw = icon_w - round(4 * u)
                    for k in range(gw):
                        pygame.draw.line(surf, body_color(k / max(gw - 1, 1)), (cx - gw // 2 + k, cy - round(4 * u)),
                                         (cx - gw // 2 + k, cy + round(4 * u)))
                elif kind == "cone":
                    r = round(11 * u)
                    a = math.radians(40)
                    o = (cx - r // 2, cy)
                    pts = [(o[0] + r * math.cos(-a + 2 * a * j / 6), o[1] + r * math.sin(-a + 2 * a * j / 6)) for j in range(7)]
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
        self._rects["legend"] = rect

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

    def _draw_params(self, window, params):
        """Settings panel and setup screen, in frosted glass. Two columns of sections, the species, the presets, and the
        full description of the setting under the mouse at the bottom."""
        u, f, w = self.u, self.fonts, self.area
        self._hits = []
        pad, gap = round(18 * u), round(16 * u)
        mouse = self.mouse
        by_key = {p[0]: p for p in params}
        sections = [[(title, [k for k in keys if k in by_key]) for title, keys in col] for col in PARAM_COLUMNS]
        known = {k for col in PARAM_COLUMNS for _, keys in col for k in keys}
        others = [k for k in by_key if k not in known]
        if others:
            sections[1].append(("Autres", others))
        species = list(PROFILES)
        head_h, preset_h, desc_h, foot_h = round(70 * u), round(40 * u), round(46 * u), round(52 * u)
        sec_h = round(26 * u)

        def column_rows(col, with_species):
            n_rows = sum(len(keys) for _, keys in col)
            n_heads = sum(1 for _, keys in col if keys) + (1 if with_species else 0)
            return n_rows, n_heads, (len(species) if with_species else 0)

        left, right = column_rows(sections[0], False), column_rows(sections[1], True)
        avail = w.h - round(24 * u) - head_h - preset_h - desc_h - foot_h
        row_h = round(34 * u)
        sp_h = round(24 * u)
        need = max(l[0] * row_h + l[1] * sec_h + l[2] * sp_h for l in (left, right))
        if need > avail:   # Small window: everything gets tighter
            k = max(0.55, avail / need)
            row_h, sec_h, sp_h = round(row_h * k), round(sec_h * k), round(sp_h * k)
            need = max(l[0] * row_h + l[1] * sec_h + l[2] * sp_h for l in (left, right))
        pw = min(round(940 * u), w.w - round(24 * u))
        rect = pygame.Rect(0, 0, pw, head_h + preset_h + need + desc_h + foot_h)
        rect.center = w.center
        window.blit(self.veil, (0, 0))
        frost(window, rect, round(14 * u), alpha=185)
        self._rects["params"] = rect

        title = "Nouvelle simulation" if self.setup is not None else "Paramètres de simulation"
        window.blit(f["title"].render(title, True, VALUE), (rect.x + pad, rect.y + round(12 * u)))
        if self.setup is not None:
            line = ("Règle le monde avant de lancer : rien ne tourne encore. Orange = changé. "
                    + ("« Reprendre » repart de la population gardée." if self.setup["resume"]
                       else "« Lancer » crée une population au hasard."))
        else:
            line = ("Les changements s'appliquent tout de suite, sauf obstacles, taille du monde, gène de taille, "
                    "fondateurs et espèces (au prochain départ).")
        window.blit(f["small"].render(_clip(f["small"], line, pw - 2 * pad), True, LABEL),
                    (rect.x + pad, rect.y + round(44 * u)))

        def button(r, text, action, enabled=True, accent=False):
            _button(window, r, text, f, u, enabled, mouse is not None and r.collidepoint(mouse), accent)
            if enabled:
                self._hits.append((r, action))

        # Presets
        py = rect.y + head_h
        bh = round(28 * u)
        lab = f["base"].render("Préréglage", True, AMBER)
        window.blit(lab, (rect.x + pad, py + (bh - lab.get_height()) // 2))
        x = rect.x + pad + lab.get_width() + round(14 * u)
        name = self.presets.label() if self.presets is not None else "indisponible"
        for action, text in (("preset_prev", "<"),):
            r = pygame.Rect(x, py, bh, bh)
            button(r, text, action, self.presets is not None)
            x = r.right + round(4 * u)
        name_w = round(260 * u)
        box = pygame.Rect(x, py, name_w, bh)
        pygame.draw.rect(window, (10, 13, 17), box, border_radius=max(3, round(6 * u)))
        img = f["small"].render(_clip(f["small"], name, name_w - round(12 * u)), True, VALUE)
        window.blit(img, (box.x + round(8 * u), box.centery - img.get_height() // 2))
        r = pygame.Rect(box.right + round(4 * u), py, bh, bh)
        button(r, ">", "preset_next", self.presets is not None)
        x = r.right + round(10 * u)
        for action, text in (("preset_apply", "Appliquer"), ("preset_save", "Enregistrer les réglages actuels")):
            bw = f["small"].size(text)[0] + round(22 * u)
            r = pygame.Rect(x, py, bw, bh)
            if r.right <= rect.right - pad:
                button(r, text, action, self.presets is not None and (action != "preset_apply" or bool(self.presets.files)))
            x = r.right + round(8 * u)

        # Two columns of settings
        col_w = (pw - 2 * pad - gap) // 2
        ab = max(round(18 * u), min(round(24 * u), row_h - round(8 * u)))
        vw = min(round(150 * u), col_w // 3)
        hovered_desc = None
        any_pending = False
        top = rect.y + head_h + preset_h
        for ci, col in enumerate(sections):
            x0 = rect.x + pad + ci * (col_w + gap)
            y = top
            for sec_title, keys in col:
                if not keys:
                    continue
                img = f["small"].render(sec_title.upper(), True, DIM)
                window.blit(img, (x0, y + sec_h - img.get_height() - round(4 * u)))
                pygame.draw.line(window, (70, 80, 92), (x0 + img.get_width() + round(8 * u), y + sec_h - img.get_height() // 2 - round(4 * u)),
                                 (x0 + col_w, y + sec_h - img.get_height() // 2 - round(4 * u)))
                y += sec_h
                for key in keys:
                    _, label, desc, cur, pend = by_key[key]
                    row = pygame.Rect(x0 - round(6 * u), y, col_w + round(12 * u), row_h)
                    if mouse and row.collidepoint(mouse):
                        pygame.draw.rect(window, (40, 48, 58), row, border_radius=round(6 * u))
                        hovered_desc = (label, desc)
                    r_inc = pygame.Rect(x0 + col_w - ab, row.centery - ab // 2, ab, ab)
                    val = pygame.Rect(r_inc.x - vw - round(4 * u), row.centery - ab // 2, vw, ab)
                    r_dec = pygame.Rect(val.x - ab - round(4 * u), row.centery - ab // 2, ab, ab)
                    for r, sign in ((r_dec, -1), (r_inc, 1)):
                        hov = mouse is not None and r.collidepoint(mouse)
                        pygame.draw.rect(window, HOVER if hov else (34, 41, 48), r, border_radius=max(3, round(5 * u)))
                        cx, cy, s = r.centerx, r.centery, round(4 * u)
                        pygame.draw.polygon(window, VALUE, [(cx - sign * s * 0.6, cy - s), (cx - sign * s * 0.6, cy + s),
                                                            (cx + sign * s * 0.9, cy)])
                    self._hits.append((r_dec, f"param:dec:{key}"))
                    self._hits.append((r_inc, f"param:inc:{key}"))
                    pygame.draw.rect(window, (10, 13, 17), val, border_radius=max(3, round(5 * u)))
                    text, color = (pend, AMBER) if pend is not None else (cur, VALUE)
                    any_pending = any_pending or pend is not None
                    img = f["base"].render(_clip(f["base"], text, vw - round(8 * u)), True, color)
                    window.blit(img, (val.centerx - img.get_width() // 2, val.centery - img.get_height() // 2))
                    img = f["base"].render(_clip(f["base"], label, r_dec.x - x0 - round(8 * u)), True,
                                           AMBER if pend is not None else VALUE)
                    window.blit(img, (x0, row.centery - img.get_height() // 2))
                    y += row_h
            if ci == 1:
                # Species: tick boxes (applied at the next start)
                ticked = self.state.get("profiles", list(config.ACTIVE_PROFILES))
                img = f["small"].render("ESPÈCES (AU PROCHAIN DÉPART)", True, AMBER if self.state.get("profiles_pending") else DIM)
                window.blit(img, (x0, y + sec_h - img.get_height() - round(4 * u)))
                y += sec_h
                for name in species:
                    row = pygame.Rect(x0 - round(6 * u), y, col_w + round(12 * u), sp_h)
                    if mouse and row.collidepoint(mouse):
                        pygame.draw.rect(window, (40, 48, 58), row, border_radius=round(6 * u))
                        hovered_desc = (PROFILES[name]["title"], "Coche ou décoche cette espèce. Il en faut au moins une. "
                                        "Le changement s'applique au prochain départ (« Lancer » ou « Repartir de zéro »).")
                    cb = pygame.Rect(x0, row.centery - round(7 * u), round(14 * u), round(14 * u))
                    if name in ticked:
                        pygame.draw.rect(window, MINT, cb, border_radius=3)
                    else:
                        pygame.draw.rect(window, DIM, cb, width=1, border_radius=3)
                    pygame.draw.circle(window, PROFILES[name]["color"], (cb.right + round(14 * u), row.centery), max(3, round(5 * u)))
                    img = f["small"].render(PROFILES[name]["title"], True, VALUE if name in ticked else DIM)
                    window.blit(img, (cb.right + round(26 * u), row.centery - img.get_height() // 2))
                    self._hits.append((row, f"profile:{name}"))
                    y += sp_h

        # Description of the setting under the mouse
        dy = rect.bottom - foot_h - desc_h + round(4 * u)
        pygame.draw.line(window, (70, 80, 92), (rect.x + pad, dy - round(4 * u)), (rect.right - pad, dy - round(4 * u)))
        if hovered_desc:
            lab, desc = hovered_desc
            lines = wrap(f["small"], f"{lab} : {desc}", pw - 2 * pad)[:2]
        else:
            lines = ["Survole un réglage pour lire sa description complète. Flèches : valeur précédente / suivante."]
        for i, t in enumerate(lines):
            window.blit(f["small"].render(t, True, LABEL), (rect.x + pad, dy + round(4 * u) + i * (f["small"].get_height() + round(2 * u))))

        # Footer buttons, right to left
        by, bh = rect.bottom - foot_h + round(12 * u), round(30 * u)
        x = rect.right - pad
        if self.setup is not None:
            buttons = (("setup_launch", "Lancer", True, True),)
            if self.setup["resume"]:
                buttons += (("setup_resume", "Reprendre la population gardée", True, False),)
            if self.setup["cancel"]:
                buttons += (("setup_cancel", "Annuler", True, False),)
            if self.setup.get("from_start"):
                buttons += (("start_back", "Retour", True, False),)
            buttons += (("params_cancel", "Annuler les changements", any_pending, False),)
        else:
            buttons = (("params_close", "Fermer", True, False), ("restart_now", "Repartir de zéro", True, any_pending),
                       ("params_cancel", "Annuler les changements", any_pending, False))
        for action, text, enabled, accent in buttons:
            bw = f["small"].size(text)[0] + round(24 * u)
            r = pygame.Rect(x - bw, by, bw, bh)
            button(r, text, action, enabled, accent)
            x = r.x - round(8 * u)

    def _draw_net_big(self, window, world, selected):
        u, f, w = self.u, self.fonts, self.area
        pw, ph = round(w.w * 0.56), round(w.h * 0.62)
        rect = pygame.Rect(0, 0, pw, ph)
        if self.net_pos is None:
            rect.bottomright = (w.right - round(12 * u), w.bottom - round(12 * u))
        else:
            rect.topleft = self.net_pos
        rect.clamp_ip(w)
        self.net_pos = rect.topleft
        frost(window, rect, round(12 * u), alpha=150)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*PANEL, 60), surf.get_rect(), border_radius=round(12 * u))
        grab = f["small"].render("Glisser le titre pour déplacer", True, DIM)
        surf.blit(grab, (pw - round(16 * u) - grab.get_width(), round(16 * u)))
        pad = round(16 * u)
        surf.blit(f["title"].render("Réseau de la créature sélectionnée", True, VALUE), (pad, round(10 * u)))
        self._rects["net"] = rect
        if selected is None or not selected.alive:
            note = "Clique sur une créature vivante." if selected is None else "Créature morte."
            surf.blit(f["base"].render(note, True, LABEL), (pad, round(48 * u)))
            window.blit(surf, rect.topleft)
            return
        flag = selected.food_nearby
        inputs = world.sense(selected)
        selected.food_nearby = flag
        hidden, outputs = selected.brain.activations(inputs)
        rows = network_rows(inputs, outputs, selected.profile)
        n_in, n_h, n_out = len(inputs), len(hidden), len(outputs)
        top, bottom = round(52 * u), round(34 * u)
        left_w, right_w = round(190 * u), round(140 * u)
        area = pygame.Rect(left_w, top, pw - left_w - right_w, ph - top - bottom)
        xs = (area.x, area.centerx, area.right)

        def column(x, n):
            step = area.h / n
            return [(x, int(area.y + step * (k + 0.5))) for k in range(n)]

        pin, ph_, pout = column(xs[0], n_in), column(xs[1], n_h), column(xs[2], n_out)
        r = max(5, min(round(13 * u), int(area.h / max(n_in, n_h, n_out) / 2.3)))
        wmax = max(float(abs(selected.brain.w1).max()),
                   float(abs(selected.brain.w2).max()) if selected.brain.w2.size else 0.0, 1e-9)
        if n_h == 0:   # No hidden neuron: inputs wired straight to the outputs
            for o in range(n_out):
                for i in range(n_in):
                    _edge(surf, pin[i], pout[o], float(selected.brain.w1[o, i]), float(inputs[i]), wmax)
        for h in range(n_h):
            for i in range(n_in):
                _edge(surf, pin[i], ph_[h], float(selected.brain.w1[h, i]), float(inputs[i]), wmax)
        for o in range(n_out):
            for h in range(n_h):
                _edge(surf, ph_[h], pout[o], float(selected.brain.w2[o, h]), float(hidden[h]), wmax)
        for pos, v in zip(pin, inputs):
            _node(surf, *pos, r, float(v))
        for pos, v in zip(ph_, hidden):
            _node(surf, *pos, r, float(v))
        for pos, v in zip(pout, outputs):
            _node(surf, *pos, r, float(v))
        sm = f["small"]
        for (label, txt, _, _, _), (x, y) in zip(rows[:n_in], pin):
            lab = sm.render(label, True, LABEL)
            surf.blit(lab, (x - r - round(8 * u) - lab.get_width(), y - lab.get_height() // 2))
            val = sm.render(txt, True, MINT)
            surf.blit(val, (x - r - round(16 * u) - lab.get_width() - val.get_width(), y - val.get_height() // 2))
        for (label, txt, _, _, _), (x, y) in zip(rows[n_in:], pout):
            lab = sm.render(label, True, LABEL)
            surf.blit(lab, (x + r + round(8 * u), y - lab.get_height() // 2))
            val = sm.render(txt, True, AMBER)
            surf.blit(val, (x + r + round(8 * u), y + lab.get_height() // 2 - round(1 * u)))
        cap = sm.render("Neurone : vert = activation positive, rouge = négative.  Lien : couleur = signe du signal, "
                        "épaisseur = force.  N : changer la taille.", True, DIM)
        surf.blit(pygame.transform.smoothscale(cap, (min(cap.get_width(), pw - 2 * pad),
                                                     round(cap.get_height() * min(1.0, (pw - 2 * pad) / cap.get_width()))))
                  if cap.get_width() > pw - 2 * pad else cap, (pad, ph - bottom + round(10 * u)))
        window.blit(surf, rect.topleft)

    # ---------- tips ----------

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

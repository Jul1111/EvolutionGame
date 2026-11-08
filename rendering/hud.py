import csv

import pygame
import config
from brain.profiles import PROFILES, input_labels, output_labels
from rendering.scene import energy_color
from utils.timefmt import format_time  # noqa: F401  (main.py imports it from here)

VALUE = config.HUD_VALUE_COLOR
LABEL = config.HUD_LABEL_COLOR
MINT = (120, 224, 176)
AMBER = (240, 196, 92)
CORAL = (222, 96, 78)
BLUE = (110, 180, 235)

# Natural height (logical pixels at scale 1) of the Génération and Créature panels. They are stretched vertically
# (0.85x to 1.9x) to use the room left by the network panel and the curves.
H_CONTENT = 176
H_CHART = 130     # Curves panel in the side bar
GRAPH_H = 120     # Network graph, when shown (natural height)
GRAPH_MIN = 90    # Smallest graph height before the cards are squeezed to make room
CHART_MIN = 100   # Smallest curves panel in the side bar (it disappears if even that does not fit)
KY_MIN = 0.8      # Smallest vertical stretch of the Génération and Créature cards
KY_GOOD = 0.92    # Stretch the cards keep as long as the graph or the curves panel can still fit


# How each network input is displayed, by label: value → (text, signed bar?).
# A label that is not listed here is shown as a plain number with a plain bar.
INPUT_FORMAT = {
    "Distance": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle": lambda v: (f"{v:+.2f}", True),
    "Peut manger": lambda v: ("oui" if v >= 0.5 else "non", False),
    "Dist. poison": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle poison": lambda v: (f"{v:+.2f}", True),
    "Dist. obstacle": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle obstacle": lambda v: (f"{v:+.2f}", True),
    "Contact": lambda v: ("oui" if v >= 0.5 else "non", False),
    "Cap cos": lambda v: (f"{v:+.2f}", True),
    "Cap sin": lambda v: (f"{v:+.2f}", True),
    **{f"Mémoire {i}": (lambda v: (f"{v:+.2f}", True)) for i in range(1, 9)},
}


def network_rows(inputs, outputs, profile):
    """Rows of the network panel: (label, text, value, signed bar?, colour), with the labels of the creature's profile."""
    rows = []
    for label, value in zip(input_labels(profile), inputs):
        value = float(value)
        text, signed = INPUT_FORMAT.get(label, lambda v: (f"{v:.2f}", False))(value)
        rows.append((label, text, value, signed, MINT))
    for label, value in zip(output_labels(profile), outputs):
        value = float(value)
        rows.append((label, f"{value:+.2f}", value, True, AMBER))
    return rows
MAX_PANEL_W = 560    # Logical width cap, for very wide windows




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


def create_fonts(u):
    """Fonts at the real size: every size is multiplied by the interface scale u, so text stays sharp."""
    def make(size, bold=False):
        return pygame.font.SysFont("arial", max(9, round(size * u)), bold=bold)
    return {"title": make(20, True), "base": make(15), "small": make(13)}


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _node(surf, x, y, r, value):
    """Neuron: fill brightness = |activation|, mint if positive, coral if negative."""
    t = max(0.0, min(1.0, abs(value)))
    base = MINT if value >= 0 else CORAL
    pygame.draw.circle(surf, _lerp((38, 46, 54), base, t), (x, y), r)
    pygame.draw.circle(surf, (255, 255, 255, 80), (x, y), r, 1)


def _edge(surf, a, b, weight, source, wmax):
    """Link: colour = sign of the signal (weight x source activation), strength = size of that signal.
    A link carrying no signal stays faintly visible, according to the size of its weight."""
    signal = weight * source
    sign = signal if abs(signal) > 1e-3 else weight
    t = min(1.0, abs(signal))
    alpha = int(min(255, 22 + 190 * t + 40 * abs(weight) / wmax))
    color = (*(MINT if sign >= 0 else CORAL), alpha)
    pygame.draw.line(surf, color, a, b, 1 if t < 0.4 else 2)


class Ctx:
    """Converts logical coordinates to pixels: x/width/size by the scale u, y by u times the vertical stretch."""

    def __init__(self, u, ky=1.0):
        self.u = u
        self.ky = ky

    def x(self, v):
        return round(v * self.u)

    def y(self, v):
        return round(v * self.u * self.ky)


# ---------- drawing helpers ----------

def _panel(width, height, u):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    radius = max(4, round(12 * u))
    pygame.draw.rect(surf, config.HUD_PANEL_COLOR, surf.get_rect(), border_radius=radius)
    pygame.draw.rect(surf, (255, 255, 255, 28), surf.get_rect(), width=1, border_radius=radius)
    return surf


def _bar(surf, x, y, w, h, fraction, color):
    fraction = max(0.0, min(1.0, fraction))
    pygame.draw.rect(surf, (255, 255, 255, 25), (x, y, w, h), border_radius=h // 2)
    if fraction > 0:
        pygame.draw.rect(surf, color, (x, y, max(h, int(w * fraction)), h), border_radius=h // 2)


def _signed_bar(surf, x, y, w, h, value, color):
    """Bar centred on zero, value in [-1, 1]."""
    value = max(-1.0, min(1.0, value))
    pygame.draw.rect(surf, (255, 255, 255, 25), (x, y, w, h), border_radius=h // 2)
    mid = x + w // 2
    length = int(abs(value) * (w // 2))
    if length > 0:
        left = mid if value > 0 else mid - length
        pygame.draw.rect(surf, color, (left, y, length, h), border_radius=h // 2)
    pygame.draw.line(surf, (255, 255, 255, 90), (mid, y - 2), (mid, y + h + 1))


def _text(surf, font, txt, x, y, color, right=False):
    img = font.render(txt, True, color)
    surf.blit(img, (x - img.get_width() if right else x, y))
    return img


def _row(surf, fonts, c, y, label, value, value_color=VALUE):
    pad = c.x(14)
    _text(surf, fonts["base"], label, pad, c.y(y), LABEL)
    _text(surf, fonts["base"], value, surf.get_width() - pad, c.y(y), value_color, right=True)


def _col(name):
    return lambda row: row.get(name)


# Curves that can be shown: (key, label, colour, value(row), fixed maximum or None = largest value seen, text format).
# One point per line of timeline.csv. Each curve is scaled to its own range.
SERIES = [
    ("population", "Population", (204, 172, 132), _col("population"), lambda: config.POP_MAX, lambda v: f"{v:.0f}"),
    ("births", "Naissances (par relevé)", MINT, _col("births"), None, lambda v: f"{v:.0f}"),
    ("deaths_hunger", "Morts de faim (par relevé)", CORAL, _col("deaths_hunger"), None, lambda v: f"{v:.0f}"),
    ("deaths_age", "Morts de vieillesse (par relevé)", (150, 164, 178), _col("deaths_age"), None, lambda v: f"{v:.0f}"),
    ("food_rate", "Repas / 1000 ticks de vie", (90, 200, 110), _col("food_rate"), None, lambda v: f"{v:.2f}"),
    ("poison_rate", "Poisons / 1000 ticks de vie", (176, 96, 214), _col("poison_rate"), None, lambda v: f"{v:.2f}"),
    ("mean_speed", "Vitesse moy.", BLUE, _col("mean_speed"), lambda: config.CREATURE_MAX_SPEED, lambda v: f"{v:.2f}"),
    ("mean_energy", "Énergie moy.", AMBER, _col("mean_energy"), lambda: config.ENERGY_MAX, lambda v: f"{v:.0f}"),
    ("mean_lineage_gen", "Génération de lignée moy.", (160, 190, 255), _col("mean_lineage_gen"), None,
     lambda v: f"{v:.1f}"),
    ("mean_age_at_death", "Âge moyen à la mort", (236, 142, 72), _col("mean_age_at_death"), lambda: config.AGE_MAX or None,
     format_time),
    ("food_available", "Nourritures disponibles", (178, 224, 120), _col("food_available"), None, lambda v: f"{v:.0f}"),
    ("cap_blocked", "Naissances bloquées (plafond)", (230, 122, 182), _col("cap_blocked"), None, lambda v: f"{v:.0f}"),
]
SERIES_BY_KEY = {s[0]: s for s in SERIES}
DEFAULT_SERIES = ("population", "food_rate", "mean_speed", "mean_lineage_gen")


def _clip(font, text, max_w):
    """Text shortened with an ellipsis so that it is at most max_w pixels wide."""
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "…")[0] > max_w:
        text = text[:-1]
    return text + "…"


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


class Hud:
    """Side bar (generation, selected creature, network, curves, key hints) and, when the window is tall,
    a strip under the world with the curves. Everything is drawn at the real resolution (see relayout)."""

    def __init__(self):
        self.show_chart = True    # Curves (in the strip when there is one, else in the side bar)
        self.show_graph = False   # Network drawn as a graph above the bars
        self.chart_keys = set(DEFAULT_SERIES)   # Curves shown (menu Courbes)
        self.layout = None
        self.profiles = list(config.ACTIVE_PROFILES)        # Species in the world
        self.timeline_path = None   # timeline.csv of the running simulation (set by main.py)
        self.rows = []

    # ---------- layout ----------

    def relayout(self, layout):
        """Call whenever the window size changes."""
        self.layout = layout
        self.u = layout.scale
        self.fonts = create_fonts(self.u)
        small = self.fonts["small"]
        hint_color = (110, 122, 128)
        self.hints = [
            small.render("H : aide et raccourcis", True, hint_color),
            small.render("Survole un libellé pour l'expliquer.", True, hint_color),
        ]
        self._compute_slots()

    def _net_height(self):
        """Natural height (logical) of the network panel without the graph."""
        rows_h = 15 * max(len(input_labels(p)) + len(output_labels(p)) for p in self.profiles) + 4
        return 36 + rows_h + 12

    def _fit(self, hints_h, chart):
        """Heights for one choice of hints and curves panel: (space, net_h, graph_h, chart_h), pixels except graph_h
        (logical). The Génération and Créature cards keep a comfortable stretch (KY_GOOD); the graph or the curves panel
        take what is left, up to their natural height. If that is too little, the cards shrink down to KY_MIN."""
        layout, u = self.layout, self.u
        m, gap = round(12 * u), round(8 * u)
        space = layout.sidebar.h - 2 * m - hints_h - gap * (3 + chart)
        net_h = self._net_height() * u
        cards_good = 2 * H_CONTENT * u * KY_GOOD
        cards_min = 2 * H_CONTENT * u * KY_MIN
        graph_h = chart_h = 0.0
        if self.show_graph:
            left = lambda cards: (space - cards - net_h) / u - 12
            graph_h = left(cards_good)
            if graph_h < GRAPH_MIN:
                graph_h = min(GRAPH_MIN, left(cards_min))   # Shrink the cards rather than the graph
            graph_h = max(20.0, min(GRAPH_H, graph_h))
            net_h += (graph_h + 12) * u
        elif chart:
            chart_h = space - cards_good - net_h
            if chart_h < CHART_MIN * u:
                chart_h = min(CHART_MIN * u, space - cards_min - net_h)
            chart_h = min(H_CHART * u, chart_h)
        return space, net_h, graph_h, chart_h

    def _compute_slots(self):
        """Stack the panels in the side bar. The Génération and Créature cards stretch vertically (ky) to use the
        room left by the others. Call again when the curves or the graph are toggled."""
        layout, u = self.layout, self.u
        sb = layout.sidebar
        m, gap = round(12 * u), round(8 * u)
        pw = min(sb.w - 2 * m, round(MAX_PANEL_W * u))
        full_hints_h = sum(h.get_height() for h in self.hints) + 2 * len(self.hints)
        # The curves go under the world when there is a strip; else in the side bar, unless the graph needs the room
        chart = layout.strip is None and self.show_chart and not self.show_graph
        space, net_h, graph_h, chart_h = self._fit(0, chart)
        if chart and chart_h < CHART_MIN * u:
            chart = False   # Not enough room even with small cards: no curves panel in the side bar
            space, net_h, graph_h, chart_h = self._fit(0, False)
        # Key hints (the menu already lists every shortcut): only when the cards would still be comfortable
        self.show_hints = False
        hints_h = 0
        if not self.show_graph and not chart:
            with_hints = self._fit(full_hints_h, False)
            if (with_hints[0] - with_hints[1]) / (2 * H_CONTENT * u) >= KY_GOOD:
                self.show_hints, hints_h = True, full_hints_h
                space, net_h, graph_h, chart_h = with_hints
        self.graph_h = graph_h
        self.ky = max(KY_MIN, min((space - net_h - chart_h) / (2 * H_CONTENT * u), 1.9))
        card_h = round(H_CONTENT * u * self.ky)

        self.slots, y = {}, m
        for name, h in (("gen", card_h), ("creature", card_h), ("net", round(net_h)), ("chart", round(chart_h))):
            if h:
                self.slots[name] = pygame.Rect(m, y, pw, h)
                y += h + gap
        self.hints_y = sb.h - m - hints_h
        self.bg = {name: _panel(r.w, r.h, u) for name, r in self.slots.items() if name != "chart"}

        self.strip_slot = None
        if layout.strip is not None:
            st = layout.strip
            self.strip_slot = pygame.Rect(m, m, st.w - 2 * m, st.h - 2 * m)
        self._build_charts()

    def _build_charts(self):
        self.chart = None         # Curves in the strip under the world (tall windows only)
        self.chart_side = None    # Curves in the side bar (no strip)
        if self.layout is None:
            return
        if self.strip_slot is not None:
            r = self.strip_slot
            self.chart = self._chart(r, True)
        if "chart" in self.slots:
            r = self.slots["chart"]
            self.chart_side = self._chart(r, False)

    def _chart(self, r, wide):
        """Curves of the whole population, one point per line of timeline.csv."""
        return build_chart(self.fonts, self.rows, r.w, r.h, self.u, wide, self.chart_keys)

    def toggle_chart(self):
        self.show_chart = not self.show_chart
        self._compute_slots()

    def toggle_series(self, key):
        if key in SERIES_BY_KEY:
            self.chart_keys ^= {key}
            self._build_charts()

    def reset_series(self):
        self.chart_keys = set(DEFAULT_SERIES)
        self._build_charts()

    def toggle_graph(self):
        self.show_graph = not self.show_graph
        self._compute_slots()

    def reload_stats(self, profiles=None):
        """Call after a new line of timeline.csv, or when the species of the world changed."""
        if profiles:
            self.profiles = list(profiles)
        self.rows = load_timeline(self.timeline_path) if self.timeline_path else []
        if self.layout is not None:
            self._compute_slots()   # The network panel height depends on the species (it ends by rebuilding the charts)

    # ---------- panels ----------

    def _draw_generation(self, world, fps, speed, info, debug_mode, paused, color_label):
        """Population card. info: births, deaths (since the start), extinct (bool)."""
        f, c = self.fonts, Ctx(self.u, self.ky)
        p = self.bg["gen"].copy()
        W, pad = p.get_width(), c.x(14)
        creatures = world.creatures
        n = len(creatures)
        gens = [cr.lineage_gen for cr in creatures]

        _text(p, f["title"], f"Population {n}", pad, c.y(8), VALUE)
        if info.get("extinct"):
            status, status_color = "Extinction", CORAL
        elif paused:
            status, status_color = "Pause", AMBER
        else:
            status, status_color = "En cours", MINT
        img = _text(p, f["small"], status, W - pad, c.y(13), status_color, right=True)
        pygame.draw.circle(p, status_color, (W - pad - img.get_width() - c.x(9), c.y(13) + img.get_height() // 2),
                           max(3, c.x(4)))

        bar_h = max(3, c.x(5))
        _row(p, f, c, 38, "Vivantes / plafond", f"{n}/{config.POP_MAX}")
        _bar(p, pad, c.y(59), W - 2 * pad, bar_h, n / config.POP_MAX if config.POP_MAX else 0, energy_color(0.85))
        _row(p, f, c, 68, "Temps simulé", format_time(world.tick))
        _row(p, f, c, 86, "Naissances / morts", f"{info.get('births', 0)} / {info.get('deaths', 0)}")
        _row(p, f, c, 104, "Lignée moy. / max",
             f"{sum(gens) / n:.1f} / {max(gens)}" if n else "-")
        if len(self.profiles) > 1:
            # One dot (the species colour) and the number of living creatures per species
            _text(p, f["base"], "Espèces", pad, c.y(122), LABEL)
            x = W - pad
            for name in reversed(self.profiles):
                n_alive = sum(1 for cr in creatures if cr.alive and cr.profile == name)
                img = _text(p, f["small"], str(n_alive), x, c.y(124), VALUE, right=True)
                x -= img.get_width() + c.x(5)
                pygame.draw.circle(p, PROFILES[name]["color"], (x - c.x(3), c.y(124) + img.get_height() // 2), max(3, c.x(4)))
                x -= c.x(14)

        debug_label = ("off", "sélection", "toutes")[debug_mode]
        _text(p, f["small"], f"x{speed}  ·  {fps:.0f} FPS", pad, c.y(142), LABEL)
        _text(p, f["small"], f"debug : {debug_label}", W - pad, c.y(142), LABEL, right=True)
        _text(p, f["small"], f"couleur : {color_label}", pad, c.y(158), LABEL)
        return p

    def _draw_creature(self, world, selected):
        f, c = self.fonts, Ctx(self.u, self.ky)
        p = self.bg["creature"].copy()
        W, pad = p.get_width(), c.x(14)
        if selected is None:
            _text(p, f["base"], "Aucune créature sélectionnée", pad, c.y(10), VALUE)
            _text(p, f["small"], "Clique sur une créature dans le monde.", pad, c.y(36), LABEL)
            _text(p, f["small"], "Elle sera suivie, avec sa trajectoire.", pad, c.y(54), LABEL)
            return p
        cr = selected
        img_title = _text(p, f["title"], "Créature", pad, c.y(8), VALUE)
        pygame.draw.circle(p, PROFILES[selected.profile]["color"], (pad + img_title.get_width() + c.x(12), c.y(8) + img_title.get_height() // 2), max(3, c.x(4)))
        _text(p, f["small"], PROFILES[selected.profile]["title"], pad + img_title.get_width() + c.x(20), c.y(13), LABEL)
        state, state_color = ("Vivante", MINT) if cr.alive else ("Morte", CORAL)
        img = _text(p, f["small"], state, W - pad, c.y(13), state_color, right=True)
        pygame.draw.circle(p, state_color, (W - pad - img.get_width() - c.x(9), c.y(13) + img.get_height() // 2),
                           max(3, c.x(4)))

        bar_h = max(3, c.x(5))
        energy_ratio = cr.energy / config.ENERGY_INPUT_MAX
        _row(p, f, c, 36, "Énergie", f"{max(cr.energy, 0):.1f}")
        _bar(p, pad, c.y(57), W - 2 * pad, bar_h, energy_ratio, energy_color(max(0.0, min(energy_ratio, 1.0))))
        _row(p, f, c, 66, "Vitesse", f"{cr.speed:.2f}")
        _bar(p, pad, c.y(87), W - 2 * pad, bar_h, cr.speed / config.CREATURE_MAX_SPEED, BLUE)
        _row(p, f, c, 96, "Âge", format_time(cr.age))
        _row(p, f, c, 114, "Nourriture / poison", f"{cr.food_eaten} / {cr.poison_hits}")
        blind_share = cr.blind_ticks / cr.age if cr.age else 0.0
        _row(p, f, c, 132, "Temps aveugle", f"{blind_share:.0%}")
        _row(p, f, c, 150, "Génération / petits", f"{cr.lineage_gen} / {cr.children}")
        return p

    def _draw_network(self, world, selected):
        f, c = self.fonts, Ctx(self.u)   # No vertical stretch: the graph takes the room instead
        p = self.bg["net"].copy()
        W, H, pad = p.get_width(), p.get_height(), c.x(14)
        _text(p, f["title"], "Réseau de neurones", pad, c.x(8), VALUE)
        if selected is None or not selected.alive:
            note = "Sélectionne une créature vivante." if selected is None else "Créature morte."
            _text(p, f["small"], note, pad, c.x(40), LABEL)
            return p

        # World.sense also sets food_nearby (a metric): put it back as it was
        flag = selected.food_nearby
        inputs = world.sense(selected)
        selected.food_nearby = flag
        hidden, outputs = selected.brain.activations(inputs)

        rows = network_rows(inputs, outputs, selected.profile)
        n_in = len(inputs)
        rows_top = c.x(36)
        if self.show_graph:
            graph = pygame.Rect(pad, c.x(32), W - 2 * pad, round(self.graph_h * self.u))
            self._draw_graph(p, graph, selected.brain, inputs, hidden, outputs, selected.profile)
            rows_top = graph.bottom + c.x(12)

        x0 = c.x(96)
        bw = W - x0 - c.x(84)
        bar_h = max(3, c.x(5))
        for i, (label, txt, value, signed, color) in enumerate(rows):
            y = rows_top + c.x(i * 15 + (4 if i >= n_in else 0))
            _text(p, f["small"], label, pad, y, LABEL)
            by = y + (f["small"].get_height() - bar_h) // 2
            if signed:
                _signed_bar(p, x0, by, bw, bar_h, value, color)
            else:
                _bar(p, x0, by, bw, bar_h, value, color)
            _text(p, f["small"], txt, W - pad, y, VALUE, right=True)
        ly = rows_top + c.x(n_in * 15) + c.x(1)
        pygame.draw.line(p, (255, 255, 255, 30), (pad, ly), (W - pad, ly))
        return p

    def _draw_graph(self, p, rect, brain, x_in, hidden, outputs, profile):
        """The network as a graph: inputs, hidden layer, outputs. Neuron brightness = activation, link colour = sign of
        the signal it carries, link strength = size of that signal. Biases are not drawn."""
        f, c = self.fonts, Ctx(self.u)
        n_in, n_h, n_out = len(x_in), len(hidden), len(outputs)
        label_w = c.x(80)
        xs = (rect.x + label_w, rect.centerx, rect.right - label_w)
        if n_h == 0:
            xs = (rect.x + label_w, rect.centerx, rect.right - label_w)   # Inputs wired straight to the outputs

        def column(x, n):
            step = rect.h / n
            return [(x, int(rect.y + step * (k + 0.5))) for k in range(n)]

        pin, ph, pout = column(xs[0], n_in), column(xs[1], n_h), column(xs[2], n_out)
        r = max(4, min(c.x(9), int(rect.h / max(n_in, n_h, n_out) / 2.4)))
        wmax = max(float(abs(brain.w1).max()), float(abs(brain.w2).max()) if brain.w2.size else 0.0, 1e-9)
        if n_h == 0:
            for o in range(n_out):
                for i in range(n_in):
                    _edge(p, pin[i], pout[o], float(brain.w1[o, i]), float(x_in[i]), wmax)
        for h in range(n_h):
            for i in range(n_in):
                _edge(p, pin[i], ph[h], float(brain.w1[h, i]), float(x_in[i]), wmax)
        for o in range(n_out):
            for h in range(n_h):
                _edge(p, ph[h], pout[o], float(brain.w2[o, h]), float(hidden[h]), wmax)
        for pos, v in zip(pin, x_in):
            _node(p, *pos, r, float(v))
        for pos, v in zip(ph, hidden):
            _node(p, *pos, r, float(v))
        for pos, v in zip(pout, outputs):
            _node(p, *pos, r, float(v))
        th = f["small"].get_height()
        for label, (x, y) in zip(input_labels(profile), pin):
            _text(p, f["small"], label, x - r - c.x(6), y - th // 2, LABEL, right=True)
        for label, (x, y) in zip(output_labels(profile), pout):
            _text(p, f["small"], label, x + r + c.x(6), y - th // 2, LABEL)

    # ---------- frame ----------

    def draw(self, sidebar, strip, world, fps, speed, info, debug_mode, paused, selected, color_label):
        """sidebar: surface of layout.sidebar. strip: surface of layout.strip, or None."""
        sidebar.fill(config.SIDEBAR_BG_COLOR)
        pygame.draw.line(sidebar, (48, 54, 60), (0, 0), (0, sidebar.get_height()))
        panels = {
            "gen": lambda: self._draw_generation(world, fps, speed, info, debug_mode, paused, color_label),
            "creature": lambda: self._draw_creature(world, selected),
            "net": lambda: self._draw_network(world, selected),
            "chart": lambda: self.chart_side,
        }
        for name, rect in self.slots.items():
            panel = panels[name]()
            if panel is not None:
                sidebar.blit(panel, rect.topleft)
        hy = self.hints_y
        for img in self.hints if self.show_hints else ():
            sidebar.blit(img, (self.slots["gen"].x + 2, hy))
            hy += img.get_height() + 2

        if strip is not None:
            strip.fill(config.SIDEBAR_BG_COLOR)
            pygame.draw.line(strip, (48, 54, 60), (0, 0), (strip.get_width(), 0))
            if self.show_chart and self.chart is not None:
                strip.blit(self.chart, self.strip_slot.topleft)

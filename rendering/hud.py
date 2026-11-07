import csv

import pygame
import config
from rendering.scene import energy_color

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
GRAPH_H = 120     # Network graph, when shown


# How each network input is displayed, by label: value → (text, signed bar?).
# A label that is not listed here is shown as a plain number with a plain bar.
INPUT_FORMAT = {
    "Distance": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle": lambda v: (f"{v:+.2f}", True),
    "Peut manger": lambda v: ("oui" if v >= 0.5 else "non", False),
}


def network_rows(inputs, outputs):
    """Rows of the network panel: (label, text, value, signed bar?, colour). Driven by config.INPUT_LABELS and OUTPUT_LABELS."""
    rows = []
    for label, value in zip(config.INPUT_LABELS, inputs):
        value = float(value)
        text, signed = INPUT_FORMAT.get(label, lambda v: (f"{v:.2f}", False))(value)
        rows.append((label, text, value, signed, MINT))
    for label, value in zip(config.OUTPUT_LABELS, outputs):
        value = float(value)
        rows.append((label, f"{value:+.2f}", value, True, AMBER))
    return rows
MAX_PANEL_W = 560    # Logical width cap, for very wide windows


def format_time(ticks):
    """Convert a number of ticks to a mm:ss string (simulated time)."""
    seconds = ticks / config.TICKS_PER_SECOND
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None  # Empty cell (e.g. blind_speed when no tick was blind) or missing column


def load_stats():
    """Read saves/stats.csv. List of dicts, values are floats or None. Empty list if the file is missing."""
    rows = []
    try:
        with open(config.STATS_FILE, newline="", encoding="utf-8") as f:
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


def build_chart(fonts, stats, width, height, u, wide):
    """Pre-render the per-generation curves. Each curve is scaled to its own range.
    wide=False: plot on top, legend below (side bar). wide=True: plot on the left, legend on the right (strip)."""
    c = Ctx(u)
    surf = _panel(width, height, u)
    pad = c.x(14)
    _text(surf, fonts["base"], "Courbes par génération", pad, c.x(7), VALUE)
    _text(surf, fonts["small"], "échelles propres", width - pad, c.x(9), LABEL, right=True)

    if wide:
        plot = pygame.Rect(pad, c.x(30), int(width * 0.62), height - c.x(30) - pad)
    else:
        legend_h = 4 * c.x(16)
        plot_h = max(c.x(30), height - c.x(28) - legend_h - c.x(16))
        plot = pygame.Rect(pad, c.x(28), width - 2 * pad, plot_h)
    pygame.draw.rect(surf, (255, 255, 255, 14), plot, border_radius=max(3, c.x(6)))
    if not stats:
        msg = fonts["small"].render("Pas encore de données", True, LABEL)
        surf.blit(msg, (plot.centerx - msg.get_width() // 2, plot.centery - msg.get_height() // 2))
        return surf

    def column(key):
        return [r.get(key) for r in stats]

    food_max = max([v for v in column("mean_food") if v is not None] + [1.0])
    blind_max = max([v for v in column("blind_frac") if v is not None] + [0.01])
    series = [
        ("Meilleur âge", AMBER, "best_age", config.GEN_MAX_TICKS, lambda v: format_time(v)),
        ("Nourriture moy.", config.FOOD_COLOR, "mean_food", food_max, lambda v: f"{v:.0f}"),
        ("Vitesse moy.", BLUE, "mean_speed", config.CREATURE_MAX_SPEED, lambda v: f"{v:.2f}"),
        ("Part aveugle", CORAL, "blind_frac", blind_max, lambda v: f"{v:.0%}"),
    ]
    n = len(stats)
    margin = c.x(3)
    for i, (label, color, key, vmax, fmt) in enumerate(series):
        values = column(key)
        pts = []
        for j, v in enumerate(values):
            if v is None:
                continue
            px = plot.left + (plot.width * j / (n - 1) if n > 1 else plot.width / 2)
            py = plot.bottom - margin - min(v / vmax, 1.0) * (plot.height - 2 * margin)
            pts.append((px, py))
        if len(pts) > 1:
            pygame.draw.aalines(surf, color, False, pts)
        elif pts:
            pygame.draw.circle(surf, color, (int(pts[0][0]), int(pts[0][1])), max(2, c.x(3)))
        if wide:
            row_h = plot.height / 4
            ly = int(plot.top + i * row_h + row_h / 2 - fonts["small"].get_height() / 2)
            lx = plot.right + c.x(24)
        else:
            ly = plot.bottom + c.x(6) + i * c.x(16)
            lx = pad
        dot_r = max(3, c.x(4))
        pygame.draw.circle(surf, color, (lx + c.x(6), ly + fonts["small"].get_height() // 2), dot_r)
        _text(surf, fonts["small"], label, lx + c.x(16), ly, LABEL)
        last = next((v for v in reversed(values) if v is not None), None)
        _text(surf, fonts["small"], fmt(last) if last is not None else "n/a", width - pad, ly, VALUE, right=True)
    return surf


class Hud:
    """Side bar (generation, selected creature, network, curves, key hints) and, when the window is tall,
    a strip under the world with the curves. Everything is drawn at the real resolution (see relayout)."""

    def __init__(self):
        self.show_chart = True    # Curves (in the strip when there is one, else in the side bar)
        self.show_graph = False   # Network drawn as a graph above the bars
        self.layout = None
        self.stats = load_stats()

    # ---------- layout ----------

    def relayout(self, layout):
        """Call whenever the window size changes."""
        self.layout = layout
        self.u = layout.scale
        self.fonts = create_fonts(self.u)
        small = self.fonts["small"]
        hint_color = (110, 122, 128)
        self.hints = [
            small.render("Clic : sélectionner   Espace : pause   → : 1 tick", True, hint_color),
            small.render("D : debug  C : couleur  F : plein écran", True, hint_color),
            small.render("G : courbes   N : graphe du réseau", True, hint_color),
        ]
        self._compute_slots()

    def _net_height(self):
        """Natural height (logical) of the network panel."""
        rows_h = 15 * (len(config.INPUT_LABELS) + len(config.OUTPUT_LABELS)) + 4
        return 36 + (GRAPH_H + 12 if self.show_graph else 0) + rows_h + 12

    def _compute_slots(self):
        """Stack the panels in the side bar. The Génération and Créature cards stretch vertically (ky) to use the
        room left by the others. Call again when the curves or the graph are toggled."""
        layout, u = self.layout, self.u
        sb = layout.sidebar
        m, gap = round(12 * u), round(8 * u)
        pw = min(sb.w - 2 * m, round(MAX_PANEL_W * u))
        hints_h = sum(h.get_height() for h in self.hints) + 2 * len(self.hints)
        # The curves go under the world when there is a strip; else in the side bar, unless the graph needs the room
        chart_in_sidebar = layout.strip is None and self.show_chart and not self.show_graph
        net_h = round(self._net_height() * u)
        chart_h = round(H_CHART * u) if chart_in_sidebar else 0
        n_panels = 3 + (1 if chart_in_sidebar else 0)
        avail = sb.h - 2 * m - hints_h - gap * n_panels - net_h - chart_h
        self.ky = max(0.85, min(avail / (2 * H_CONTENT * u), 1.9))
        card_h = round(H_CONTENT * u * self.ky)

        self.slots, y = {}, m
        for name, h in (("gen", card_h), ("creature", card_h), ("net", net_h), ("chart", chart_h)):
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
            self.chart = build_chart(self.fonts, self.stats, r.w, r.h, self.u, wide=True)
        if "chart" in self.slots:
            r = self.slots["chart"]
            self.chart_side = build_chart(self.fonts, self.stats, r.w, r.h, self.u, wide=False)

    def toggle_chart(self):
        self.show_chart = not self.show_chart
        self._compute_slots()

    def toggle_graph(self):
        self.show_graph = not self.show_graph
        self._compute_slots()

    def reload_stats(self):
        """Call after a generation has been logged."""
        self.stats = load_stats()
        self._build_charts()

    # ---------- panels ----------

    def _draw_generation(self, world, fps, speed, generation, debug_mode, paused, color_label):
        f, c = self.fonts, Ctx(self.u, self.ky)
        p = self.bg["gen"].copy()
        W, pad = p.get_width(), c.x(14)
        creatures = world.creatures
        total = len(creatures)
        alive = sum(1 for cr in creatures if cr.alive)
        best_age = max((cr.age for cr in creatures), default=0)
        zero_food = sum(1 for cr in creatures if cr.food_eaten == 0)
        over = world.is_over()

        _text(p, f["title"], f"Génération {generation}", pad, c.y(8), VALUE)
        if paused:
            status, status_color = "Pause", AMBER
        elif over:
            status, status_color = "Terminé", CORAL
        else:
            status, status_color = "En cours", MINT
        img = _text(p, f["small"], status, W - pad, c.y(13), status_color, right=True)
        pygame.draw.circle(p, status_color, (W - pad - img.get_width() - c.x(9), c.y(13) + img.get_height() // 2),
                           max(3, c.x(4)))

        bar_h = max(3, c.x(5))
        _row(p, f, c, 38, "Vivantes", f"{alive}/{total}")
        _bar(p, pad, c.y(59), W - 2 * pad, bar_h, alive / total if total else 0, energy_color(0.85))
        _row(p, f, c, 68, "Temps", f"{format_time(world.tick)} / {format_time(config.GEN_MAX_TICKS)}")
        _bar(p, pad, c.y(89), W - 2 * pad, bar_h, world.tick / config.GEN_MAX_TICKS, energy_color(0.5))
        _row(p, f, c, 98, "Meilleur âge", format_time(best_age))
        _row(p, f, c, 116, "Sans nourriture", str(zero_food))

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
        _text(p, f["title"], "Créature", pad, c.y(8), VALUE)
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
        _row(p, f, c, 114, "Nourriture mangée", str(cr.food_eaten))
        blind_share = cr.blind_ticks / cr.age if cr.age else 0.0
        _row(p, f, c, 132, "Temps aveugle", f"{blind_share:.0%}")
        better = sum(1 for o in world.creatures if (o.age, o.energy) > (cr.age, cr.energy))
        _row(p, f, c, 150, "Rang (âge, énergie)", f"{better + 1}/{len(world.creatures)}")
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

        rows = network_rows(inputs, outputs)
        n_in = len(config.INPUT_LABELS)
        rows_top = c.x(36)
        if self.show_graph:
            graph = pygame.Rect(pad, c.x(32), W - 2 * pad, c.x(GRAPH_H))
            self._draw_graph(p, graph, selected.brain, inputs, hidden, outputs)
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

    def _draw_graph(self, p, rect, brain, x_in, hidden, outputs):
        """The network as a graph: inputs, hidden layer, outputs. Neuron brightness = activation, link colour = sign of
        the signal it carries, link strength = size of that signal. Biases are not drawn."""
        f, c = self.fonts, Ctx(self.u)
        n_in, n_h, n_out = len(x_in), len(hidden), len(outputs)
        label_w = c.x(80)
        xs = (rect.x + label_w, rect.centerx, rect.right - label_w)

        def column(x, n):
            step = rect.h / n
            return [(x, int(rect.y + step * (k + 0.5))) for k in range(n)]

        pin, ph, pout = column(xs[0], n_in), column(xs[1], n_h), column(xs[2], n_out)
        r = max(4, min(c.x(9), int(rect.h / max(n_in, n_h, n_out) / 2.4)))
        wmax = max(float(abs(brain.w1).max()), float(abs(brain.w2).max()), 1e-9)
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
        for label, (x, y) in zip(config.INPUT_LABELS, pin):
            _text(p, f["small"], label, x - r - c.x(6), y - th // 2, LABEL, right=True)
        for label, (x, y) in zip(config.OUTPUT_LABELS, pout):
            _text(p, f["small"], label, x + r + c.x(6), y - th // 2, LABEL)

    # ---------- frame ----------

    def draw(self, sidebar, strip, world, fps, speed, generation, debug_mode, paused, selected, color_label):
        """sidebar: surface of layout.sidebar. strip: surface of layout.strip, or None."""
        sidebar.fill(config.SIDEBAR_BG_COLOR)
        pygame.draw.line(sidebar, (48, 54, 60), (0, 0), (0, sidebar.get_height()))
        panels = {
            "gen": lambda: self._draw_generation(world, fps, speed, generation, debug_mode, paused, color_label),
            "creature": lambda: self._draw_creature(world, selected),
            "net": lambda: self._draw_network(world, selected),
            "chart": lambda: self.chart_side,
        }
        for name, rect in self.slots.items():
            panel = panels[name]()
            if panel is not None:
                sidebar.blit(panel, rect.topleft)
        hy = self.hints_y
        for img in self.hints:
            sidebar.blit(img, (self.slots["gen"].x + 2, hy))
            hy += img.get_height() + 2

        if strip is not None:
            strip.fill(config.SIDEBAR_BG_COLOR)
            pygame.draw.line(strip, (48, 54, 60), (0, 0), (strip.get_width(), 0))
            if self.show_chart and self.chart is not None:
                strip.blit(self.chart, self.strip_slot.topleft)

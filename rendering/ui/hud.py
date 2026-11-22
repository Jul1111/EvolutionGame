"""Side bar (population, selected creature, network, curves) and the strip under the world with the curves."""
import pygame

import config
from rendering import theme
from brain.profiles import PROFILES, input_labels, output_labels
from rendering.backend.glass import frost
from rendering.ui.draw import VALUE, LABEL, MINT, AMBER, CORAL, BLUE, Ctx, create_fonts, _panel, _bar, _signed_bar, \
    _text, _row
from rendering.ui.netview import network_rows, _node, _edge
from rendering.ui.series import SERIES_BY_KEY, DEFAULT_SERIES, build_chart, load_timeline
from rendering.world.scene import energy_color
from utils.timefmt import TICKS_PER_SECOND, format_time

# Natural height (logical pixels at scale 1) of the Population and Créature panels. They are stretched vertically
# (0.85x to 1.9x) to use the room left by the network panel and the curves.
H_CONTENT = 176
H_CHART = 130     # Curves panel in the side bar
GRAPH_H = 120     # Network graph, when shown (natural height)
GRAPH_MIN = 90    # Smallest graph height before the cards are squeezed to make room
CHART_MIN = 100   # Smallest curves panel in the side bar (it disappears if even that does not fit)
KY_MIN = 0.8      # Smallest vertical stretch of the Population and Créature cards
KY_GOOD = 0.92    # Stretch the cards keep as long as the graph or the curves panel can still fit

MAX_PANEL_W = 560    # Logical width cap, for very wide windows


class Hud:
    """Side bar (population, selected creature, network, curves, key hints) and, when the window is tall,
    a strip under the world with the curves. Everything is drawn at the real resolution (see relayout)."""

    def __init__(self, cfg=config):
        self.cfg = cfg   # Settings in force (see config.Settings)
        self.show_chart = True    # Curves (in the strip when there is one, else in the side bar)
        self.show_graph = False   # Network drawn as a graph above the bars
        self.chart_keys = set(DEFAULT_SERIES)   # Curves shown (menu Courbes)
        self.layout = None
        self.profiles = list(self.cfg.ACTIVE_PROFILES)        # Species in the world
        self.timeline_path = None   # timeline.csv of the running simulation (set by app/)
        self.rows = []
        self.visible = True    # Tab hides every panel (clean view of the world)
        self.lineage = None    # LineageTracker of the scene (set by app/)

    # ---------- layout ----------

    def relayout(self, layout):
        """Call whenever the window size changes."""
        self.layout = layout
        self.u = layout.scale
        self.fonts = create_fonts(self.u)
        self.hints = []   # No loose text over the world: the « ? » button and the Aide menu list the shortcuts
        self._compute_slots()

    def _net_height(self):
        """Natural height (logical) of the network panel without the graph."""
        rows_h = 15 * max(len(input_labels(p)) + len(output_labels(p)) for p in self.profiles) + 4
        return 36 + rows_h + 12

    def _fit(self, hints_h, chart):
        """Heights for one choice of hints and curves panel: (space, net_h, graph_h, chart_h), pixels except graph_h
        (logical). The Population and Créature cards keep a comfortable stretch (KY_GOOD); the graph or the curves panel
        take what is left, up to their natural height. If that is too little, the cards shrink down to KY_MIN."""
        layout, u = self.layout, self.u
        m, gap = round(12 * u), round(8 * u)
        space = layout.sidebar.h - 2 * m - hints_h - gap * (3 + chart)
        net_h = self._net_height() * u
        cards_good = 2 * H_CONTENT * u * KY_GOOD
        cards_min = 2 * H_CONTENT * u * KY_MIN
        graph_h = chart_h = 0.0
        if self.show_graph:
            def left(cards):
                return (space - cards - net_h) / u - 12

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
        """Stack the panels in the side bar. The Population and Créature cards stretch vertically (ky) to use the
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
        return build_chart(self.fonts, self.rows, r.w, r.h, self.u, wide, self.chart_keys, self.cfg)

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

    def _draw_population(self, world, fps, speed, info, debug_mode, paused, color_label):
        """Population card. info: births, deaths (since the start), extinct (bool), pop_max, setup.
        Rates come from the last line of timeline.csv; lineages from the display tracker
        (rendering/world/lineage.py)."""
        f, c = self.fonts, Ctx(self.u, self.ky)
        p = self.bg["gen"].copy()
        W, pad = p.get_width(), c.x(14)
        creatures = world.creatures
        n = len(creatures)
        gens = [cr.lineage_gen for cr in creatures]

        _text(p, f["title"], f"Population {n}", pad, c.y(8), VALUE)
        if info.get("setup"):
            status, status_color = "Réglages", AMBER
        elif info.get("extinct"):
            status, status_color = "Extinction", CORAL
        elif paused:
            status, status_color = "Pause", AMBER
        else:
            status, status_color = "En cours", MINT
        img = _text(p, f["small"], status, W - pad, c.y(13), status_color, right=True)
        pygame.draw.circle(p, status_color, (W - pad - img.get_width() - c.x(9), c.y(13) + img.get_height() // 2),
                           max(3, c.x(4)))

        bar_h = max(3, c.x(5))
        cap = info.get("pop_max", self.cfg.POP_CAP)
        _row(p, f, c, 38, "Vivantes / plafond", f"{n}/{cap}")
        _bar(p, pad, c.y(59), W - 2 * pad, bar_h, n / cap if cap else 0, (204, 172, 132))
        _row(p, f, c, 68, "Temps simulé", format_time(world.tick))
        last = self.rows[-1] if self.rows else None
        per_min = 60 * TICKS_PER_SECOND / self.cfg.SAMPLE_TICKS   # Lines of timeline.csv per simulated minute
        if last is not None:
            born = (last.get("births") or 0) * per_min
            dead = ((last.get("deaths_hunger") or 0) + (last.get("deaths_age") or 0)) * per_min
            rates = f"+{born:.0f} / -{dead:.0f}"
        else:
            rates = "-"
        _row(p, f, c, 86, "Naissances / morts par min", rates)
        _row(p, f, c, 104, "Générations moy. / max", f"{sum(gens) / n:.1f} / {max(gens)}" if n else "-")
        lineage = getattr(self, "lineage", None)
        if lineage is not None and n and len(self.profiles) == 1:   # Several species: their counts take this row
            count, share, _ = lineage.summary(world)
            share_txt = f"{share:.0%}" if share >= 0.1 else f"{share * 100:.1f} %"
            _row(p, f, c, 122, "Lignées · la plus grande", f"{count} · {share_txt}")
        if len(self.profiles) > 1:
            # Duel: one curve per species (its colour, common scale) and its number of living creatures
            x = W - pad
            for name in reversed(self.profiles):
                n_alive = sum(1 for cr in creatures if cr.alive and cr.profile == name)
                img = _text(p, f["small"], str(n_alive), x, c.y(124), VALUE, right=True)
                x -= img.get_width() + c.x(5)
                pygame.draw.circle(p, PROFILES[name]["color"], (x - c.x(3), c.y(124) + img.get_height() // 2),
                                   max(3, c.x(4)))
                x -= c.x(14)
            area = pygame.Rect(pad, c.y(138), W - 2 * pad, max(c.x(10), c.y(16)))
            pygame.draw.rect(p, (255, 255, 255, 12), area, border_radius=max(2, c.x(4)))
            recent = self.rows[-80:]
            series = {nm: [r.get(f"pop__{nm}") for r in recent] for nm in self.profiles}
            top = max([v for vs in series.values() for v in vs if v is not None] + [1])
            for nm, vals in series.items():
                pts = [(area.x + area.w * i / max(1, len(vals) - 1), area.bottom - 2 - (area.h - 4) * v / top)
                       for i, v in enumerate(vals) if v is not None]
                if len(pts) > 1:
                    pygame.draw.aalines(p, PROFILES[nm]["color"], False, pts)
        else:
            # Mini curve of the population over the last relevés
            pops = [r.get("population") for r in self.rows[-80:] if r.get("population") is not None]
            area = pygame.Rect(pad, c.y(138), W - 2 * pad, max(c.x(10), c.y(16)))
            pygame.draw.rect(p, (255, 255, 255, 12), area, border_radius=max(2, c.x(4)))
            if len(pops) > 1:
                top = max(pops) or 1
                pts = [(area.x + area.w * i / (len(pops) - 1), area.bottom - 2 - (area.h - 4) * v / top)
                       for i, v in enumerate(pops)]
                pygame.draw.aalines(p, (204, 172, 132), False, pts)

        debug_label = ("off", "sélection", "toutes")[debug_mode]
        _text(p, f["small"], f"couleur : {color_label}  ·  debug : {debug_label}", pad, c.y(158), LABEL)
        renderer = getattr(self, 'renderer', 'CPU')
        _text(p, f["small"], f"{fps:.0f} FPS · {renderer}", W - pad, c.y(158), LABEL, right=True)
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
        dot = (pad + img_title.get_width() + c.x(12), c.y(8) + img_title.get_height() // 2)
        pygame.draw.circle(p, PROFILES[selected.profile]["color"], dot, max(3, c.x(4)))
        _text(p, f["small"], PROFILES[selected.profile]["title"], pad + img_title.get_width() + c.x(20), c.y(13), LABEL)
        state, state_color = ("Vivante", MINT) if cr.alive else ("Morte", CORAL)
        img = _text(p, f["small"], state, W - pad, c.y(13), state_color, right=True)
        pygame.draw.circle(p, state_color, (W - pad - img.get_width() - c.x(9), c.y(13) + img.get_height() // 2),
                           max(3, c.x(4)))

        bar_h = max(3, c.x(5))
        energy_ratio = cr.energy / cr.energy_max
        _row(p, f, c, 36, "Énergie", f"{max(cr.energy, 0):.1f}")
        _bar(p, pad, c.y(57), W - 2 * pad, bar_h, energy_ratio, energy_color(max(0.0, min(energy_ratio, 1.0))))
        _row(p, f, c, 66, "Vitesse", f"{cr.speed:.2f}")
        _bar(p, pad, c.y(87), W - 2 * pad, bar_h, cr.speed / self.cfg.CREATURE_MAX_SPEED, BLUE)
        _row(p, f, c, 96, "Âge", format_time(cr.age))
        _row(p, f, c, 114, "Nourriture / poison", f"{cr.food_eaten} / {cr.poison_hits}")
        blind_share = cr.blind_ticks / cr.age if cr.age else 0.0
        _row(p, f, c, 132, "Temps aveugle", f"{blind_share:.0%}")
        _row(p, f, c, 150, "Taille / génération / petits", f"{cr.size:.2f} / {cr.lineage_gen} / {cr.children}")
        return p

    def _draw_network(self, world, selected):
        f, c = self.fonts, Ctx(self.u)   # No vertical stretch: the graph takes the room instead
        p = self.bg["net"].copy()
        W, pad = p.get_width(), c.x(14)
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
        if not self.visible:
            return   # Tab: panels hidden, the whole world is visible
        radius = max(4, round(12 * self.u))
        for rect in self.slots.values():
            frost(sidebar, rect, radius)   # The panels float over the world in frosted glass
        panels = {
            "gen": lambda: self._draw_population(world, fps, speed, info, debug_mode, paused, color_label),
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
            strip.fill(theme.SIDEBAR_BG_COLOR)
            pygame.draw.line(strip, (48, 54, 60), (0, 0), (strip.get_width(), 0))
            if self.show_chart and self.chart is not None:
                strip.blit(self.chart, self.strip_slot.topleft)

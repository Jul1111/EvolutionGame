"""Interface layer drawn on top of the world: tool bar, pause banner, legend, help, hover tips, settings panel and the
large network view. Everything is drawn at the real resolution (sizes multiplied by the scale u), like the rest of the UI.
This module never touches the simulation: it only reads the world and returns action names, app.py runs them."""
import time

import pygame

from rendering.backend.glass import frost
from rendering.ui.charts import ChartView
from rendering.ui.draw import VALUE, LABEL, MINT, AMBER, create_fonts
from rendering.ui.minimap import MiniMap
from rendering.ui.overlay.help import HelpMixin
from rendering.ui.overlay.legend import LegendMixin
from rendering.ui.overlay.network import NetworkMixin
from rendering.ui.overlay.params import ParamsMixin
from rendering.ui.overlay.texts import TOOLBAR
from rendering.ui.overlay.tips import TipsMixin
from rendering.ui.overlay.widgets import PANEL, BORDER, HOVER, DIM, ACTIVE_BG, _icon


class Overlay(LegendMixin, HelpMixin, ParamsMixin, NetworkMixin, TipsMixin):
    def __init__(self, hud, scene):
        self.hud, self.scene = hud, scene
        self.layout = None
        self.help_open = False
        self.legend_open = False
        self.params_open = False
        self.net_big = False
        self.toast_text, self.toast_until = None, 0.0   # Short message at the bottom of the world (toast())
        self.setup = None   # Settings screen before a simulation (app.py): {"resume": bool, "cancel": bool} or None
        self.mouse = None
        self.mouse_since = 0.0
        self.state = {}
        self._hits = []           # (rect, action) of the settings panel, rebuilt at each draw
        self._rects = {}          # name → rect of the panels drawn last (for clicks)
        self._cache = {}
        self.start = None             # rendering.startmenu.StartMenu at launch (set by app.py)
        self.chart_big = False        # Large curves view (key G, third press)
        self.charts = ChartView(hud)
        self.minimap = MiniMap()      # Key M
        self.presets = None           # utils.presets.PresetBrowser (set by app.py)
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

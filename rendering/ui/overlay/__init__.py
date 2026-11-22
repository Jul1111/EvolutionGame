"""Interface layer drawn on top of the world: tool bar, pause banner, legend, help, hover tips, settings panel and the
large network view. Everything is drawn at the real resolution (sizes multiplied by the scale u), like the rest of
the UI.
This module never touches the simulation: it only reads the world and returns action names, app/ runs them.

Overlay is the assembly: each panel (toolbar, legend, help, network, params, tips) is its own object with its own state
and receives what it needs; Overlay routes the mouse to them and draws them in order."""
import time

import pygame

from rendering.backend.glass import frost
from rendering.ui.charts import ChartView
from rendering.ui.draw import VALUE, LABEL, AMBER
from rendering.ui.minimap import MiniMap
from rendering.ui.overlay.context import UiContext
from rendering.ui.overlay.help import Help
from rendering.ui.overlay.legend import Legend
from rendering.ui.overlay.network import NetworkPanel
from rendering.ui.overlay.params import ParamsPanel
from rendering.ui.overlay.tips import Tips
from rendering.ui.overlay.toolbar import Toolbar
from rendering.ui.overlay.widgets import PANEL


class Overlay:
    def __init__(self, hud, scene):
        self.hud, self.scene = hud, scene
        self.ctx = UiContext(hud)
        self.minimap = MiniMap(hud.cfg)   # Key M
        self.charts = ChartView(hud)
        self.chart_big = False        # Large curves view (key G, third press)
        self.toolbar = Toolbar(self.ctx)
        self.legend = Legend(self.ctx, scene, self.minimap)
        self.help = Help(self.ctx)
        self.net = NetworkPanel(self.ctx)
        self.params = ParamsPanel(self.ctx, hud.cfg)
        self.tips = Tips(self.ctx, hud, scene, self.toolbar, self.blocks, self._modal_open)
        self.start = None             # rendering.startmenu.StartMenu at launch (set by app/)
        self.toast_text, self.toast_until = None, 0.0   # Short message at the bottom of the world (toast())
        self.banner = None            # Pre-rendered pause banner

    # ---------- state ----------

    def _modal_open(self):
        return self.help.open or self.params.open or self.start is not None

    def any_modal(self):
        return self._modal_open()

    def close_modals(self):
        self.help.open = self.params.open = False

    def _on_hud(self, x, y):
        hud = self.hud
        if not hud.visible or hud.layout is None:
            return False
        sb = hud.layout.sidebar
        return any(r.move(sb.x, sb.y).collidepoint(x, y) for r in hud.slots.values())

    def blocks(self, x, y):
        """True on a card or a panel: the world under it must neither zoom nor select."""
        if self.any_modal() or self.toolbar.bar_rect.collidepoint(x, y) or self._on_hud(x, y):
            return True
        if self.minimap.enabled and self.minimap.rect and self.minimap.rect.collidepoint(x, y):
            return True
        if self.chart_big and self.charts.rect and self.charts.rect.collidepoint(x, y):
            return True
        return any(r is not None and r.collidepoint(x, y) for r in (self.legend.rect, self.net.rect))

    def relayout(self, layout):
        ctx = self.ctx
        ctx.relayout(layout)
        u, f = ctx.u, ctx.fonts
        self.legend.relayout()
        self.help.relayout()
        self.toolbar.relayout()
        # Pause banner, pre-rendered
        title = f["title"].render("PAUSE", True, AMBER)
        hint = f["small"].render("Espace : reprendre    →  : avancer d'un tick", True, LABEL)
        bw = max(title.get_width(), hint.get_width()) + round(36 * u)
        bh = title.get_height() + hint.get_height() + round(18 * u)
        banner = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(banner, (*PANEL, 90), banner.get_rect(), border_radius=round(10 * u))
        pygame.draw.rect(banner, (240, 196, 92, 110), banner.get_rect(), width=1, border_radius=round(10 * u))
        banner.blit(title, ((bw - title.get_width()) // 2, round(7 * u)))
        banner.blit(hint, ((bw - hint.get_width()) // 2, round(10 * u) + title.get_height()))
        self.banner = banner

    # ---------- mouse ----------

    def hover(self, x, y):
        self.net.hover(x, y)
        self.ctx.move_mouse(x, y)

    def click(self, x, y):
        """Left click. Returns (consumed, action). The settings panel and the help are modal; the legend and the
        large network only take the clicks that land on them, so another creature can still be picked."""
        if self.start is not None and not self.params.open:
            return True, self.start.click(x, y)   # Start menu: it takes every click
        if self.help.open:
            self.help.open = False
            return True, None
        if self.params.open:
            return True, self.params.click(x, y)
        consumed, action = self.toolbar.click(x, y)
        if consumed:
            return True, action
        if self.chart_big and self.charts.click(x, y):
            return True, None
        if self.minimap.enabled and self.minimap.rect and self.minimap.rect.collidepoint(x, y):
            self.scene.center_on(*self.minimap.to_world(x, y))
            return True, "cam_follow_off"
        if self.net.grab(x, y) or self._on_hud(x, y):
            return True, None
        if self.legend.contains(x, y) or self.net.contains(x, y):
            return True, None
        return False, None

    # ---------- drawing ----------

    def toast(self, text, seconds=4.0):
        """Shows `text` at the bottom of the world for a few seconds (saves, extinction...)."""
        self.toast_text, self.toast_until = text, time.monotonic() + seconds

    def draw(self, window, state, world, selected, params):
        """state: paused, speed, debug (0-2), color, follow, graph (0-2). params: rows of the settings panel."""
        ctx = self.ctx
        u, f, w = ctx.u, ctx.fonts, ctx.area
        for panel in (self.legend, self.help, self.net, self.params):
            panel.rect = None   # Set again by the panels drawn this frame: a hidden panel takes no click

        active = {"pause": state["paused"], "debug": state["debug"] > 0, "legend": self.legend.open,
                  "follow": state["follow"], "graph": state["graph"] > 0, "params_panel": self.params.open,
                  "help": self.help.open, "chart": state.get("chart", 0) > 0,
                  "cam_follow": state.get("cam_follow", False)}
        self.toolbar.draw(window, state, active, self.any_modal())

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
            top = self.toolbar.bar_rect.bottom + m
            self.charts.draw(window, pygame.Rect(w.x + m, top, w.w - 2 * m, w.bottom - top - m), f, u, ctx.mouse)
        if self.legend.open:
            self.legend.draw(window)
        if self.net.big:
            self.net.draw(window, world, selected)
        if self.params.open:
            self.params.draw(window, params, state)
        if self.help.open:
            self.help.draw(window)
        if self.start is not None and not self.params.open:
            self.start.draw(window, ctx.layout, f, u, ctx.mouse)

    def draw_tips(self, window, world, selected, menu_open, state):
        """Hover tips, drawn last. `state`: the same as for draw()."""
        self.tips.draw(window, world, selected, menu_open, state)

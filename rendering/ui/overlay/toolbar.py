"""The tool bar at the top of the world, and its speed label."""
import pygame

from rendering.backend.glass import frost
from rendering.ui.draw import VALUE, MINT, AMBER
from rendering.ui.overlay.texts import TOOLBAR
from rendering.ui.overlay.widgets import PANEL, BORDER, HOVER, DIM, ACTIVE_BG, _icon


class Toolbar:
    def __init__(self, ctx):
        self.ctx = ctx
        self.buttons = []         # (rect, action, icon, title, shortcut)
        self.seps = []
        self.speed_rect = None
        self.bar_rect = None
        self.bar_bg = None

    def relayout(self):
        ctx = self.ctx
        u, w = ctx.u, ctx.area
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

    def click(self, x, y):
        """Returns (consumed, action) for a click on a button or on the bar."""
        for rect, action, *_ in self.buttons:
            if rect.collidepoint(x, y):
                return True, action
        return self.bar_rect.collidepoint(x, y), None

    def draw(self, window, state, active, modal):
        """`active`: actions whose button is lit. `modal`: a panel is open (no hover highlight)."""
        ctx = self.ctx
        u, f, mouse = ctx.u, ctx.fonts, ctx.mouse
        frost(window, self.bar_rect, round(10 * u))
        window.blit(self.bar_bg, self.bar_rect.topleft)
        for rect, action, icon, _, _ in self.buttons:
            on = active.get(action, False)
            hov = mouse is not None and rect.collidepoint(mouse) and not modal
            if on or hov:
                pygame.draw.rect(window, ACTIVE_BG if on else HOVER, rect, border_radius=max(3, round(6 * u)))
            enabled = action != "step" or state["paused"]
            name = "play" if (action == "pause" and state["paused"]) else icon
            _icon(window, name, rect, (MINT if on else (VALUE if enabled else DIM)), f, u)
        for sx in self.seps:
            pygame.draw.line(window, BORDER, (sx, self.bar_rect.y + round(8 * u)),
                             (sx, self.bar_rect.bottom - round(8 * u)))
        limited = state.get("real_speed", 0) and state["real_speed"] < state["speed"] * 0.95 and not state["paused"]
        sp = f["base"].render(f"x{state['real_speed']:.0f}" if limited else f"x{state['speed']}", True,
                              AMBER if limited else VALUE)   # Amber: the machine cannot keep the asked speed
        window.blit(sp, (self.speed_rect.centerx - sp.get_width() // 2, self.speed_rect.centery - sp.get_height() // 2))

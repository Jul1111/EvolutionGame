"""What every overlay panel needs to place itself: scale, fonts, free area of the world, mouse position."""
import time

from rendering.ui.draw import create_fonts
import pygame


class UiContext:
    def __init__(self, hud):
        self.hud = hud
        self.layout = None
        self.u = 1.0               # Scale of the UI (sizes are multiplied by it)
        self.fonts = None
        self.veil = None           # Dark veil drawn behind the modal panels
        self.mouse = None          # Last mouse position, in surface pixels
        self.mouse_since = 0.0     # When the mouse last moved (hover tips wait for it to rest)

    @property
    def area(self):
        """Free part of the world: not under the menu bar nor under the panels (when shown)."""
        return self.layout.free_area(self.hud.visible)

    def relayout(self, layout):
        self.layout = layout
        self.u = layout.scale
        self.fonts = create_fonts(self.u)
        veil = pygame.Surface(layout.window_size, pygame.SRCALPHA)
        veil.fill((6, 8, 12, 150))
        self.veil = veil

    def move_mouse(self, x, y):
        if self.mouse is None or abs(x - self.mouse[0]) + abs(y - self.mouse[1]) > 2:
            self.mouse_since = time.monotonic()
        self.mouse = (x, y)

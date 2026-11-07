import pygame

import config

LOGICAL = (config.WINDOW_WIDTH, config.SCREEN_HEIGHT)   # Size at scale 1, used only to pick the first window size


def fit_window_size(width_ratio=0.95, height_ratio=0.85):
    """Largest window with the base proportions (never bigger than scale 1) that fits on the desktop.
    Sizes are in screen points. The ratios leave room for the title bar, the dock or the task bar."""
    desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
    scale = min(1.0, desktop_w * width_ratio / LOGICAL[0], desktop_h * height_ratio / LOGICAL[1])
    return max(640, int(LOGICAL[0] * scale)), max(288, int(LOGICAL[1] * scale))


class Display:
    """The window: resizable, or fullscreen at the desktop resolution.

    With pygame-ce the window is created in high-DPI mode: on a Retina screen the drawing surface has the real
    pixels (2x the window size in points), so everything is sharp. With plain pygame (2.6) that mode does not
    exist and macOS doubles the image, which looks blurry: the game still runs, just less sharp.

    Drawing happens directly at the surface's resolution (see rendering/layout.py), never rescaled."""

    def __init__(self, title):
        self.windowed_size = fit_window_size()
        self.fullscreen = False
        self.generation = 0                      # +1 whenever the surface may have been replaced
        self.hidpi = hasattr(pygame, "Window")   # pygame-ce
        if self.hidpi:
            self.window = pygame.Window(title, self.windowed_size, resizable=True, allow_high_dpi=True)
        else:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            pygame.display.set_caption(title)

    def surface(self):
        """The surface to draw on (in real pixels). Ask again every frame: it follows the window size."""
        return self.window.get_surface() if self.hidpi else pygame.display.get_surface()

    def flip(self):
        if self.hidpi:
            self.window.flip()
        else:
            pygame.display.flip()

    def pixel_ratio(self):
        """Surface pixels per window point: 2.0 on a Retina screen in high-DPI mode, else 1.0."""
        if not self.hidpi:
            return 1.0
        return self.surface().get_width() / self.window.size[0]

    def to_pixels(self, pos):
        """Mouse position (window points) → position on the surface (pixels)."""
        ratio = self.pixel_ratio()
        return pos[0] * ratio, pos[1] * ratio

    def toggle_fullscreen(self):
        if self.hidpi:
            if self.fullscreen:
                self.window.set_windowed()
            else:
                self.window.set_fullscreen(desktop=True)
        elif self.fullscreen:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        else:
            self.windowed_size = pygame.display.get_surface().get_size()
            pygame.display.set_mode(pygame.display.get_desktop_sizes()[0], pygame.FULLSCREEN)
        self.fullscreen = not self.fullscreen
        self.generation += 1

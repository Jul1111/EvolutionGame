import pygame

import config

LOGICAL = (config.WINDOW_WIDTH, config.SCREEN_HEIGHT)   # Size at scale 1, used only to pick the first window size


def fit_window_size(width_ratio=0.95, height_ratio=0.85):
    """Largest window with the base proportions (never bigger than scale 1) that fits on the desktop.
    The ratios leave room for the title bar, the dock or the task bar."""
    desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
    scale = min(1.0, desktop_w * width_ratio / LOGICAL[0], desktop_h * height_ratio / LOGICAL[1])
    return max(640, int(LOGICAL[0] * scale)), max(288, int(LOGICAL[1] * scale))


class Display:
    """The window: resizable, or fullscreen at the desktop resolution. Drawing happens directly at the
    window's resolution (see rendering/layout.py), so there is no rescaling and nothing gets blurry."""

    def __init__(self):
        self.windowed_size = fit_window_size()
        self.fullscreen = False
        pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def toggle_fullscreen(self):
        if self.fullscreen:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        else:
            self.windowed_size = pygame.display.get_surface().get_size()
            pygame.display.set_mode(pygame.display.get_desktop_sizes()[0], pygame.FULLSCREEN)
        self.fullscreen = not self.fullscreen

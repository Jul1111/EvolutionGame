import pygame

import config

BASE_W, BASE_H = config.WINDOW_WIDTH, config.SCREEN_HEIGHT   # World + side bar at scale 1 (1600 x 720)
STRIP_MIN = 170   # Logical height of the bottom strip (curves) when the window is taller than the base ratio


class Layout:
    """Where everything goes in the window, in real pixels. The three areas tile the window exactly,
    so nothing is left empty: no black bars."""

    def __init__(self, scale, window_size, world, sidebar, strip):
        self.scale = scale              # Pixels per world unit, also the size factor of the interface
        self.window_size = window_size
        self.world = world              # Rect: the simulated world
        self.sidebar = sidebar          # Rect: panels on the right
        self.strip = strip              # Rect or None: curves under the world


def compute_layout(width, height):
    """Adaptive layout, same drawing at any window size:
    - window wider than the base ratio (or equal): the world fills the height, the side bar takes the width left;
    - window taller: the world is scaled to the width, the curves go in a strip under it (when the side bar
      alone cannot absorb the height)."""
    width, height = max(width, 320), max(height, 180)
    if width / height >= BASE_W / BASE_H:
        scale = height / config.SCREEN_HEIGHT
        world_w = round(config.SCREEN_WIDTH * scale)
        return Layout(scale, (width, height),
                      pygame.Rect(0, 0, world_w, height),
                      pygame.Rect(world_w, 0, width - world_w, height),
                      None)
    scale = min(width / BASE_W, height / (config.SCREEN_HEIGHT + STRIP_MIN))
    world_w = round(config.SCREEN_WIDTH * scale)
    world_h = round(config.SCREEN_HEIGHT * scale)
    return Layout(scale, (width, height),
                  pygame.Rect(0, 0, world_w, world_h),
                  pygame.Rect(world_w, 0, width - world_w, height),
                  pygame.Rect(0, world_h, world_w, height - world_h))

import pygame

import config

MENU_H = 32       # Logical height of the menu bar at the top
BASE_W, BASE_H = config.WINDOW_WIDTH, config.SCREEN_HEIGHT + MENU_H   # Menu + world + side bar at scale 1 (1600 x 752)
STRIP_MIN = 170   # Logical height of the bottom strip (curves) when the window is taller than the base ratio


class Layout:
    """Where everything goes in the window, in real pixels. The four areas tile the window exactly,
    so nothing is left empty: no black bars."""

    def __init__(self, scale, window_size, menu, world, sidebar, strip):
        self.scale = scale              # Pixels per world unit, also the size factor of the interface
        self.window_size = window_size
        self.menu = menu                # Rect: menu bar across the top of the window
        self.world = world              # Rect: the simulated world
        self.sidebar = sidebar          # Rect: panels on the right
        self.strip = strip              # Rect or None: curves under the world


def compute_layout(width, height):
    """Adaptive layout, same drawing at any window size. The menu bar spans the top of the window, then:
    - window wider than the base ratio (or equal): the world fills the height left, the side bar takes the width left;
    - window taller: the world is scaled to the width, the curves go in a strip under it (when the side bar
      alone cannot absorb the height)."""
    width, height = max(width, 320), max(height, 180)
    if width / height >= BASE_W / BASE_H:
        scale = height / BASE_H
        menu_h = round(MENU_H * scale)
        world_w = round(config.SCREEN_WIDTH * scale)
        return Layout(scale, (width, height),
                      pygame.Rect(0, 0, width, menu_h),
                      pygame.Rect(0, menu_h, world_w, height - menu_h),
                      pygame.Rect(world_w, menu_h, width - world_w, height - menu_h),
                      None)
    scale = min(width / BASE_W, height / (BASE_H + STRIP_MIN))
    menu_h = round(MENU_H * scale)
    world_w = round(config.SCREEN_WIDTH * scale)
    world_h = round(config.SCREEN_HEIGHT * scale)
    return Layout(scale, (width, height),
                  pygame.Rect(0, 0, width, menu_h),
                  pygame.Rect(0, menu_h, world_w, world_h),
                  pygame.Rect(world_w, menu_h, width - world_w, height - menu_h),
                  pygame.Rect(0, menu_h + world_h, world_w, height - menu_h - world_h))

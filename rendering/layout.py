import pygame

import config

MENU_H = 32       # Logical height of the menu bar at the top
SIDE_W = 320      # Logical width of the column of floating panels on the right
BASE_W, BASE_H = config.WINDOW_WIDTH, config.SCREEN_HEIGHT + MENU_H   # Reference size at scale 1 (1600 x 752)


class Layout:
    """Where everything goes in the window, in real pixels. The world fills the whole window; the menu bar and the
    column of panels float over it, in frosted glass."""

    def __init__(self, scale, window_size, menu, world, sidebar, strip):
        self.scale = scale              # Size factor of the interface (pixels per logical unit)
        self.window_size = window_size
        self.menu = menu                # Rect: menu bar across the top of the window (over the world)
        self.world = world              # Rect: the simulated world = the whole window
        self.sidebar = sidebar          # Rect: column of floating panels on the right (over the world)
        self.strip = strip              # Always None now: the curves live in the side panel or the large view

    def free_area(self, panels_visible=True):
        """Part of the world not covered by the menu bar nor by the panels: where the other cards go."""
        right = self.sidebar.x if panels_visible else self.window_size[0]
        return pygame.Rect(0, self.menu.bottom, right, self.window_size[1] - self.menu.bottom)


def compute_layout(width, height):
    """Same drawing at any window size: one interface scale from the reference size, the world under everything."""
    width, height = max(width, 320), max(height, 180)
    scale = min(width / BASE_W, height / BASE_H)
    menu_h = round(MENU_H * scale)
    side_w = min(round(SIDE_W * scale), width // 2)
    return Layout(scale, (width, height),
                  pygame.Rect(0, 0, width, menu_h),
                  pygame.Rect(0, 0, width, height),
                  pygame.Rect(width - side_w, menu_h, side_w, height - menu_h),
                  None)

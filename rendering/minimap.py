"""Mini-map: the whole world in a small glass card, with the creatures, the anemones and the part of the world on
screen (light frame, cut in pieces when it crosses an edge of the torus). A click moves the view there."""
import pygame

import config
from rendering.glass import frost

DOT = (226, 232, 240)
ANEMONE = (96, 112, 190)
FRAME = (240, 196, 92)


class MiniMap:
    def __init__(self):
        self.enabled = True
        self.rect = None

    def place(self, area, u):
        """Bottom-left corner of the free area. Width 210 (logical), height from the world's proportions."""
        w = round(210 * u)
        h = max(round(60 * u), round(w * config.WORLD_HEIGHT / config.WORLD_WIDTH))
        m = round(12 * u)
        self.rect = pygame.Rect(area.x + m, area.bottom - m - h, w, h)
        return self.rect

    def to_world(self, x, y):
        r = self.rect
        return ((x - r.x) / r.w * config.WORLD_WIDTH, (y - r.y) / r.h * config.WORLD_HEIGHT)

    def draw(self, window, world, scene, u):
        r = self.rect
        frost(window, r, max(4, round(8 * u)), alpha=165)
        kx, ky = r.w / config.WORLD_WIDTH, r.h / config.WORLD_HEIGHT
        clip = window.get_clip()
        window.set_clip(r.inflate(-2, -2))
        for o in world.obstacles:
            pygame.draw.circle(window, ANEMONE, (r.x + o.x * kx, r.y + o.y * ky), max(1.5, o.radius * kx))
        dot = max(1, round(1.2 * u))
        for c in world.creatures:
            if c.alive:
                pygame.draw.circle(window, DOT, (r.x + c.x * kx, r.y + c.y * ky), dot)
        # Part of the world on screen: one frame, cut at the edges of the map (the torus repetition is not shown)
        if scene.size is not None and scene.scale:
            vw, vh = scene.size[0] / scene.scale, scene.size[1] / scene.scale
            if vw < config.WORLD_WIDTH or vh < config.WORLD_HEIGHT:
                frame = pygame.Rect(round(r.x + (scene.cam_x - vw / 2) * kx), round(r.y + (scene.cam_y - vh / 2) * ky),
                                    max(4, round(vw * kx)), max(4, round(vh * ky))).clip(r)
                if frame.w > 1 and frame.h > 1:
                    pygame.draw.rect(window, FRAME, frame, max(1, round(1.2 * u)))
        window.set_clip(clip)

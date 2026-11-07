import math

import numpy as np
import pygame

import config
from core.physics import torus_delta

ENERGY_BUCKETS = 16   # Number of pre-rendered creature sprites (one per energy level)
FOOD_FRAMES = 12      # Number of pre-rendered food pulsation frames
SUPERSAMPLE = 4       # Sprites are drawn 4x bigger then shrunk, for smooth edges

# Soft light patches on the background: (x, y, radius in px, RGB boost). Fixed on purpose:
# no random number is drawn here, so the simulation's single seeded generator is untouched.
BLOBS = [
    (260, 170, 220, (10, 18, 14)),
    (980, 210, 260, (8, 14, 20)),
    (640, 560, 300, (14, 16, 10)),
    (160, 620, 200, (8, 16, 18)),
    (1120, 640, 220, (12, 12, 20)),
]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def energy_color(t):
    """Colour for an energy ratio t in [0, 1]: coral → amber → mint."""
    if t < 0.5:
        return _lerp(config.ENERGY_LOW_COLOR, config.ENERGY_MID_COLOR, t * 2.0)
    return _lerp(config.ENERGY_MID_COLOR, config.ENERGY_HIGH_COLOR, (t - 0.5) * 2.0)


def _shrink(big, size):
    return pygame.transform.smoothscale(big, (size, size)).convert_alpha()


class Scene:
    """Draws the world (background, food, creatures, debug overlay). Read-only on the simulation."""

    def __init__(self):
        self.background = self._build_background()
        self.bucket_colors = [energy_color(i / (ENERGY_BUCKETS - 1)) for i in range(ENERGY_BUCKETS)]
        self.body_sprites = [self._build_body(c) for c in self.bucket_colors]
        self.dead_sprite = self._build_dead()
        self.food_sprites = [self._build_food(f) for f in range(FOOD_FRAMES)]

    # ---------- sprite construction (done once) ----------

    def _build_background(self):
        w, h = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        xs = np.arange(w, dtype=np.float32)[:, None]
        ys = np.arange(h, dtype=np.float32)[None, :]
        # Radial vignette: bright centre, dark edges
        r = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 * 0.8 + ((ys - h / 2) / (h / 2)) ** 2)
        t = np.clip(r / 1.15, 0.0, 1.0) ** 1.7
        center = np.array(config.BG_CENTER_COLOR, dtype=np.float32)
        edge = np.array(config.BG_EDGE_COLOR, dtype=np.float32)
        img = center * (1.0 - t[..., None]) + edge * t[..., None]
        for bx, by, br, boost in BLOBS:
            g = np.exp(-(((xs - bx) ** 2 + (ys - by) ** 2) / (2.0 * (br / 2.0) ** 2)))
            img += g[..., None] * np.array(boost, dtype=np.float32)
        img = np.clip(img, 0, 255).astype(np.uint8)
        return pygame.surfarray.make_surface(img).convert()

    def _build_body(self, color):
        r = config.CREATURE_RADIUS
        size = 2 * (r + 3)
        s = SUPERSAMPLE
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        c = size * s // 2
        dark = _lerp(color, (10, 12, 16), 0.55)
        light = _lerp(color, (255, 255, 255), 0.45)
        pygame.draw.circle(big, (*color, 55), (c, c), (r + 2.5) * s)          # soft halo
        pygame.draw.circle(big, (*color, 225), (c, c), r * s)                 # body
        pygame.draw.circle(big, (*light, 255), (c, c), r * s, int(1.3 * s))   # membrane
        pygame.draw.circle(big, (*dark, 255), (c, c), r * 0.42 * s)           # nucleus
        return _shrink(big, size)

    def _build_dead(self):
        r = config.CREATURE_RADIUS
        size = 2 * (r + 3)
        s = SUPERSAMPLE
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        c = size * s // 2
        pygame.draw.circle(big, (*config.DEAD_COLOR, 70), (c, c), r * s)
        pygame.draw.circle(big, (*config.DEAD_COLOR, 110), (c, c), r * s, int(1.0 * s))
        return _shrink(big, size)

    def _build_food(self, frame):
        r = config.FOOD_RADIUS
        halo = r * 4
        size = 2 * halo + 2
        s = SUPERSAMPLE
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        c = size * s // 2
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.cos(2 * math.pi * frame / FOOD_FRAMES))
        steps = 10
        for k in range(steps):  # concentric discs, alpha growing towards the centre
            radius = halo * s * (1.0 - k / steps)
            alpha = int(70 * pulse * ((k + 1) / steps) ** 1.5)
            pygame.draw.circle(big, (*config.FOOD_COLOR, alpha), (c, c), radius)
        core = _lerp(config.FOOD_COLOR, (255, 255, 255), 0.35)
        pygame.draw.circle(big, (*config.FOOD_COLOR, 255), (c, c), r * s)
        pygame.draw.circle(big, (*core, 255), (c - r * 0.25 * s, c - r * 0.25 * s), r * 0.5 * s)
        return _shrink(big, size)

    # ---------- drawing (every frame) ----------

    @staticmethod
    def _blit_wrapped(screen, sprite, x, y, world_w, world_h):
        """Blit a sprite centred on (x, y), and its ghost on the other side if it crosses a torus edge."""
        sw, sh = sprite.get_size()
        hw, hh = sw / 2, sh / 2
        xs = [x]
        if x < hw:
            xs.append(x + world_w)
        elif x > world_w - hw:
            xs.append(x - world_w)
        ys = [y]
        if y < hh:
            ys.append(y + world_h)
        elif y > world_h - hh:
            ys.append(y - world_h)
        for px in xs:
            for py in ys:
                screen.blit(sprite, (px - hw, py - hh))

    def draw(self, screen, world, debug_mode):
        """debug_mode: 0 = off, 1 = oldest living creature only, 2 = all living creatures."""
        screen.blit(self.background, (0, 0))
        ww, wh = world.width, world.height

        now = pygame.time.get_ticks()  # real time: pulsation does not accelerate with the sim speed
        for i, food in enumerate(world.foods):
            frame = int(now / 90 + i * 3) % FOOD_FRAMES
            self._blit_wrapped(screen, self.food_sprites[frame], food.x, food.y, ww, wh)

        for c in world.creatures:
            if not c.alive:
                self._blit_wrapped(screen, self.dead_sprite, c.x, c.y, ww, wh)

        r = config.CREATURE_RADIUS
        for c in world.creatures:
            if not c.alive:
                continue
            ratio = max(0.0, min(c.energy / config.ENERGY_INPUT_MAX, 1.0))
            bucket = int(ratio * (ENERGY_BUCKETS - 1) + 0.5)
            color = self.bucket_colors[bucket]
            cos_a, sin_a = math.cos(c.angle), math.sin(c.angle)

            # Tail behind the creature: longer when it moves faster
            if c.speed > 0.3:
                length = c.speed * 3.0
                p0 = (c.x - cos_a * r, c.y - sin_a * r)
                p1 = (c.x - cos_a * (r + length), c.y - sin_a * (r + length))
                pygame.draw.aaline(screen, _lerp(color, (10, 12, 16), 0.35), p0, p1)

            self._blit_wrapped(screen, self.body_sprites[bucket], c.x, c.y, ww, wh)

            # Heading marker: small light dot towards the front
            nub = (int(c.x + cos_a * r * 0.62), int(c.y + sin_a * r * 0.62))
            pygame.draw.circle(screen, _lerp(color, (255, 255, 255), 0.75), nub, 2)

        if debug_mode:
            self._draw_debug(screen, world, debug_mode)

    def _draw_debug(self, screen, world, mode):
        alive = [c for c in world.creatures if c.alive]
        if not alive:
            return
        targets = alive if mode == 2 else [max(alive, key=lambda c: (c.age, c.energy))]
        vision2 = config.VISION_RANGE ** 2
        for c in targets:
            center = (int(c.x), int(c.y))
            vision_color = config.DEBUG_VISION_COLOR if mode == 1 else _lerp(config.DEBUG_VISION_COLOR, (0, 0, 0), 0.6)
            pygame.draw.circle(screen, vision_color, center, config.VISION_RANGE, 1)
            # Same rule as World.sense: nearest food within the vision range
            best = None
            best_d2 = vision2
            for food in world.foods:
                dx = torus_delta(c.x, food.x, world.width)
                dy = torus_delta(c.y, food.y, world.height)
                d2 = dx * dx + dy * dy
                if d2 <= best_d2:
                    best_d2 = d2
                    best = (dx, dy)
            if best is not None:
                pygame.draw.aaline(screen, config.DEBUG_LINK_COLOR, (c.x, c.y), (c.x + best[0], c.y + best[1]))
            if mode == 1:
                pygame.draw.circle(screen, (255, 255, 255), center, config.CREATURE_RADIUS + 5, 1)

import math

import numpy as np
import pygame

import config
from core.physics import torus_delta
from rendering.obstacles import obstacle_sprite

ENERGY_BUCKETS = 16   # Number of pre-rendered creature sprites (one per energy level)
FOOD_FRAMES = 12      # Number of pre-rendered food pulsation frames
COLOR_MODES = ("énergie", "vitesse", "nourriture")  # What the creature colour encodes (key C)
TRAIL_COLOR = (255, 226, 140)
TRAIL_FADE = (24, 30, 34)
SUPERSAMPLE = 4       # Sprites are drawn 4x bigger then shrunk, for smooth edges

# Soft light patches on the background: (x, y, radius, RGB boost), in world units. Fixed on purpose:
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


def pick_creature(world, x, y, radius=14.0):
    """Creature under the point (x, y) in world units, torus-aware. Living ones win over dead ones."""
    best = None
    best_key = None
    for c in world.creatures:
        dx = torus_delta(x, c.x, world.width)
        dy = torus_delta(y, c.y, world.height)
        d2 = dx * dx + dy * dy
        if d2 <= radius * radius:
            key = (0 if c.alive else 1, d2)
            if best_key is None or key < best_key:
                best, best_key = c, key
    return best


class Scene:
    """Draws the world (background, food, creatures, debug overlay) at the window's real resolution.
    Read-only on the simulation. Call resize() whenever the layout changes."""

    def __init__(self):
        self.scale = None          # Pixels per world unit used for positions (exact)
        self.sprite_scale = None   # Scale the sprites were built for (rebuilt only on a >1% change)
        self.size = None
        self.color_mode = 0
        self.bucket_colors = [energy_color(i / (ENERGY_BUCKETS - 1)) for i in range(ENERGY_BUCKETS)]

    def cycle_color_mode(self):
        self.color_mode = (self.color_mode + 1) % len(COLOR_MODES)

    def color_label(self):
        return COLOR_MODES[self.color_mode]

    def resize(self, scale, size):
        """Rebuild what depends on the size: background always (cheap), sprites if the scale changed enough."""
        self.scale = scale
        if size != self.size:
            self.size = size
            self.background = self._build_background(size)
        if self.sprite_scale is None or abs(scale / self.sprite_scale - 1.0) > 0.01:
            self.sprite_scale = scale
            self.body_sprites = [self._build_body(c) for c in self.bucket_colors]
            self.dead_sprite = self._build_dead()
            self.food_sprites = [self._build_food(f) for f in range(FOOD_FRAMES)]
            self.poison_sprites = [self._build_poison(f) for f in range(FOOD_FRAMES)]

    # ---------- construction (on resize) ----------

    @staticmethod
    def _build_background(size):
        w, h = size
        # Computed on a small grid then enlarged: the background is smooth, so nothing is lost
        gw, gh = max(16, min(w, 640)), max(9, min(h, 360))
        xs = (np.arange(gw, dtype=np.float32) * (config.SCREEN_WIDTH / gw))[:, None]
        ys = (np.arange(gh, dtype=np.float32) * (config.SCREEN_HEIGHT / gh))[None, :]
        cx, cy = config.SCREEN_WIDTH / 2, config.SCREEN_HEIGHT / 2
        r = np.sqrt(((xs - cx) / cx) ** 2 * 0.8 + ((ys - cy) / cy) ** 2)   # Vignette: bright centre, dark edges
        t = np.clip(r / 1.15, 0.0, 1.0) ** 1.7
        center = np.array(config.BG_CENTER_COLOR, dtype=np.float32)
        edge = np.array(config.BG_EDGE_COLOR, dtype=np.float32)
        img = center * (1.0 - t[..., None]) + edge * t[..., None]
        for bx, by, br, boost in BLOBS:
            g = np.exp(-(((xs - bx) ** 2 + (ys - by) ** 2) / (2.0 * (br / 2.0) ** 2)))
            img += g[..., None] * np.array(boost, dtype=np.float32)
        small = pygame.surfarray.make_surface(np.clip(img, 0, 255).astype(np.uint8))
        return pygame.transform.smoothscale(small, (w, h)).convert()

    def _sprite_canvas(self, half):
        size = int(math.ceil(half)) * 2
        s = SUPERSAMPLE
        return size, s, pygame.Surface((size * s, size * s), pygame.SRCALPHA)

    def _build_body(self, color):
        k = self.sprite_scale
        r = config.CREATURE_RADIUS * k
        size, s, big = self._sprite_canvas(r + 3 * k)
        c = size * s / 2
        dark = _lerp(color, (10, 12, 16), 0.55)
        light = _lerp(color, (255, 255, 255), 0.45)
        pygame.draw.circle(big, (*color, 55), (c, c), (r + 2.5 * k) * s)             # soft halo
        pygame.draw.circle(big, (*color, 225), (c, c), r * s)                        # body
        pygame.draw.circle(big, (*light, 255), (c, c), r * s, max(1, int(1.3 * k * s)))  # membrane
        pygame.draw.circle(big, (*dark, 255), (c, c), r * 0.42 * s)                  # nucleus
        return _shrink(big, size)

    def _build_dead(self):
        k = self.sprite_scale
        r = config.CREATURE_RADIUS * k
        size, s, big = self._sprite_canvas(r + 3 * k)
        c = size * s / 2
        pygame.draw.circle(big, (*config.DEAD_COLOR, 70), (c, c), r * s)
        pygame.draw.circle(big, (*config.DEAD_COLOR, 110), (c, c), r * s, max(1, int(k * s)))
        return _shrink(big, size)

    def _build_food(self, frame):
        k = self.sprite_scale
        r = config.FOOD_RADIUS * k
        halo = r * 4
        size, s, big = self._sprite_canvas(halo + k)
        c = size * s / 2
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.cos(2 * math.pi * frame / FOOD_FRAMES))
        steps = 10
        for i in range(steps):  # concentric discs, alpha growing towards the centre
            radius = halo * s * (1.0 - i / steps)
            alpha = int(70 * pulse * ((i + 1) / steps) ** 1.5)
            pygame.draw.circle(big, (*config.FOOD_COLOR, alpha), (c, c), radius)
        core = _lerp(config.FOOD_COLOR, (255, 255, 255), 0.35)
        pygame.draw.circle(big, (*config.FOOD_COLOR, 255), (c, c), r * s)
        pygame.draw.circle(big, (*core, 255), (c - r * 0.25 * s, c - r * 0.25 * s), r * 0.5 * s)
        return _shrink(big, size)

    def _build_poison(self, frame):
        """Poison: purple halo and a dark diamond with a light edge. A different shape from food, not only a colour."""
        k = self.sprite_scale
        r = config.FOOD_RADIUS * 1.25 * k
        halo = r * 3.6
        size, s, big = self._sprite_canvas(halo + k)
        c = size * s / 2
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.cos(2 * math.pi * frame / FOOD_FRAMES))
        steps = 10
        for i in range(steps):
            radius = halo * s * (1.0 - i / steps)
            alpha = int(80 * pulse * ((i + 1) / steps) ** 1.5)
            pygame.draw.circle(big, (*config.POISON_COLOR, alpha), (c, c), radius)
        d = r * s
        diamond = [(c, c - d), (c + d, c), (c, c + d), (c - d, c)]
        pygame.draw.polygon(big, (*_lerp(config.POISON_COLOR, (10, 12, 16), 0.55), 255), diamond)
        pygame.draw.polygon(big, (*_lerp(config.POISON_COLOR, (255, 255, 255), 0.4), 255), diamond, max(1, int(1.3 * k * s)))
        return _shrink(big, size)

    # ---------- drawing (every frame) ----------

    @staticmethod
    def _blit_wrapped(screen, sprite, x, y, area_w, area_h):
        """Blit a sprite centred on (x, y) (pixels), and its ghost on the other side if it crosses a torus edge."""
        sw, sh = sprite.get_size()
        hw, hh = sw / 2, sh / 2
        xs = [x]
        if x < hw:
            xs.append(x + area_w)
        elif x > area_w - hw:
            xs.append(x - area_w)
        ys = [y]
        if y < hh:
            ys.append(y + area_h)
        elif y > area_h - hh:
            ys.append(y - area_h)
        for px in xs:
            for py in ys:
                screen.blit(sprite, (round(px - hw), round(py - hh)))

    def draw(self, screen, world, debug_mode, selected=None, trail=None):
        """screen: the world area. debug_mode: 0 = off, 1 = selected (else oldest living) creature, 2 = all living."""
        k = self.scale
        screen.blit(self.background, (0, 0))
        ww, wh = world.width * k, world.height * k   # The world, in pixels

        now = pygame.time.get_ticks()  # real time: pulsation does not accelerate with the sim speed
        self._draw_obstacles(screen, world, ww, wh)

        for i, food in enumerate(world.foods):
            if food.cooldown > 0:
                continue  # Eaten, not back yet
            frame = int(now / 90 + i * 3) % FOOD_FRAMES
            self._blit_wrapped(screen, self.food_sprites[frame], food.x * k, food.y * k, ww, wh)

        for i, poison in enumerate(world.poisons):
            if poison.cooldown > 0:
                continue  # Just triggered, not back yet
            frame = int(now / 110 + i * 5) % FOOD_FRAMES
            self._blit_wrapped(screen, self.poison_sprites[frame], poison.x * k, poison.y * k, ww, wh)

        for c in world.creatures:
            if not c.alive:
                self._blit_wrapped(screen, self.dead_sprite, c.x * k, c.y * k, ww, wh)

        if trail is not None:
            self._draw_trail(screen, trail, world)

        r = config.CREATURE_RADIUS * k
        nub_radius = max(1, round(2 * k))
        max_food = max([c.food_eaten for c in world.creatures if c.alive] + [1])
        for c in world.creatures:
            if not c.alive:
                continue
            if self.color_mode == 0:
                ratio = c.energy / config.ENERGY_INPUT_MAX
            elif self.color_mode == 1:
                ratio = c.speed / config.CREATURE_MAX_SPEED
            else:
                ratio = c.food_eaten / max_food
            ratio = max(0.0, min(ratio, 1.0))
            bucket = int(ratio * (ENERGY_BUCKETS - 1) + 0.5)
            color = self.bucket_colors[bucket]
            px, py = c.x * k, c.y * k
            cos_a, sin_a = math.cos(c.angle), math.sin(c.angle)

            # Tail behind the creature: longer when it moves faster
            if c.speed > 0.3:
                length = c.speed * 3.0 * k
                p0 = (px - cos_a * r, py - sin_a * r)
                p1 = (px - cos_a * (r + length), py - sin_a * (r + length))
                pygame.draw.aaline(screen, _lerp(color, (10, 12, 16), 0.35), p0, p1)

            self._blit_wrapped(screen, self.body_sprites[bucket], px, py, ww, wh)

            # Heading marker: small light dot towards the front
            nub = (round(px + cos_a * r * 0.62), round(py + sin_a * r * 0.62))
            pygame.draw.circle(screen, _lerp(color, (255, 255, 255), 0.75), nub, nub_radius)

        if selected is not None:
            center = (round(selected.x * k), round(selected.y * k))
            width = max(1, round(k))
            pygame.draw.circle(screen, (255, 255, 255), center, round(r + 6 * k), width)
            pygame.draw.circle(screen, (120, 125, 130), center, round(r + 9 * k), width)

        if debug_mode:
            self._draw_debug(screen, world, debug_mode, selected)

    def _draw_obstacles(self, screen, world, ww, wh):
        """Solid discs, drawn again on the other side of the torus when they cross an edge."""
        k = self.scale
        fill = config.OBSTACLE_COLOR
        edge = _lerp(config.OBSTACLE_COLOR, (255, 255, 255), 0.3)
        width = max(1, round(1.5 * k))
        for o in world.obstacles:
            r = o.radius * k
            xs = [o.x * k] + ([o.x * k + ww] if o.x * k < r else []) + ([o.x * k - ww] if o.x * k > ww - r else [])
            ys = [o.y * k] + ([o.y * k + wh] if o.y * k < r else []) + ([o.y * k - wh] if o.y * k > wh - r else [])
            for px in xs:
                for py in ys:
                    self._draw_obstacle_shape(screen, o, px, py, k, fill, edge, width)

    def _draw_obstacle_shape(self, screen, o, px, py, k, fill, edge, width):
        """Stone sprite with its shadow (rendering/obstacles.py), centred on (px, py)."""
        sprite, (ox, oy) = obstacle_sprite(o, k)
        screen.blit(sprite, (round(px) - ox, round(py) - oy))

    def _draw_trail(self, screen, trail, world):
        """Trajectory of the selected creature, fading with age. Segments that wrap the torus are skipped."""
        n = len(trail)
        if n < 2:
            return
        k = self.scale
        half_w, half_h = world.width / 2, world.height / 2
        prev = trail[0]
        for i in range(1, n):
            cur = trail[i]
            if abs(cur[0] - prev[0]) < half_w and abs(cur[1] - prev[1]) < half_h:
                pygame.draw.aaline(screen, _lerp(TRAIL_FADE, TRAIL_COLOR, i / n),
                                   (prev[0] * k, prev[1] * k), (cur[0] * k, cur[1] * k))
            prev = cur

    def _draw_debug(self, screen, world, mode, selected=None):
        k = self.scale
        alive = [c for c in world.creatures if c.alive]
        if not alive:
            return
        if mode == 2:
            targets = alive
        elif selected is not None and selected.alive:
            targets = [selected]
        else:
            targets = [max(alive, key=lambda c: (c.age, c.energy))]
        vision_color = config.DEBUG_VISION_COLOR if mode == 1 else _lerp(config.DEBUG_VISION_COLOR, (0, 0, 0), 0.6)
        radius = round(config.VISION_RANGE * k)
        half_fov = math.radians(config.VISION_FOV_DEGREES) / 2.0
        for c in targets:
            center = (round(c.x * k), round(c.y * k))
            if config.VISION_FOV_DEGREES >= 360:
                pygame.draw.circle(screen, vision_color, center, radius, 1)
            else:
                # Field of view: the two edges and the arc between them, centred on the heading
                n = max(8, round(config.VISION_FOV_DEGREES / 5))
                arc = [(center[0] + math.cos(c.angle - half_fov + 2 * half_fov * i / n) * radius,
                        center[1] + math.sin(c.angle - half_fov + 2 * half_fov * i / n) * radius)
                       for i in range(n + 1)]
                pygame.draw.lines(screen, vision_color, False, [arc[0], center, arc[-1]], 1)
                pygame.draw.lines(screen, vision_color, False, arc, 1)
            # Same rule as World.sense (the world's own method): nearest available item in view
            for items, color in ((world.foods, config.DEBUG_LINK_COLOR), (world.poisons, config.POISON_COLOR),
                              (world.obstacles, config.OBSTACLE_COLOR)):
                best, _ = world.nearest(c, items)
                if best is not None:
                    _, dx, dy = best
                    pygame.draw.aaline(screen, color, (c.x * k, c.y * k), ((c.x + dx) * k, (c.y + dy) * k))
            if mode == 1:
                pygame.draw.circle(screen, (255, 255, 255), center, round((config.CREATURE_RADIUS + 5) * k), 1)

"""Births and deaths made visible: a light ring opens where a creature is born, a grey ghost fades where one dies.
Found by comparing the creatures between two frames (nothing in the simulation changes). Real-time animation.
At high speed there are too many events to read: the number shown at once is capped."""
import pygame

BIRTH_MS = 650
DEATH_MS = 700
MAX_EFFECTS = 80
BIRTH_COLOR = (230, 240, 255)
DEATH_COLOR = (112, 118, 128)


class Effects:
    def __init__(self):
        self.enabled = True
        self._world = None
        self._last = {}         # uid → (x, y) at the previous frame
        self.items = []         # (kind, x, y, start ms)

    def update(self, world):
        now = pygame.time.get_ticks()
        current = {c.uid: (c.x, c.y) for c in world.creatures if c.alive}
        if world is not self._world:        # New world: nothing to show for the first frame
            self._world, self._last, self.items = world, current, []
            return
        if self.enabled:
            for uid, pos in current.items():
                if uid not in self._last:
                    self.items.append(("birth", pos[0], pos[1], now))
            for uid, pos in self._last.items():
                if uid not in current:
                    self.items.append(("death", pos[0], pos[1], now))
            if len(self.items) > MAX_EFFECTS:
                self.items = self.items[-MAX_EFFECTS:]
        self._last = current
        self.items = [e for e in self.items if now - e[3] < (BIRTH_MS if e[0] == "birth" else DEATH_MS)]

    def draw(self, screen, world, scene):
        if not self.enabled or not self.items:
            return
        now = pygame.time.get_ticks()
        k = scene.scale
        width = max(1, round(1.5 * k))
        for kind, x, y, start in self.items:
            t = (now - start) / (BIRTH_MS if kind == "birth" else DEATH_MS)
            if t >= 1.0:
                continue   # Ended since update(): a slow frame (zoom, new sprites) can get here late
            t = max(0.0, t)
            for px, py in scene._images(world, x, y, 30):
                if kind == "birth":
                    r = (8 + 22 * t) * k
                    color = tuple(int(c * (1 - t) + 18 * t) for c in BIRTH_COLOR)
                    pygame.draw.circle(screen, color, (round(px), round(py)), max(2, round(r)), width)
                else:
                    s = max(2, round((3.5 + 1.5 * t) * k))
                    color = tuple(int(c * (1 - t) + 18 * t) for c in DEATH_COLOR)
                    pygame.draw.line(screen, color, (px - s, py - s), (px + s, py + s), width)
                    pygame.draw.line(screen, color, (px - s, py + s), (px + s, py - s), width)

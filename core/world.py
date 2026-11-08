import math

import numpy as np

import config
from core.food import Food
from core.obstacle import Obstacle
from core.physics import torus_delta, normalize_angle
from core.creature import Creature
from brain.profiles import PROFILES, SENSORS, new_brain

class World:
    def __init__(self, rng):
        self.rng = rng
        self.width = config.WORLD_WIDTH
        self.height = config.WORLD_HEIGHT
        self.creatures = []
        # FOOD_COUNT, POISON_COUNT and OBSTACLE_COUNT are given per screen-sized area: a bigger world holds more
        self.area_factor = self.width * self.height / (config.SCREEN_WIDTH * config.SCREEN_HEIGHT)
        # Obstacles first: food, poison and creatures are never placed inside one
        self.obstacles = self._make_obstacles()
        reach = config.CREATURE_RADIUS + config.FOOD_RADIUS   # Far enough from an obstacle for a creature to touch it
        self.foods = [Food(*self._free_position(reach), config.FOOD_ENERGY) for _ in range(self._count(config.FOOD_COUNT))]
        # Poison: same kind of object as food, but its `energy` is the damage. Seen through its own two inputs
        self.poisons = [Food(*self._free_position(reach), config.POISON_ENERGY) for _ in range(self._count(config.POISON_COUNT))]
        self.tick = 0

    def _count(self, per_screen):
        return round(per_screen * self.area_factor)

    def _make_obstacles(self):
        """Random obstacles (shapes from OBSTACLE_SHAPES), kept apart so that there is always room to pass between two."""
        obstacles = []
        for _ in range(self._count(config.OBSTACLE_COUNT)):
            for _attempt in range(100):
                radius = self.rng.uniform(config.OBSTACLE_RADIUS_MIN, config.OBSTACLE_RADIUS_MAX)
                x, y = self.rng.uniform(0, self.width), self.rng.uniform(0, self.height)
                if all(math.hypot(torus_delta(x, o.x, self.width), torus_delta(y, o.y, self.height))
                       >= radius + o.radius + config.OBSTACLE_MIN_GAP for o in obstacles):
                    shape = self.rng.choice(config.OBSTACLE_SHAPES)
                    obstacles.append(Obstacle(x, y, radius, shape, self.rng.uniform(0, 2 * math.pi)))
                    break   # No room found after 100 tries: this obstacle is skipped
        return obstacles

    def _blocked(self, x, y, margin):
        """True if the point is inside an obstacle, or closer than `margin` to its edge."""
        for o in self.obstacles:
            dx, dy = torus_delta(o.x, x, self.width), torus_delta(o.y, y, self.height)   # From the obstacle to the point
            if math.hypot(dx, dy) <= o.radius + margin:   # Inside the bounding circle: look at the real shape
                cx, cy, inside = o.closest(dx, dy)
                if inside or math.hypot(dx - cx, dy - cy) <= margin:
                    return True
        return False

    def _free_position(self, margin):
        """Random position outside every obstacle (last try if the world is too crowded)."""
        for _ in range(100):
            x, y = self.rng.uniform(0, self.width), self.rng.uniform(0, self.height)
            if not self._blocked(x, y, margin):
                break
        return x, y

    def _collide(self, creature):
        """A creature cannot enter an obstacle: it is pushed back to the edge, so it slides along it."""
        touched = False
        for _ in range(2):   # Two passes: pushed out of one obstacle, it must not end up inside a neighbour
            for o in self.obstacles:
                dx = torus_delta(o.x, creature.x, self.width)   # From the obstacle to the creature
                dy = torus_delta(o.y, creature.y, self.height)
                if dx * dx + dy * dy >= (o.radius + config.CREATURE_RADIUS) ** 2:
                    continue   # Outside the bounding circle
                pushed = o.push(dx, dy, config.CREATURE_RADIUS)
                if pushed:
                    creature.x = (o.x + pushed[0]) % self.width
                    creature.y = (o.y + pushed[1]) % self.height
                    touched = True
        creature.touching = touched
        if touched:
            creature.obstacle_ticks += 1

    def update(self):
        """One tick. Same rules as _update_reference, with the distance computations done for all creatures at once."""
        if self.is_over():
            return
        # Phase 0: what every creature sees, computed together (items do not move during phase 1)
        self.sense_all()

        # Phase 1: every creature decides and moves
        for creature in self.creatures:
            if creature.alive:
                creature.update(self.sense(creature), self.width, self.height)
        alive = [c for c in self.creatures if c.alive]
        n = len(alive)
        if n:
            X = np.fromiter((c.x for c in alive), float, n)
            Y = np.fromiter((c.y for c in alive), float, n)
            self._collide_all(alive, X, Y)
            X = np.fromiter((c.x for c in alive), float, n)   # Collisions may have moved some of them
            Y = np.fromiter((c.y for c in alive), float, n)
            E = np.fromiter((c.energy for c in alive), float, n)
            reach2 = (config.CREATURE_RADIUS + config.FOOD_RADIUS) ** 2
            half_w, half_h = self.width / 2, self.height / 2

            # Phase 2: food. Each source goes to the closest creature in contact that still has room for the meal
            for food in self.foods:
                if food.cooldown > 0:
                    food.cooldown -= 1
                    continue
                dx = (food.x - X) % self.width
                dx = np.where(dx > half_w, dx - self.width, dx)
                dy = (food.y - Y) % self.height
                dy = np.where(dy > half_h, dy - self.height, dy)
                d2 = np.where(E + food.energy <= config.ENERGY_MAX, dx * dx + dy * dy, np.inf)
                i = int(np.argmin(d2))
                if d2[i] < reach2:
                    best = alive[i]
                    best.eat_food(food.energy)
                    E[i] = min(E[i] + food.energy, config.ENERGY_MAX)
                    food.cooldown = config.FOOD_RESPAWN_DELAY
                    food.eats += 1
                    if not config.FOOD_FIXED_POSITIONS or food.eats >= config.FOOD_MAX_EATS:
                        food.x, food.y = self._free_position(config.CREATURE_RADIUS + config.FOOD_RADIUS)
                        food.eats = 0

            # Phase 3: poison. The closest creature touching it is hurt; the poison then moves to a new random place
            for poison in self.poisons:
                if poison.cooldown > 0:
                    poison.cooldown -= 1
                    continue
                dx = (poison.x - X) % self.width
                dx = np.where(dx > half_w, dx - self.width, dx)
                dy = (poison.y - Y) % self.height
                dy = np.where(dy > half_h, dy - self.height, dy)
                d2 = dx * dx + dy * dy
                i = int(np.argmin(d2))
                if d2[i] < reach2:
                    alive[i].hit_by_poison(poison.energy)
                    poison.cooldown = config.FOOD_RESPAWN_DELAY
                    poison.x, poison.y = self._free_position(config.CREATURE_RADIUS + config.FOOD_RADIUS)
        else:
            for item in self.foods + self.poisons:
                if item.cooldown > 0:
                    item.cooldown -= 1

        self.tick += 1

    def _collide_all(self, alive, X, Y):
        """Obstacle collisions: a cheap numpy test finds the few creatures near an obstacle, only those go through
        the exact push of _collide. The others are simply not touching."""
        near = np.zeros(len(alive), dtype=bool)
        for o in self.obstacles:
            dx = (X - o.x + self.width / 2) % self.width - self.width / 2
            dy = (Y - o.y + self.height / 2) % self.height - self.height / 2
            near |= dx * dx + dy * dy < (o.radius + config.CREATURE_RADIUS) ** 2
        for c, is_near in zip(alive, near):
            if is_near:
                self._collide(c)
            else:
                c.touching = False

    def sense_all(self):
        """Nearest food, poison and obstacle in view of every living creature, for all of them at once (numpy).
        Same rule as nearest(): within range, inside the field of view, available, closest wins (an exact tie goes
        to the last item of the list, like nearest). The result is cached on each creature for this tick."""
        alive = [c for c in self.creatures if c.alive]
        n = len(alive)
        if not n:
            return
        needed = {"food"}
        for name in {c.profile for c in alive}:
            keys = PROFILES[name]["sensors"]
            if "poison" in keys:
                needed.add("poison")
            if "obstacle" in keys:
                needed.add("obstacle")
        cx = np.fromiter((c.x for c in alive), float, n)
        cy = np.fromiter((c.y for c in alive), float, n)
        heading = np.fromiter((c.angle for c in alive), float, n)
        range_ = config.VISION_RANGE
        range2 = range_ ** 2
        all_around = config.VISION_FOV_DEGREES >= 360
        half_fov = math.radians(config.VISION_FOV_DEGREES) / 2.0
        for c in alive:
            c._near = {}
            c._near_tick = self.tick
        rows = np.arange(n)
        for key, items in (("food", self.foods), ("poison", self.poisons), ("obstacle", self.obstacles)):
            if key not in needed:
                continue
            m = len(items)
            if m == 0:
                for c in alive:
                    c._near[key] = None
                    if key == "food":
                        c.food_nearby = False
                continue
            ix = np.fromiter((i.x for i in items), float, m)
            iy = np.fromiter((i.y for i in items), float, m)
            cool = np.fromiter((i.cooldown for i in items), float, m)
            dx = (ix[None, :] - cx[:, None]) % self.width
            dx = np.where(dx > self.width / 2, dx - self.width, dx)
            dy = (iy[None, :] - cy[:, None]) % self.height
            dy = np.where(dy > self.height / 2, dy - self.height, dy)
            d2 = dx * dx + dy * dy
            if key == "obstacle":
                # Distance to the real outline, only for the creatures that can reach the obstacle
                for j, o in enumerate(items):
                    idx = np.nonzero(d2[:, j] <= (range_ + o.radius) ** 2)[0]
                    if idx.size:
                        edge = o.edge_distance_np(-dx[idx, j], -dy[idx, j])
                        d2[idx, j] = edge * edge
            visible = d2 <= range2
            if not all_around:
                rel = (np.arctan2(dy, dx) - heading[:, None] + math.pi) % (2 * math.pi) - math.pi
                visible &= np.abs(rel) <= half_fov
            in_view = visible.any(axis=1)
            masked = np.where(visible & (cool <= 0)[None, :], d2, np.inf)
            j_best = m - 1 - np.argmin(masked[:, ::-1], axis=1)   # Last of equal minima, like nearest()
            best = masked[rows, j_best]
            for i, c in enumerate(alive):
                if key == "food":
                    c.food_nearby = bool(in_view[i])
                if best[i] < np.inf:
                    j = j_best[i]
                    c._near[key] = (float(best[i]), float(dx[i, j]), float(dy[i, j]))
                else:
                    c._near[key] = None

    def _update_reference(self):
        """Plain loop version of update(), one creature at a time. Slow: kept as the reference the tests compare to."""

        if self.is_over():
            return

        # Phase 1: Update all creatures
        for creature in self.creatures:
            if creature.alive:
                inputs = self.sense(creature)
                creature.update(inputs, self.width, self.height)
                self._collide(creature)

        # Phase 2: Check for food consumption
        for food in self.foods:
            # A food that was eaten recently is not there yet: count down and skip it
            if food.cooldown > 0:
                food.cooldown -= 1
                continue

            best = None
            best_distance2 = (config.CREATURE_RADIUS + config.FOOD_RADIUS) ** 2
            
            for creature in self.creatures:
                if not creature.alive or creature.energy + food.energy > config.ENERGY_MAX:
                    continue  # Dead, or the meal would not fit: leaves the food to the others
                dx = torus_delta(creature.x, food.x, self.width)
                dy = torus_delta(creature.y, food.y, self.height)
                distance2 = dx * dx + dy * dy
                if distance2 < best_distance2:
                    best_distance2 = distance2
                    best = creature

            if best is not None:
                best.eat_food(food.energy)
                # The food comes back after a delay. A source that has been eaten FOOD_MAX_EATS
                # times is exhausted: it comes back at a new random place instead
                food.cooldown = config.FOOD_RESPAWN_DELAY
                food.eats += 1
                if not config.FOOD_FIXED_POSITIONS or food.eats >= config.FOOD_MAX_EATS:
                    food.x, food.y = self._free_position(config.CREATURE_RADIUS + config.FOOD_RADIUS)
                    food.eats = 0

        # Phase 3: poison. The closest creature touching it is hurt; the poison then moves to a new random place
        for poison in self.poisons:
            if poison.cooldown > 0:
                poison.cooldown -= 1
                continue
            victim = None
            best_distance2 = (config.CREATURE_RADIUS + config.FOOD_RADIUS) ** 2
            for creature in self.creatures:
                if not creature.alive:
                    continue
                dx = torus_delta(creature.x, poison.x, self.width)
                dy = torus_delta(creature.y, poison.y, self.height)
                distance2 = dx * dx + dy * dy
                if distance2 < best_distance2:
                    best_distance2 = distance2
                    victim = creature
            if victim is not None:
                victim.hit_by_poison(poison.energy)
                poison.cooldown = config.FOOD_RESPAWN_DELAY
                poison.x, poison.y = self._free_position(config.CREATURE_RADIUS + config.FOOD_RADIUS)

        self.tick += 1

    def add_creature(self, brain, profile):
        x, y = self._free_position(config.CREATURE_RADIUS)
        angle = self.rng.uniform(-math.pi, math.pi)
        creature = Creature(x, y, angle, config.INITIAL_ENERGY, brain, profile)
        self.creatures.append(creature)

    def add_population(self, profile, count):
        """`count` creatures of the profile with random networks."""
        for _ in range(count):
            brain = new_brain(profile)
            brain.randomize(self.rng, config.NN_INIT_STD)
            self.add_creature(brain, profile)

    def nearest(self, creature, items):
        """Nearest available item in the creature's field of view: ((distance², dx, dy) or None, in_view).
        In view = within the vision range AND within VISION_FOV_DEGREES centred on the heading.
        in_view says whether any item is in view, available or not. Also used by the debug overlay."""
        best = None
        range2 = config.VISION_RANGE ** 2
        best_distance2 = range2
        in_view = False
        all_around = config.VISION_FOV_DEGREES >= 360
        half_fov = math.radians(config.VISION_FOV_DEGREES) / 2.0
        for item in items:
            dx = torus_delta(creature.x, item.x, self.width)
            dy = torus_delta(creature.y, item.y, self.height)
            distance2 = dx * dx + dy * dy
            if item.radius:
                # Obstacle: the distance is measured to its edge, the angle stays the one of its centre
                if distance2 > (range2 ** 0.5 + item.radius) ** 2:
                    continue   # Too far even for its bounding circle
                edge = item.edge_distance(-dx, -dy)   # The point (creature) relative to the obstacle centre
                distance2 = edge * edge
            if distance2 > range2:
                continue
            # Range is tested first: the angle (atan2) is only computed for the few items that are close enough
            if not all_around and abs(normalize_angle(math.atan2(dy, dx) - creature.angle)) > half_fov:
                continue  # Outside the field of view
            in_view = True
            if item.cooldown > 0:
                continue  # Not available yet: the network cannot see it
            if distance2 <= best_distance2:
                best_distance2 = distance2
                best = (distance2, dx, dy)
        return best, in_view

    def _direction(self, creature, found):
        """Network inputs for one kind of target: [distance, relative angle]. Nothing in view: maximum distance, ahead."""
        if found is None:
            return [1.0, 0.0]
        distance2, dx, dy = found
        distance = math.sqrt(distance2) / config.VISION_RANGE
        angle = normalize_angle(math.atan2(dy, dx) - creature.angle) / math.pi
        return [distance, angle]

    def sense(self, creature):
        """Network inputs: the sensors of the creature's profile (brain/profiles.py), then its memory cells.
        Uses what sense_all found for this tick when it is there, else looks up the nearest items itself
        (the interface calls it for the selected creature). The nearest food is always looked up: it feeds the
        `food_nearby` metric."""
        if getattr(creature, "_near_tick", -1) == self.tick:
            ctx = creature._near
        else:
            food, in_view = self.nearest(creature, self.foods)
            creature.food_nearby = in_view  # Any food in view, even one that is not available yet (metric only)
            ctx = {"food": food}
        values = []
        for key in PROFILES[creature.profile]["sensors"]:
            values += SENSORS[key][1](self, creature, ctx)
        return values + creature.memory

    def is_over(self):
        """The generation ends at the time cap, or when every species is down to its number of parents
        (config.parents_for: a species of one creature ends when it is dead)."""
        if self.tick >= config.GEN_MAX_TICKS:
            return True
        total, alive = {}, {}
        for c in self.creatures:
            total[c.profile] = total.get(c.profile, 0) + 1
            if c.alive:
                alive[c.profile] = alive.get(c.profile, 0) + 1
        return all(alive.get(p, 0) <= (config.parents_for(n) if n > 1 else 0)
                   for p, n in total.items())

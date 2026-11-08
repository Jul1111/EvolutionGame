import math

import numpy as np

import config
from core.food import Food
from core.obstacle import Obstacle
from core.physics import torus_delta, normalize_angle
from core.creature import Creature
from brain.profiles import PROFILES, needed_items, new_brain
from core.sensors import SENSORS

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
        self.eaten = 0             # Meals and poison hits since the start (continuous measures)
        self.poisoned = 0
        # Every kind of item a creature can perceive, by name. A new kind of item: add it here, then a sensor
        # nearest_of("<kind>") in core/sensors.py
        self.items = {"food": self.foods, "poison": self.poisons, "obstacle": self.obstacles}

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

    def _place_item(self, item):
        """Where a food or a poison reappears: a random place outside the obstacles and at least SPAWN_CLEARANCE from
        the edge of every living creature (never on one, never right next to one). Returns False when no such place
        was found in 100 tries (crowded world): the item then waits one more tick and tries again."""
        reach = config.CREATURE_RADIUS + config.FOOD_RADIUS
        living = [c for c in self.creatures if c.alive]
        n = len(living)
        if n:
            cx = np.fromiter((c.x for c in living), float, n)
            cy = np.fromiter((c.y for c in living), float, n)
            keep = (np.fromiter((c.radius for c in living), float, n) + config.FOOD_RADIUS
                    + config.SPAWN_CLEARANCE) ** 2
        for _ in range(100):
            x, y = self.rng.uniform(0, self.width), self.rng.uniform(0, self.height)
            if self._blocked(x, y, reach):
                continue
            if n:
                dx = (cx - x + self.width / 2) % self.width - self.width / 2
                dy = (cy - y + self.height / 2) % self.height - self.height / 2
                if (dx * dx + dy * dy < keep).any():
                    continue
            item.x, item.y = x, y
            return True
        return False

    def _item_returns(self, item):
        """Count down an eaten food or a used poison; on the tick it comes back, it is placed (or waits one more tick)."""
        item.cooldown -= 1
        if item.cooldown == 0 and not self._place_item(item):
            item.cooldown = 1

    def _collide(self, creature, obstacles=None):
        """A creature cannot enter an obstacle: it is pushed back to the edge, so it slides along it.
        `obstacles`: the ones to test (default: all of them)."""
        touched = False
        for _ in range(2):   # Two passes: pushed out of one obstacle, it must not end up inside a neighbour
            for o in self.obstacles if obstacles is None else obstacles:
                dx = torus_delta(o.x, creature.x, self.width)   # From the obstacle to the creature
                dy = torus_delta(o.y, creature.y, self.height)
                if dx * dx + dy * dy >= (o.radius + creature.radius) ** 2:
                    continue   # Outside the bounding circle
                pushed = o.push(dx, dy, creature.radius)
                if pushed:
                    creature.x = (o.x + pushed[0]) % self.width
                    creature.y = (o.y + pushed[1]) % self.height
                    touched = True
        creature.touching = touched
        if touched:
            creature.obstacle_ticks += 1

    def update(self):
        """One tick. Same rules as _update_reference (tests/test_world.py checks it), computed for all creatures at once."""
        # Phase 0: what every creature sees, computed together (items do not move during phase 1)
        self.sense_all()

        # Phase 1: every creature decides and moves, then obstacles push it back
        for creature in self.creatures:
            if creature.alive:
                creature.update(self.sense(creature), self.width, self.height)
        alive = [c for c in self.creatures if c.alive]
        if alive:
            n = len(alive)
            X = np.fromiter((c.x for c in alive), float, n)
            Y = np.fromiter((c.y for c in alive), float, n)
            if self._collide_all(alive, X, Y):
                X = np.fromiter((c.x for c in alive), float, n)   # Collisions moved some of them
                Y = np.fromiter((c.y for c in alive), float, n)
            E = np.fromiter((c.energy for c in alive), float, n)
            body = (np.fromiter((c.radius for c in alive), float, n),       # Contact radius (body size)
                    np.fromiter((c.energy_max for c in alive), float, n))   # Energy reserve (body size)
            # Phase 2: food goes to the closest creature in contact that still has room for the whole meal
            self._contacts(self.foods, alive, X, Y, E, body, self._eat, fits=True)
            # Phase 3: poison hurts the closest creature in contact, then moves to a new random place
            self._contacts(self.poisons, alive, X, Y, E, body, self._poisoned, fits=False)
        else:
            for item in self.foods + self.poisons:
                if item.cooldown > 0:
                    self._item_returns(item)
        self.tick += 1

    def _contacts(self, items, alive, X, Y, E, body, effect, fits):
        """For each available item, in list order: the closest living creature in contact gets `effect`.
        body = (contact radius, energy reserve) of each creature.
        fits=True: only creatures for which the item energy fits under their reserve are eligible.
        A cheap numpy pass finds the items that touch someone; only those are resolved one by one (an item
        changes E, which matters for the next one)."""
        m = len(items)
        if m == 0:
            return
        radius, emax = body
        reach2 = (radius + config.FOOD_RADIUS) ** 2   # One value per creature
        ix = np.fromiter((i.x for i in items), float, m)
        iy = np.fromiter((i.y for i in items), float, m)
        dx = (ix[:, None] - X[None, :] + self.width / 2) % self.width - self.width / 2
        dy = (iy[:, None] - Y[None, :] + self.height / 2) % self.height - self.height / 2
        d2 = dx * dx + dy * dy
        touching = (d2 < reach2[None, :]).any(axis=1)
        for j, item in enumerate(items):
            if item.cooldown > 0:
                self._item_returns(item)   # May place it: it is only available from the next tick
                continue
            if not touching[j]:
                continue
            # Closest creature in contact; the distance is measured to its edge, as the bodies differ in size
            gap = np.where(d2[j] < reach2, np.sqrt(d2[j]) - radius, np.inf)
            if fits:
                gap = np.where(E + item.energy <= emax, gap, np.inf)
            i = int(np.argmin(gap))
            if gap[i] < np.inf:
                effect(item, alive[i])
                E[i] = alive[i].energy

    def _eat(self, food, creature):
        creature.eat_food(food.energy)
        self.eaten += 1
        food.cooldown = max(1, config.FOOD_RESPAWN_DELAY)   # Placed elsewhere when it comes back (_item_returns)

    def _poisoned(self, poison, creature):
        creature.hit_by_poison(poison.energy)
        self.poisoned += 1
        poison.cooldown = max(1, config.FOOD_RESPAWN_DELAY)   # Placed elsewhere when it comes back (_item_returns)

    def _collide_all(self, alive, X, Y):
        """Obstacle collisions: a numpy test finds, for each creature, the obstacles whose bounding circle it
        overlaps; only those go through the exact push of _collide. Returns True if at least one creature touched."""
        m = len(self.obstacles)
        for c in alive:
            c.touching = False
        if m == 0:
            return False
        ox = np.fromiter((o.x for o in self.obstacles), float, m)
        oy = np.fromiter((o.y for o in self.obstacles), float, m)
        orad = np.fromiter((o.radius for o in self.obstacles), float, m)
        crad = np.fromiter((c.radius for c in alive), float, len(alive))
        lim = (orad[None, :] + crad[:, None]) ** 2
        dx = (X[:, None] - ox[None, :] + self.width / 2) % self.width - self.width / 2
        dy = (Y[:, None] - oy[None, :] + self.height / 2) % self.height - self.height / 2
        near = dx * dx + dy * dy < lim
        moved = False
        for i in np.nonzero(near.any(axis=1))[0]:
            # A creature pushed out of one obstacle can land in a neighbour: neighbours = obstacles near it
            # (an obstacle is at least OBSTACLE_MIN_GAP away from the others, so the candidates are enough)
            candidates = [self.obstacles[j] for j in np.nonzero(near[i])[0]]
            self._collide(alive[i], candidates)
            moved |= alive[i].touching
        return moved

    def sense_all(self):
        """Nearest food, poison and obstacle in view of every living creature, for all of them at once (numpy).
        Same rule as nearest(): within range, inside the field of view, available, closest wins (an exact tie goes
        to the last item of the list, like nearest). The result is cached on each creature for this tick."""
        alive = [c for c in self.creatures if c.alive]
        n = len(alive)
        if not n:
            return
        needed = needed_items({c.profile for c in alive})
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
        for key in sorted(needed):
            items = self.items[key]
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
            if getattr(items[0], "radius", 0):
                # Item with an extent (obstacle): distance to its real outline, only for the creatures in reach
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

        # Phase 1: Update all creatures
        for creature in self.creatures:
            if creature.alive:
                inputs = self.sense(creature)
                creature.update(inputs, self.width, self.height)
                self._collide(creature)

        # Phase 2: Check for food consumption
        for food in self.foods:
            # A food that was eaten recently is not there yet: count down and skip it (placed when it comes back)
            if food.cooldown > 0:
                self._item_returns(food)
                continue

            best = None
            best_gap = math.inf

            for creature in self.creatures:
                if not creature.alive or creature.energy + food.energy > creature.energy_max:
                    continue  # Dead, or the meal would not fit: leaves the food to the others
                dx = torus_delta(creature.x, food.x, self.width)
                dy = torus_delta(creature.y, food.y, self.height)
                distance = math.hypot(dx, dy)
                if distance < creature.radius + config.FOOD_RADIUS and distance - creature.radius < best_gap:
                    best_gap = distance - creature.radius
                    best = creature

            if best is not None:
                best.eat_food(food.energy)
                # The food comes back after a delay, at a new random place away from the creatures
                food.cooldown = max(1, config.FOOD_RESPAWN_DELAY)

        # Phase 3: poison. The closest creature touching it is hurt; the poison then moves to a new random place
        for poison in self.poisons:
            if poison.cooldown > 0:
                self._item_returns(poison)
                continue
            victim = None
            best_gap = math.inf
            for creature in self.creatures:
                if not creature.alive:
                    continue
                dx = torus_delta(creature.x, poison.x, self.width)
                dy = torus_delta(creature.y, poison.y, self.height)
                distance = math.hypot(dx, dy)
                if distance < creature.radius + config.FOOD_RADIUS and distance - creature.radius < best_gap:
                    best_gap = distance - creature.radius
                    victim = creature
            if victim is not None:
                victim.hit_by_poison(poison.energy)
                poison.cooldown = max(1, config.FOOD_RESPAWN_DELAY)

        self.tick += 1

    def resize_items(self):
        """Applies FOOD_COUNT and POISON_COUNT changed during the run: new items at free places, or the last ones removed.
        Obstacles are only drawn when the world is created."""
        reach = config.CREATURE_RADIUS + config.FOOD_RADIUS
        for items, count, energy in ((self.foods, config.FOOD_COUNT, config.FOOD_ENERGY),
                                     (self.poisons, config.POISON_COUNT, config.POISON_ENERGY)):
            target = self._count(count)
            del items[target:]
            while len(items) < target:
                item = Food(*self._free_position(reach), energy)
                if not self._place_item(item):
                    item.cooldown = 1   # No room away from the creatures now: it will try again next tick
                items.append(item)
            for item in items:
                item.energy = energy

    def add_creature(self, brain, profile, energy=None, near=None, **lineage):
        """Adds a creature at a random free place, or close to `near` = (x, y) (a newborn next to its parent).
        `lineage`: uid, parent_id, birth_tick, lineage_gen, size (see Creature)."""
        margin = config.CREATURE_RADIUS * lineage.get("size", 1.0)
        x, y = self._free_position(margin) if near is None else self._free_near(*near, margin)
        angle = self.rng.uniform(-math.pi, math.pi)
        creature = Creature(x, y, angle, config.INITIAL_ENERGY if energy is None else energy, brain, profile,
                            **lineage)
        self.creatures.append(creature)
        return creature

    def _free_near(self, x, y, margin=None):
        """Free position a few radii from (x, y); a random free place if the surroundings are blocked."""
        margin = config.CREATURE_RADIUS if margin is None else margin
        for _ in range(20):
            a = self.rng.uniform(-math.pi, math.pi)
            d = self.rng.uniform(2, 4) * margin
            nx, ny = (x + d * math.cos(a)) % self.width, (y + d * math.sin(a)) % self.height
            if not self._blocked(nx, ny, margin):
                return nx, ny
        return self._free_position(margin)

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

    def direction(self, creature, found):
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
            values += SENSORS[key].fn(self, creature, ctx)
        return values + creature.memory

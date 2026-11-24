import math

import numpy as np

import config
from core.food import Food, kind_pattern, kind_position
from core.obstacle import Obstacle
from core.physics import torus_delta, normalize_angle
from core.creature import Creature, CreatureStore
from brain.profiles import IS_PREDATOR, PROFILES, PROFILE_NAMES, needed_items, new_brain
from core.sensors import SENSORS
from core.batch import decide_and_move
from core import kernels
from core.grid import near_pairs

class World:
    def __init__(self, rng, cfg=config):
        self.rng = rng
        self.cfg = cfg   # Settings in force (see self.cfg.Settings)
        self.width = self.cfg.WORLD_WIDTH
        self.height = self.cfg.WORLD_HEIGHT
        self.store = CreatureStore()   # Numeric state of the creatures, row i = self.creatures[i]
        self._creatures = []
        # FOOD_COUNT, POISON_COUNT and OBSTACLE_COUNT are given per screen-sized area: a bigger world holds more
        self.area_factor = self.width * self.height / (self.cfg.SCREEN_WIDTH * self.cfg.SCREEN_HEIGHT)
        # Obstacles first: food, poison and creatures are never placed inside one
        self.obstacles = self._make_obstacles()
        # Far enough from an obstacle for a creature to touch it
        reach = self.cfg.CREATURE_RADIUS + self.cfg.FOOD_RADIUS
        self._kinds = kind_pattern(self.cfg)   # Kind of the food of index i: self._kinds[i % len(self._kinds)]
        self.foods = [Food(*self._free_position(reach), self.cfg.FOOD_ENERGY, self._kind_of(k))
                      for k in range(self._count(self.cfg.FOOD_COUNT))]
        # Poison: same kind of object as food, but its `energy` is the damage. Seen through its own two inputs
        self.poisons = [Food(*self._free_position(reach), self.cfg.POISON_ENERGY)
                        for _ in range(self._count(self.cfg.POISON_COUNT))]
        self.tick = 0
        self.blind_ticks = 0       # Ticks of life with no available food in view, speed and |turn| then (core/batch.py)
        self.blind_speed = 0.0
        self.blind_turn = 0.0
        self.eaten = 0             # Meals and poison hits since the start (continuous measures)
        self.poisoned = 0
        self.predated = 0          # Prey eaten since the start (config.PREDATION)
        self.hunting = False       # Predators and prey alive at this tick (World.sense_all)
        # Hunting measures since the start (core/batch.py): «prey» = the predators and the prey they see, «predator»
        # = the prey and the predators they see. Ticks of life, ticks with one in view, speed with and without one in
        # view, turn toward it (turn × side of the target: > 0 = turns toward, < 0 = turns away)
        self.hunt = {k: dict.fromkeys(("ticks", "seen", "speed_seen", "speed_unseen", "toward"), 0.0)
                     for k in ("prey", "predator")}
        self._points = None        # Creatures as points while _update_reference runs (positions at the tick start)
        # Every kind of item a creature can perceive, by name. A new kind of item: add it here, then a sensor
        # nearest_of("<kind>") in core/sensors.py
        self.items = {"food": self.foods, "poison": self.poisons, "obstacle": self.obstacles}

    @property
    def creatures(self):
        return self._creatures

    @creatures.setter
    def creatures(self, new):
        """A new list of this world's creatures (the dead removed, usually): their rows follow, in the same order."""
        new = list(new)
        rows = np.fromiter((c._i for c in new), np.int64, len(new))
        if len(new) != self.store.n or (rows != np.arange(len(new))).any():
            self.store.keep(rows)
            for i, c in enumerate(new):
                c._i = i
        self._creatures = new

    def columns(self, *names):
        """Python lists of the given CreatureStore fields, item i = self.creatures[i]: for code that reads many
        creatures (the drawing), much faster than one attribute at a time (each goes through the store)."""
        return [self.store.col(n).tolist() for n in names]

    def living(self):
        """(living creatures, their rows in the store): rows is slice(None) when every creature is alive."""
        alive = self.store.col("alive")
        if alive.all():
            return list(self._creatures), slice(None)
        rows = np.nonzero(alive)[0]
        return [self._creatures[i] for i in rows], rows

    def _count(self, per_screen):
        return round(per_screen * self.area_factor)

    def _make_obstacles(self):
        """Random obstacles (shapes from OBSTACLE_SHAPES), kept apart so that there is always room to pass between
        two."""
        obstacles = []
        for _ in range(self._count(self.cfg.OBSTACLE_COUNT)):
            for _attempt in range(100):
                radius = self.rng.uniform(self.cfg.OBSTACLE_RADIUS_MIN, self.cfg.OBSTACLE_RADIUS_MAX)
                x, y = self.rng.uniform(0, self.width), self.rng.uniform(0, self.height)
                if all(math.hypot(torus_delta(x, o.x, self.width), torus_delta(y, o.y, self.height))
                       >= radius + o.radius + self.cfg.OBSTACLE_MIN_GAP for o in obstacles):
                    shape = self.rng.choice(self.cfg.OBSTACLE_SHAPES)
                    obstacles.append(Obstacle(x, y, radius, shape, self.rng.uniform(0, 2 * math.pi)))
                    break   # No room found after 100 tries: this obstacle is skipped
        return obstacles

    def _blocked(self, x, y, margin):
        """True if the point is inside an obstacle, or closer than `margin` to its edge."""
        for o in self.obstacles:
            # From the obstacle to the point
            dx, dy = torus_delta(o.x, x, self.width), torus_delta(o.y, y, self.height)
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
        reach = self.cfg.CREATURE_RADIUS + self.cfg.FOOD_RADIUS
        s = self.store
        rows = s.col("alive")
        n = int(rows.sum())
        if n:
            cx, cy = s.col("x")[rows], s.col("y")[rows]
            keep = (s.col("radius")[rows] + self.cfg.FOOD_RADIUS + self.cfg.SPAWN_CLEARANCE) ** 2
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
        """Count down an eaten food or a used poison; on the tick it comes back, it is placed (or waits one more
        tick)."""
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
        """One tick. Same rules as _update_reference (tests/test_world.py checks it), computed for all creatures at
        once."""
        # Phase 0: what every creature sees, computed together (items do not move during phase 1)
        seeing = self.sense_all()

        # Phase 1: every creature decides and moves (all at once, core/batch.py), then obstacles push it back
        if seeing:
            decide_and_move(self, seeing, self._near_rows, self._near)
        alive, rows = self.living()
        if alive:
            s = self.store
            X, Y = s.col("x")[rows].copy(), s.col("y")[rows].copy()
            if self._collide_all(alive, rows, X, Y):
                X, Y = s.col("x")[rows].copy(), s.col("y")[rows].copy()   # Collisions moved some of them
            E = s.col("energy")[rows].copy()
            body = (s.col("radius")[rows].copy(),        # Contact radius (body size)
                    s.col("energy_max")[rows].copy())    # Energy reserve (body size)
            # Phase 2: food goes to the closest creature in contact that still has room for the whole meal (its share
            # of it, with two kinds of food). Predators never eat food: left out
            gains = self.gains(s.col("diet")[rows])
            hunters = IS_PREDATOR[s.col("species")[rows]]
            if hunters.any():
                k = np.nonzero(~hunters)[0]
                if len(k):
                    self._contacts(self.foods, [alive[i] for i in k.tolist()], X[k], Y[k], E[k],
                                   (body[0][k], body[1][k]), self._eat, fits=True,
                                   gains=None if gains is None else gains[k])
                else:
                    self._countdown(self.foods)
            else:
                self._contacts(self.foods, alive, X, Y, E, body, self._eat, fits=True, gains=gains)
            # Phase 3: poison hurts the closest creature in contact, then moves to a new random place
            self._contacts(self.poisons, alive, X, Y, E, body, self._poisoned, fits=False)
            # Phase 4: predators kill the prey they touch (config.PREDATION)
            if hunters.any():
                self._predation(alive, rows, hunters)
        else:
            self._countdown(self.foods + self.poisons)
        self.tick += 1

    def _countdown(self, items):
        """Items not available yet count down (nobody can take them this tick)."""
        for item in items:
            if item.cooldown > 0:
                self._item_returns(item)

    def _predation(self, alive, rows, hunters):
        """Phase 4. Each prey (creature of a non-predator profile), in list order, is killed by the closest predator
        that touches it (centres closer than the sum of the radii; distance measured to the predator's edge), is not
        digesting, and has room for the meal: PREDATION_EFFICIENCY × the prey's energy. `hunters`: which creatures of
        `alive` are predators. Their digestion counts down first."""
        s = self.store
        idx = np.arange(s.n)[rows]
        pred, k = idx[hunters], np.nonzero(hunters)[0]
        s.digest[pred] = np.maximum(s.digest[pred] - 1, 0)
        prey = np.nonzero(~hunters)[0]
        if not len(prey):
            return
        q = idx[prey]
        px, py, pr = s.x[q], s.y[q], s.radius[q]
        gain = self.cfg.PREDATION_EFFICIENCY * np.maximum(s.energy[q], 0.0)
        X, Y, E, R, emax = s.x[pred], s.y[pred], s.energy[pred].copy(), s.radius[pred], s.energy_max[pred]
        ready = s.digest[pred] == 0
        if kernels.ENABLED:
            win = kernels.prey_winners(px, py, pr, gain, X, Y, E, R, emax, ready, self.width, self.height)
        else:
            win = self._prey_winners(px, py, pr, gain, X, Y, E, R, emax, ready)
        for j in np.nonzero(win >= 0)[0].tolist():
            alive[k[win[j]]].eat_prey(alive[prey[j]], float(gain[j]))
            self.predated += 1

    def _prey_winners(self, px, py, pr, gain, X, Y, E, R, emax, ready):
        """numpy version of kernels.prey_winners: same formulas, same order (prey in list order, a tie goes to the
        first predator), from the pairs of neighbouring grid cells."""
        m = len(px)
        win = np.full(m, -1, np.int64)
        pj, pi = near_pairs(px, py, X, Y, float(R.max() + pr.max()), self.width, self.height)
        dx = (px[pj] - X[pi] + self.width / 2) % self.width - self.width / 2
        dy = (py[pj] - Y[pi] + self.height / 2) % self.height - self.height / 2
        d2 = dx * dx + dy * dy
        contact = d2 < (R[pi] + pr[pj]) ** 2
        pj, pi, d2 = pj[contact], pi[contact], d2[contact]
        order = np.lexsort((pi, pj))
        pj, pi, d2 = pj[order], pi[order], d2[order]
        bounds = np.searchsorted(pj, np.arange(m + 1)).tolist()
        for j in range(m):
            lo, hi = bounds[j], bounds[j + 1]
            if lo == hi:
                continue
            who = pi[lo:hi]
            ok = ready[who] & (E[who] + gain[j] <= emax[who])
            if not ok.any():
                continue
            gap = np.where(ok, np.sqrt(d2[lo:hi]) - R[who], np.inf)
            i = int(who[int(np.argmin(gap))])
            win[j] = i
            E[i] = E[i] + gain[j]
            ready[i] = False
        return win

    def _contacts(self, items, alive, X, Y, E, body, effect, fits, gains=None):
        """For each available item, in list order: the closest living creature in contact gets `effect`.
        body = (contact radius, energy reserve) of each creature.
        fits=True: only creatures for which the item energy fits under their reserve are eligible.
        gains: (creatures, 2) share of the energy of an item of each kind (World.gains), None = the whole of it.
        A cheap numpy pass finds the items that touch someone; only those are resolved one by one (an item
        changes E, which matters for the next one)."""
        m = len(items)
        if m == 0:
            return
        radius, emax = body
        reach2 = (radius + self.cfg.FOOD_RADIUS) ** 2   # One value per creature
        ix = np.fromiter((i.x for i in items), float, m)
        iy = np.fromiter((i.y for i in items), float, m)
        if kernels.ENABLED:   # Compiled (core/kernels.py): the winner of each item, then the effects in list order
            energy = np.fromiter((i.energy for i in items), float, m)
            available = np.fromiter((i.cooldown <= 0 for i in items), bool, m)
            kinds = np.fromiter((i.kind for i in items), np.int64, m) if gains is not None else np.zeros(m, np.int64)
            win = kernels.contact_winners(ix, iy, energy, available, X, Y, E, radius, emax, self.cfg.FOOD_RADIUS,
                                          fits, self.width, self.height, gains, kinds).tolist()
            for j, item in enumerate(items):
                if item.cooldown > 0:
                    self._item_returns(item)
                elif win[j] >= 0:
                    i = win[j]
                    effect(item, alive[i], item.energy if gains is None else item.energy * gains[i, item.kind])
            return
        # Only the pairs of neighbouring grid cells (core/grid.py), with the same distance formula as a full matrix
        pj, pi = near_pairs(ix, iy, X, Y, float(np.sqrt(reach2.max())), self.width, self.height)
        dx = (ix[pj] - X[pi] + self.width / 2) % self.width - self.width / 2
        dy = (iy[pj] - Y[pi] + self.height / 2) % self.height - self.height / 2
        d2 = dx * dx + dy * dy
        contact = d2 < reach2[pi]
        pj, pi, d2 = pj[contact], pi[contact], d2[contact]
        order = np.lexsort((pi, pj))   # By item, then by creature (argmin then keeps the first creature, as before)
        pj, pi, d2 = pj[order], pi[order], d2[order]
        bounds = np.searchsorted(pj, np.arange(m + 1)).tolist()
        for j, item in enumerate(items):
            if item.cooldown > 0:
                self._item_returns(item)   # May place it: it is only available from the next tick
                continue
            lo, hi = bounds[j], bounds[j + 1]
            if lo == hi:
                continue   # Nobody touches it
            # Closest creature in contact; the distance is measured to its edge, as the bodies differ in size
            who = pi[lo:hi]
            gap = np.sqrt(d2[lo:hi]) - radius[who]
            amount = item.energy if gains is None else item.energy * gains[who, item.kind]
            if fits:
                gap = np.where(E[who] + amount <= emax[who], gap, np.inf)
            k = int(np.argmin(gap))
            if gap[k] < np.inf:
                i = int(who[k])
                effect(item, alive[i], amount if gains is None else float(amount[k]))
                E[i] = alive[i].energy

    def _kind_of(self, index):
        """Kind of the food of this index in self.foods (FOOD_KIND_SHARES, core/food.py)."""
        return self._kinds[index % len(self._kinds)]

    def gains(self, diets):
        """Part of a food's energy that each creature gets, by kind of food: array (creatures, FOOD_TYPES) for an
        array of diets; None when there is one kind of food (FOOD_TYPES = 1: the whole energy, the runs before 23/11).
        Kind k feeds best the diet k / (FOOD_TYPES - 1): (1 - |diet - k / (FOOD_TYPES - 1)| × (FOOD_TYPES - 1)) **
        DIET_EXPONENT, 0 beyond the neighbouring kinds, times FOOD_KIND_ENERGY[k] (richer or poorer kinds)."""
        n = self.cfg.FOOD_TYPES
        if n < 2:
            return None
        spread = n - 1
        out = np.stack([np.maximum(0.0, 1.0 - np.abs(diets - kind_position(k, n)) * spread) ** self.cfg.DIET_EXPONENT
                        for k in range(n)], axis=1)
        if self.cfg.FOOD_KIND_ENERGY:
            out *= np.asarray(self.cfg.FOOD_KIND_ENERGY, float)
        return out

    def gain(self, creature, food):
        """Part of `food`'s energy that `creature` gets (1 with one kind of food)."""
        if self.cfg.FOOD_TYPES < 2:
            return 1.0
        return float(self.gains(np.array([creature.diet]))[0, food.kind])

    def _eat(self, food, creature, amount):
        creature.eat_food(amount)
        self.eaten += 1
        food.cooldown = max(1, self.cfg.FOOD_RESPAWN_DELAY)   # Placed elsewhere when it comes back (_item_returns)

    def _poisoned(self, poison, creature, amount):
        creature.hit_by_poison(poison.energy)
        self.poisoned += 1
        poison.cooldown = max(1, self.cfg.FOOD_RESPAWN_DELAY)   # Placed elsewhere when it comes back (_item_returns)

    def _collide_all(self, alive, rows, X, Y):
        """Obstacle collisions: a numpy test finds, for each creature, the obstacles whose bounding circle it
        overlaps; only those go through the exact push of _collide. Returns True if at least one creature touched.
        `rows`: rows of `alive` in the store."""
        m = len(self.obstacles)
        self.store.col("touching")[rows] = False
        if m == 0:
            return False
        ox = np.fromiter((o.x for o in self.obstacles), float, m)
        oy = np.fromiter((o.y for o in self.obstacles), float, m)
        orad = np.fromiter((o.radius for o in self.obstacles), float, m)
        crad = self.store.col("radius")[rows]
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
        to the last item of the list, like nearest). Keeps, for this tick, {kind: (distance², dx, dy)} arrays aligned
        with the returned list of living creatures (distance² = inf when nothing is seen); World.sense reads them."""
        alive, alive_rows = self.living()
        n = len(alive)
        self._near, self._near_tick, self._near_rows = {}, self.tick, alive_rows
        if not n:
            return alive
        s = self.store
        species = s.col("species")[alive_rows]
        needed = needed_items({PROFILE_NAMES[k] for k in np.unique(species).tolist()})
        hunt = IS_PREDATOR[species]
        self.hunting = bool(hunt.any()) and not hunt.all()
        if self.hunting:   # Both are measured (World.hunt) whatever the sensors of the profiles
            needed |= {"prey", "predator"}
        cx, cy, heading = s.col("x")[alive_rows], s.col("y")[alive_rows], s.col("angle")[alive_rows]
        rows = np.arange(n)
        food_seen = np.zeros(n, dtype=bool)
        for key in sorted(needed):
            if key in ("prey", "predator"):
                self._near[key] = self._nearest_creatures(key, hunt, cx, cy, heading)
                continue
            items = self.items[key]
            m = len(items)
            if m == 0:
                self._near[key] = (np.full(n, np.inf), np.zeros(n), np.zeros(n))
                if key == "food":
                    self._food_value = np.zeros(n)
                continue
            ix = np.fromiter((i.x for i in items), float, m)
            iy = np.fromiter((i.y for i in items), float, m)
            cool = np.fromiter((i.cooldown for i in items), float, m)
            if kernels.ENABLED:   # Compiled, on every core (core/kernels.py)
                best, bdx, bdy, bj = kernels.nearest_points(items, cx, cy, heading, ix, iy, cool, self.cfg, self.width,
                                                        self.height)
            elif getattr(items[0], "radius", 0):
                best, bdx, bdy, bj = self._nearest_shapes(items, cx, cy, ix, iy, cool, heading)
            else:
                best, bdx, bdy, bj = self._nearest_points(cx, cy, ix, iy, cool, heading)
            self._near[key] = (best, bdx, bdy)
            if key == "food":
                self._food_value = self._value_of(s.col("diet")[alive_rows], bj)
            in_view = np.isfinite(best)   # An available item in view
            if key == "food":
                food_seen = in_view
        s.col("food_nearby")[alive_rows] = food_seen
        s.col("near_i")[alive_rows] = rows
        s.col("near_tick")[alive_rows] = self.tick
        return alive

    def _nearest_creatures(self, kind, hunt, cx, cy, heading):
        """(distance², dx, dy) of the nearest prey («prey», seen by the predators) or predator («predator», seen by
        the prey) in view; inf for the others (a creature never sees its own kind). `hunt`: predator or not, for
        the creatures at cx, cy."""
        n = len(cx)
        best, bdx, bdy = np.full(n, np.inf), np.zeros(n), np.zeros(n)
        viewers = np.nonzero(hunt if kind == "prey" else ~hunt)[0]
        targets = np.nonzero(~hunt if kind == "prey" else hunt)[0]
        if len(viewers) and len(targets):
            vx, vy, vh, ix, iy = cx[viewers], cy[viewers], heading[viewers], cx[targets], cy[targets]
            if kernels.ENABLED:
                b, dx, dy, _ = kernels.nearest_creatures(vx, vy, vh, ix, iy, self.cfg, self.width, self.height)
            else:
                b, dx, dy, _ = self._nearest_points(vx, vy, ix, iy, np.zeros(len(targets)), vh)
            best[viewers], bdx[viewers], bdy[viewers] = b, dx, dy
        return best, bdx, bdy

    def creature_points(self, kind):
        """Living prey («prey») or predators («predator») as points (Food objects) for World.nearest: their positions
        at the start of the tick while _update_reference runs, else now."""
        if self._points is not None:
            return self._points[kind]
        want = kind == "predator"
        return [Food(c.x, c.y, 0.0) for c in self.creatures if c.alive and bool(c._spec.get("predator")) == want]

    def nearest_creature(self, creature, kind):
        """Sensors «prey» and «predator» for one creature (World.nearest rules): (distance², dx, dy) or None."""
        if bool(creature._spec.get("predator")) == (kind == "predator"):
            return None   # Never sees its own kind
        return self.nearest(creature, self.creature_points(kind))[0]

    def _value_of(self, diets, food_index):
        """Sensor «valeur» (core/sensors.py): part of the energy of the nearest food in view that each creature
        would get (World.gains: 0 when it sees none, 1 with one kind of food)."""
        seen = food_index >= 0
        gains = self.gains(diets)
        if gains is None:
            return seen.astype(float)
        kinds = np.fromiter((f.kind for f in self.foods), np.int64, len(self.foods))
        rows = np.nonzero(seen)[0]
        value = np.zeros(len(food_index))
        value[rows] = gains[rows, kinds[food_index[rows]]]
        return value

    def _vision_filter(self, dx, dy, d2, heading):
        """In view: within range, and inside the field of view (the angle, arctan2 the costly part, only for the
        pairs within range)."""
        visible = d2 <= self.cfg.VISION_RANGE ** 2
        if self.cfg.VISION_FOV_DEGREES < 360:
            idx = np.nonzero(visible)[0]
            rel = (np.arctan2(dy[idx], dx[idx]) - heading[idx] + math.pi) % (2 * math.pi) - math.pi
            visible[idx[np.abs(rel) > math.radians(self.cfg.VISION_FOV_DEGREES) / 2.0]] = False
        return visible

    def _best_per_creature(self, n, pi, pj, d2, dx, dy):
        """Per creature, the pair of smallest distance² (an exact tie goes to the last item, like nearest()):
        (distance², dx, dy, item index) arrays, distance² = inf and index -1 when it has no pair."""
        best, bdx, bdy, bj = np.full(n, np.inf), np.zeros(n), np.zeros(n), np.full(n, -1, np.int64)
        if len(pi):
            order = np.lexsort((-pj, d2, pi))
            first = order[np.r_[True, pi[order][1:] != pi[order][:-1]]]
            rows = pi[first]
            best[rows], bdx[rows], bdy[rows], bj[rows] = d2[first], dx[first], dy[first], pj[first]
        return best, bdx, bdy, bj

    def _nearest_points(self, cx, cy, ix, iy, cool, heading):
        """Nearest available point item (food, poison) in view of each creature, from the pairs of neighbouring grid
        cells only (core/grid.py): same values as the full creatures × items matrix."""
        pi, pj = near_pairs(cx, cy, ix, iy, self.cfg.VISION_RANGE, self.width, self.height)
        dx = (ix[pj] - cx[pi]) % self.width
        dx = np.where(dx > self.width / 2, dx - self.width, dx)
        dy = (iy[pj] - cy[pi]) % self.height
        dy = np.where(dy > self.height / 2, dy - self.height, dy)
        d2 = dx * dx + dy * dy
        keep = self._vision_filter(dx, dy, d2, heading[pi]) & (cool[pj] <= 0)
        return self._best_per_creature(len(cx), pi[keep], pj[keep], d2[keep], dx[keep], dy[keep])

    def _nearest_shapes(self, items, cx, cy, ix, iy, cool, heading):
        """Nearest available obstacle in view of each creature: distance to its real outline, for the pairs of
        neighbouring grid cells (cells as wide as the range plus the biggest obstacle radius)."""
        range_ = self.cfg.VISION_RANGE
        orad = np.fromiter((o.radius for o in items), float, len(items))
        pi, pj = near_pairs(cx, cy, ix, iy, range_ + float(orad.max()), self.width, self.height)
        dx = (ix[pj] - cx[pi]) % self.width
        dx = np.where(dx > self.width / 2, dx - self.width, dx)
        dy = (iy[pj] - cy[pi]) % self.height
        dy = np.where(dy > self.height / 2, dy - self.height, dy)
        d2 = dx * dx + dy * dy
        # Distance to the outline, only for the creatures in reach of the obstacle's bounding circle
        reach = np.nonzero(d2 <= (range_ + orad[pj]) ** 2)[0]
        reach = reach[np.argsort(pj[reach], kind="stable")]
        bounds = np.searchsorted(pj[reach], np.arange(len(items) + 1)).tolist()
        for j, o in enumerate(items):
            idx = reach[bounds[j]:bounds[j + 1]]
            if idx.size:
                edge = o.edge_distance_np(-dx[idx], -dy[idx])
                d2[idx] = edge * edge
        keep = self._vision_filter(dx, dy, d2, heading[pi]) & (cool[pj] <= 0)
        return self._best_per_creature(len(cx), pi[keep], pj[keep], d2[keep], dx[keep], dy[keep])

    def _update_reference(self):
        """Plain loop version of update(), one creature at a time. Slow: kept as the reference the tests compare to."""

        # Phase 1: Update all creatures. Creatures seen as prey or predators: where they were at the start of the tick
        self._points = {k: self.creature_points(k) for k in ("prey", "predator")}
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
                if not creature.alive or creature.energy + food.energy * self.gain(creature, food) > \
                        creature.energy_max or creature._spec.get("predator"):
                    continue  # Dead, a predator, or the meal would not fit: leaves the food to the others
                dx = torus_delta(creature.x, food.x, self.width)
                dy = torus_delta(creature.y, food.y, self.height)
                distance = math.hypot(dx, dy)
                if distance < creature.radius + self.cfg.FOOD_RADIUS and distance - creature.radius < best_gap:
                    best_gap = distance - creature.radius
                    best = creature

            if best is not None:
                best.eat_food(food.energy * self.gain(best, food))
                # The food comes back after a delay, at a new random place away from the creatures
                food.cooldown = max(1, self.cfg.FOOD_RESPAWN_DELAY)

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
                if distance < creature.radius + self.cfg.FOOD_RADIUS and distance - creature.radius < best_gap:
                    best_gap = distance - creature.radius
                    victim = creature
            if victim is not None:
                victim.hit_by_poison(poison.energy)
                poison.cooldown = max(1, self.cfg.FOOD_RESPAWN_DELAY)

        # Phase 4: predators kill the prey they touch
        hunters = [c for c in self.creatures if c.alive and c._spec.get("predator")]
        for h in hunters:
            h.digest = max(h.digest - 1, 0)
        for prey in self.creatures if hunters else []:
            if not prey.alive or prey._spec.get("predator"):
                continue
            gain = self.cfg.PREDATION_EFFICIENCY * max(prey.energy, 0.0)
            best, best_gap = None, math.inf
            for h in hunters:
                if h.digest > 0 or h.energy + gain > h.energy_max:
                    continue
                distance = math.hypot(torus_delta(h.x, prey.x, self.width), torus_delta(h.y, prey.y, self.height))
                if distance < h.radius + prey.radius and distance - h.radius < best_gap:
                    best_gap, best = distance - h.radius, h
            if best is not None:
                best.eat_prey(prey, gain)
                self.predated += 1

        self._points = None
        self.tick += 1

    def resize_items(self, food_per_screen=None):
        """Applies the food and poison counts (per screen) during the run: new items at free places, or the last ones
        removed. `food_per_screen`: the count of this moment (scarcer food, evolution/continuous.py), else FOOD_COUNT.
        Obstacles are only drawn when the world is created."""
        reach = self.cfg.CREATURE_RADIUS + self.cfg.FOOD_RADIUS
        food = self.cfg.FOOD_COUNT if food_per_screen is None else food_per_screen
        for items, count, energy in ((self.foods, food, self.cfg.FOOD_ENERGY),
                                     (self.poisons, self.cfg.POISON_COUNT, self.cfg.POISON_ENERGY)):
            target = self._count(count)
            del items[target:]
            while len(items) < target:
                item = Food(*self._free_position(reach), energy, self._kind_of(len(items)) if items is self.foods
                            else 0)
                if not self._place_item(item):
                    item.cooldown = 1   # No room away from the creatures now: it will try again next tick
                items.append(item)
            for item in items:
                item.energy = energy

    def add_creature(self, brain, profile, energy=None, near=None, **lineage):
        """Adds a creature at a random free place, or close to `near` = (x, y) (a newborn next to its parent).
        `lineage`: uid, parent_id, birth_tick, lineage_gen, size (see Creature)."""
        margin = self.cfg.CREATURE_RADIUS * lineage.get("size", 1.0)
        x, y = self._free_position(margin) if near is None else self._free_near(*near, margin)
        angle = self.rng.uniform(-math.pi, math.pi)
        creature = Creature(x, y, angle, self.cfg.INITIAL_ENERGY if energy is None else energy, brain, profile,
                            cfg=self.cfg, store=self.store, **lineage)
        assert creature._i == len(self._creatures), "store rows out of step with World.creatures"
        self._creatures.append(creature)
        return creature

    def _free_near(self, x, y, margin=None):
        """Free position a few radii from (x, y); a random free place if the surroundings are blocked."""
        margin = self.cfg.CREATURE_RADIUS if margin is None else margin
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
            brain.randomize(self.rng, self.cfg.NN_INIT_STD)
            self.add_creature(brain, profile)

    def nearest(self, creature, items, with_item=False):
        """Nearest available item in the creature's field of view: ((distance², dx, dy) or None, in_view).
        In view = within the vision range AND within VISION_FOV_DEGREES centred on the heading.
        in_view says whether an available item is in view. Also used by the debug overlay.
        with_item=True: (found, in_view, the item or None)."""
        best = best_item = None
        range2 = self.cfg.VISION_RANGE ** 2
        best_distance2 = range2
        in_view = False
        all_around = self.cfg.VISION_FOV_DEGREES >= 360
        half_fov = math.radians(self.cfg.VISION_FOV_DEGREES) / 2.0
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
            if item.cooldown > 0:
                continue  # Not available yet: the network cannot see it
            in_view = True
            if distance2 <= best_distance2:
                best_distance2 = distance2
                best, best_item = (distance2, dx, dy), item
        return (best, in_view, best_item) if with_item else (best, in_view)

    def direction(self, creature, found):
        """Network inputs for one kind of target: [distance, relative angle]. Nothing in view: maximum distance,
        ahead."""
        if found is None:
            return [1.0, 0.0]
        distance2, dx, dy = found
        distance = math.sqrt(distance2) / self.cfg.VISION_RANGE
        angle = normalize_angle(math.atan2(dy, dx) - creature.angle) / math.pi
        return [distance, angle]

    def sense(self, creature):
        """Network inputs: the sensors of the creature's profile (brain/profiles.py), then its memory cells.
        Uses what sense_all found for this tick when it is there, else looks up the nearest items itself
        (the interface calls it for the selected creature). The nearest food is always looked up: it feeds the
        `food_nearby` metric."""
        if creature._s is self.store and creature._s.near_tick[creature._i] == self.tick == \
                getattr(self, "_near_tick", -2):
            i = int(creature._s.near_i[creature._i])
            ctx = {k: (float(d2[i]), float(dx[i]), float(dy[i])) if np.isfinite(d2[i]) else None
                   for k, (d2, dx, dy) in self._near.items()}
            ctx["food_value"] = float(self._food_value[i])
        else:
            food, in_view = self.nearest(creature, self.foods)
            creature.food_nearby = in_view  # An available food in view
            ctx = {"food": food}
        values = []
        for key in PROFILES[creature.profile]["sensors"]:
            values += SENSORS[key].fn(self, creature, ctx)
        return values + creature.memory

import math

import numpy as np

import config
from core.physics import normalize_angle
from brain.profiles import PROFILE_INDEX, PROFILES


class CreatureStore:
    """The numeric state of a world's creatures, one numpy array per field, one row per creature (row i = the i-th
    creature of World.creatures). The tick works on whole columns (core/batch.py, World.update) instead of reading
    and writing each creature object; a Creature reads and writes its own row through the fields below."""

    FLOATS = ("x", "y", "angle", "speed", "energy", "speed_sum", "blind_speed_sum", "blind_turn_sum", "last_turn",
              "size", "body", "radius", "energy_max", "base_cost", "move_cost", "diet")
    INTS = ("age", "unseen_ticks", "blind_ticks", "uid", "near_i", "near_tick", "species")
    BOOLS = ("alive", "touching", "food_nearby")

    def __init__(self, capacity=16):
        self.n = 0
        for names, dtype in ((self.FLOATS, float), (self.INTS, np.int64), (self.BOOLS, bool)):
            for name in names:
                setattr(self, name, np.zeros(capacity, dtype))

    def fields(self):
        return self.FLOATS + self.INTS + self.BOOLS

    def add(self):
        """A new row at the end; returns its index. Arrays grow by doubling (views taken before are then stale)."""
        if self.n == len(self.x):
            for name in self.fields():
                old = getattr(self, name)
                new = np.zeros(2 * len(old), old.dtype)
                new[:self.n] = old[:self.n]
                setattr(self, name, new)
        self.n += 1
        return self.n - 1

    def keep(self, rows):
        """Keeps the rows `rows` (indices, in this order) and drops the others."""
        for name in self.fields():
            col = getattr(self, name)
            col[:len(rows)] = col[rows]
        self.n = len(rows)

    def col(self, name):
        """The live rows of a field (a view: writing to it writes the creatures)."""
        return getattr(self, name)[:self.n]


class _Field:
    """Attribute of a Creature stored in its row of the CreatureStore (read back as a Python value)."""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return getattr(obj._s, self.name)[obj._i].item()

    def __set__(self, obj, value):
        getattr(obj._s, self.name)[obj._i] = value


class Creature:
    # Numeric state, kept in the world's CreatureStore (see there)
    x = _Field()
    y = _Field()
    angle = _Field()
    speed = _Field()            # Current speed, decided by the network at each tick
    energy = _Field()
    speed_sum = _Field()        # Sum of its speed over its life: mean speed = speed_sum / age
    blind_speed_sum = _Field()
    blind_turn_sum = _Field()
    last_turn = _Field()        # Turn output of the last tick (exploration measures)
    size = _Field()
    body = _Field()
    radius = _Field()
    energy_max = _Field()
    base_cost = _Field()
    move_cost = _Field()
    diet = _Field()             # Diet gene in [0, 1]: which kind of food feeds it (FOOD_TYPES = 2, config.py)
    age = _Field()
    unseen_ticks = _Field()     # Ticks since it last saw an available food (sensor «faim»)
    blind_ticks = _Field()
    uid = _Field()
    alive = _Field()
    touching = _Field()         # Pressed against an obstacle at the last tick (a sensor of some profiles)
    food_nearby = _Field()      # An available food in view (set by World.sense_all / World.sense each tick)

    def __init__(self, x, y, angle, energy, brain, profile, uid=0, parent_id=None, birth_tick=0, lineage_gen=0,
                 size=1.0, diet=0.5, cfg=config, store=None):
        """`store`: the CreatureStore of the world it lives in (World.add_creature); its own one-row store if None."""
        self._s = CreatureStore(1) if store is None else store
        self._i = self._s.add()
        self.cfg = cfg   # Settings in force (see self.cfg.Settings)
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.speed = 0.0
        self.energy = energy
        self.brain = brain
        self.profile = profile   # Name of its network profile (species), see brain/profiles.py
        self._spec = PROFILES[profile]
        self.alive = True
        self.set_size(size)
        self.diet = diet
        self.death_cause = None   # "faim" or "vieillesse" (poison kills through hunger)
        # Lineage (continuous evolution): identity, parent, birth, depth of the lineage (0 = random founder)
        self.uid = uid
        self.parent_id = parent_id
        self.birth_tick = birth_tick
        self.lineage_gen = lineage_gen
        self.last_birth_age = None   # Age at its last birth (cooldown)
        self.children = 0
        self.food_eaten = 0
        self.poison_hits = 0
        self.obstacle_ticks = 0   # Ticks spent pressed against an obstacle
        self.touching = False
        self.memory = [0.0] * PROFILES[profile]["memory"]   # Extra network outputs, fed back as inputs at the next tick
        self.age = 0
        # Exploration metrics: what the creature does when it sees no food
        self.food_nearby = True
        self.blind_ticks = 0
        self.blind_speed_sum = 0.0
        self.blind_turn_sum = 0.0
        self.last_turn = 0.0
        self.unseen_ticks = 0
        self.speed_sum = 0.0
        self._s.near_tick[self._i] = -1   # Not seen by World.sense_all yet
        self._s.species[self._i] = PROFILE_INDEX[profile]

    def set_size(self, size):
        """Body gene. `body` is the size that acts (1 unless SIZE_MODE is "actif"); everything the body changes is
        computed here once: contact radius, energy reserve, base and moving costs."""
        self.size = size
        self.body = size if self.cfg.SIZE_MODE == "actif" else 1.0
        self.radius = self.cfg.CREATURE_RADIUS * self.body
        self.energy_max = self.cfg.ENERGY_MAX * self.body
        self.base_cost = self.cfg.ENERGY_BASE_COST * self.body ** self.cfg.SIZE_BASE_EXPONENT
        self.move_cost = self.cfg.ENERGY_MOVE_COST * self.body

    def update(self, inputs, world_width, world_height):
        if not self.alive:
            return
        if self.energy <= 0:
            self.alive = False
            self.death_cause = "faim"
            return

        # The network decides: outputs are in [-1, 1] (tanh)
        outputs = self.brain.forward(inputs)
        turn = float(outputs[0])
        if self._spec["speed_output"]:
            speed_command = float(outputs[1])
            first_memory = 2
        else:
            speed_command = self._spec["fixed_speed"]   # This species cannot change its speed
            first_memory = 1
        if len(outputs) > first_memory:
            self.memory = [float(v) for v in outputs[first_memory:]]

        # Inertia: the network asks for a target speed, the speed moves toward it with limited acceleration
        target_speed = (speed_command + 1.0) / 2.0 * self.cfg.CREATURE_MAX_SPEED
        change = max(-self.cfg.CREATURE_ACCELERATION, min(self.cfg.CREATURE_ACCELERATION, target_speed - self.speed))
        self.speed += change

        # The faster the creature goes, the less it can turn
        cfg = self.cfg
        max_turn = cfg.CREATURE_MAX_TURN * (1.0 - cfg.TURN_SPEED_PENALTY * self.speed / cfg.CREATURE_MAX_SPEED)
        self.angle = normalize_angle(self.angle + turn * max_turn)

        # Blind = no available food in view (food that was eaten is somewhere else when it comes back)
        self.last_turn = turn
        if not self.food_nearby:
            self.blind_ticks += 1
            self.blind_speed_sum += self.speed
            self.blind_turn_sum += abs(turn)
            self.unseen_ticks += 1
        else:
            self.unseen_ticks = 0

        # Update the creature's position based on its speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Keep the creature within the bounds of the world
        self.x  %= world_width
        self.y  %= world_height

        # Moving costs energy: base cost + cost proportional to speed
        self.energy -= self.base_cost + self.move_cost * self.speed

        self.age += 1 #Added age increment to track how long the creature has been alive
        self.speed_sum += self.speed

    def hit_by_poison(self, amount):
        """Touching a poison costs energy. The creature dies at its next update if the energy reaches 0."""
        if not self.alive:
            return
        self.energy -= amount
        self.poison_hits += 1

    def eat_food(self,amount):
        if not self.alive:
            return
        self.energy = min(self.energy + amount, self.energy_max)  # The excess is lost
        self.food_eaten += 1


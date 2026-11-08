"""Sensors: what a creature can feed into its network.

Adding a sensor = one entry in SENSORS. Nothing else to touch: profiles pick sensors by key (brain/profiles.py),
World.sense_all precomputes the nearest items of the kinds listed in `needs`, and the interface reads the labels.

Each sensor has two forms that must give the same values:
- fn(world, creature, ctx) → list of floats, one per label. One creature (the interface, the reference loop).
  `ctx`: {item kind: (distance², dx, dy) or None}, what World.sense_all found for this tick.
- vec(world, group) → array (n, number of labels). All the creatures of a species at once (World.update).
  `group` holds their attributes as arrays (see core/batch.py: x, y, angle, speed, energy, energy_max, unseen,
  uid, touching) and `near`: {item kind: (distance², dx, dy) arrays, distance² = inf when nothing is seen}.
"""
import math
from collections import namedtuple

import numpy as np

import config

Sensor = namedtuple("Sensor", ["labels", "fn", "needs", "vec"])


def nearest_of(kind):
    """Sensor: [distance, relative angle] to the nearest available item of `kind` in view (1, 0 = nothing seen)."""
    def fn(world, c, ctx):
        if kind not in ctx:   # Not precomputed (sense() called outside a tick, e.g. by the interface)
            ctx[kind] = world.nearest(c, world.items[kind])[0]
        return world.direction(c, ctx[kind])

    def vec(world, g):
        d2, dx, dy = g["near"][kind]
        seen = np.isfinite(d2)
        distance = np.where(seen, np.sqrt(np.where(seen, d2, 0.0)) / config.VISION_RANGE, 1.0)
        rel = (np.arctan2(dy, dx) - g["angle"] + math.pi) % (2 * math.pi) - math.pi
        return np.stack([distance, np.where(seen, rel / math.pi, 0.0)], axis=1)
    return fn, vec


def _energy(world, c, ctx):
    return [max(0.0, min(c.energy / c.energy_max, 1.0))]   # Share of its own reserve (depends on its size)


def _energy_v(world, g):
    return np.clip(g["energy"] / g["energy_max"], 0.0, 1.0)[:, None]


def _speed(world, c, ctx):
    return [c.speed / config.CREATURE_MAX_SPEED]


def _speed_v(world, g):
    return (g["speed"] / config.CREATURE_MAX_SPEED)[:, None]


def _can_eat(world, c, ctx):
    # 1.0 if a meal would fit (same rule as the food phase), else 0.0
    return [1.0 if c.energy + config.FOOD_ENERGY <= c.energy_max else 0.0]


def _can_eat_v(world, g):
    return (g["energy"] + config.FOOD_ENERGY <= g["energy_max"]).astype(float)[:, None]


def _compass(world, c, ctx):
    return [math.cos(c.angle), math.sin(c.angle)]   # Heading in the world (the creature has no other way to know it)


def _compass_v(world, g):
    return np.stack([np.cos(g["angle"]), np.sin(g["angle"])], axis=1)


def _touch(world, c, ctx):
    return [1.0 if c.touching else 0.0]   # Pushed against an obstacle at the last tick


def _touch_v(world, g):
    return g["touching"].astype(float)[:, None]


def _hunger(world, c, ctx):
    # Time since it last saw an available food, 0 → 1 over HUNGER_SCALE ticks. The only input that keeps changing
    # when nothing is in view: lets evolution find «the longer I see nothing, the more I move»
    return [min(1.0, c.unseen_ticks / config.HUNGER_SCALE)]


def _hunger_v(world, g):
    return np.minimum(1.0, g["unseen"] / config.HUNGER_SCALE)[:, None]


def _noise(world, c, ctx):
    # A new value in [-1, 1] at each tick, different for each creature: lets a network wander at random.
    # Computed from (creature, tick), not drawn from the world's random generator: looking at a creature in the
    # interface never changes the simulation
    v = math.sin(c.uid * 12.9898 + world.tick * 78.233) * 43758.5453
    return [2.0 * (v - math.floor(v)) - 1.0]


def _noise_v(world, g):
    v = np.sin(g["uid"] * 12.9898 + world.tick * 78.233) * 43758.5453
    return (2.0 * (v - np.floor(v)) - 1.0)[:, None]


def _sensor(labels, pair, needs=()):
    fn, vec = pair
    return Sensor(labels, fn, set(needs), vec)


SENSORS = {
    "food": _sensor(["Distance", "Angle"], nearest_of("food"), {"food"}),
    "energy": _sensor(["Énergie"], (_energy, _energy_v)),
    "speed": _sensor(["Vitesse"], (_speed, _speed_v)),
    "can_eat": _sensor(["Peut manger"], (_can_eat, _can_eat_v)),
    "poison": _sensor(["Dist. poison", "Angle poison"], nearest_of("poison"), {"poison"}),
    "obstacle": _sensor(["Dist. obstacle", "Angle obstacle"], nearest_of("obstacle"), {"obstacle"}),
    "compass": _sensor(["Cap cos", "Cap sin"], (_compass, _compass_v)),
    "touch": _sensor(["Contact"], (_touch, _touch_v)),
    "hunger": _sensor(["Faim"], (_hunger, _hunger_v)),
    "noise": _sensor(["Bruit"], (_noise, _noise_v)),
}

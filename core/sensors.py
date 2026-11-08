"""Sensors: what a creature can feed into its network.

Adding a sensor = one entry in SENSORS. Nothing else to touch: profiles pick sensors by key (brain/profiles.py),
World.sense_all precomputes the nearest items of the kinds listed in `needs`, and the interface reads the labels.

A sensor function receives (world, creature, ctx) and returns a list of floats, one per label.
`ctx` holds what World.sense_all found for this tick: {item kind: (distance², dx, dy) or None}.
"""
import math
from collections import namedtuple

import config

Sensor = namedtuple("Sensor", ["labels", "fn", "needs"])


def nearest_of(kind):
    """Sensor: [distance, relative angle] to the nearest available item of `kind` in view (1, 0 = nothing seen)."""
    def fn(world, c, ctx):
        if kind not in ctx:   # Not precomputed (sense() called outside a tick, e.g. by the interface)
            ctx[kind] = world.nearest(c, world.items[kind])[0]
        return world.direction(c, ctx[kind])
    return fn


def _energy(world, c, ctx):
    return [max(0.0, min(c.energy / config.ENERGY_INPUT_MAX, 1.0))]


def _speed(world, c, ctx):
    return [c.speed / config.CREATURE_MAX_SPEED]


def _can_eat(world, c, ctx):
    # 1.0 if a meal would fit (same rule as the food phase), else 0.0
    return [1.0 if c.energy + config.FOOD_ENERGY <= config.ENERGY_MAX else 0.0]


def _compass(world, c, ctx):
    return [math.cos(c.angle), math.sin(c.angle)]   # Heading in the world (the creature has no other way to know it)


def _touch(world, c, ctx):
    return [1.0 if c.touching else 0.0]   # Pushed against an obstacle at the last tick


SENSORS = {
    "food": Sensor(["Distance", "Angle"], nearest_of("food"), {"food"}),
    "energy": Sensor(["Énergie"], _energy, set()),
    "speed": Sensor(["Vitesse"], _speed, set()),
    "can_eat": Sensor(["Peut manger"], _can_eat, set()),
    "poison": Sensor(["Dist. poison", "Angle poison"], nearest_of("poison"), {"poison"}),
    "obstacle": Sensor(["Dist. obstacle", "Angle obstacle"], nearest_of("obstacle"), {"obstacle"}),
    "compass": Sensor(["Cap cos", "Cap sin"], _compass, set()),
    "touch": Sensor(["Contact"], _touch, set()),
}

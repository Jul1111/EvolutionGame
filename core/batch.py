"""Phase 1 of a tick for all the creatures at once: sensors, networks, movement, energy.

Same rules as Creature.update + World.sense applied one creature at a time (World._update_reference, checked by
tests/test_world.py), but computed with numpy, one species at a time for the networks. This is where most of the
simulation time went (a Python call per creature per tick).
"""
import math

import numpy as np

import config
from brain.profiles import PROFILES
from core.sensors import SENSORS


def _arr(cs, attr, dtype=float):
    return np.fromiter((getattr(c, attr) for c in cs), dtype, len(cs))


def _group(cs, rows, near):
    """Attributes of the creatures `cs` (rows = their index in the arrays of `near`) for the vectorized sensors."""
    return {"angle": _arr(cs, "angle"), "speed": _arr(cs, "speed"), "energy": _arr(cs, "energy"),
            "energy_max": _arr(cs, "energy_max"), "unseen": _arr(cs, "unseen_ticks"), "uid": _arr(cs, "uid"),
            "touching": _arr(cs, "touching", bool),
            "near": {k: (d2[rows], dx[rows], dy[rows]) for k, (d2, dx, dy) in near.items()}}


_stacks = {}   # species → (ids of the brains, stacked weights): rebuilt only when the members change


def _weights(name, cs):
    key = tuple(map(id, (c.brain for c in cs)))
    cached = _stacks.get(name)
    if cached is None or cached[0] != key:
        brains = [c.brain for c in cs]
        cached = (key, np.stack([b.w1 for b in brains]), np.stack([b.b1 for b in brains]),
                  np.stack([b.w2 for b in brains]), np.stack([b.b2 for b in brains]))
        _stacks[name] = cached
    return cached[1:]


def _forward(cs, inputs):
    """Outputs of the networks of `cs` (same species, same shapes) for the rows of `inputs`."""
    if PROFILES[cs[0].profile].get("brain") == "scripted":
        return np.array([c.brain.forward(row) for c, row in zip(cs, inputs)])
    w1, b1, w2, b2 = _weights(cs[0].profile, cs)
    first = np.tanh(np.einsum("nji,ni->nj", w1, inputs) + b1)
    if cs[0].brain.direct:
        return first
    return np.tanh(np.einsum("noj,nj->no", w2, first) + b2)


def decide_and_move(world, alive, near):
    """`alive`: the creatures alive at the start of the tick, in the order of the arrays of `near`
    ({kind: (distance², dx, dy)}, from World.sense_all). Creatures with no energy left die here, the others decide
    and move. Collisions, food and poison come after (World.update)."""
    starving = [c for c in alive if c.energy <= 0]
    for c in starving:
        c.alive = False
        c.death_cause = "faim"
    rows_of = {id(c): i for i, c in enumerate(alive)}
    by_species = {}
    for c in alive:
        if c.alive:
            by_species.setdefault(c.profile, []).append(c)
    for name, cs in by_species.items():
        spec = PROFILES[name]
        rows = np.fromiter((rows_of[id(c)] for c in cs), int, len(cs))
        g = _group(cs, rows, near)
        parts = [SENSORS[key].vec(world, g) for key in spec["sensors"]]
        if spec["memory"]:
            parts.append(np.array([c.memory for c in cs], dtype=float))
        out = _forward(cs, np.concatenate(parts, axis=1))
        _move(world, cs, g, out, spec, near["food"][0][rows])


def _move(world, cs, g, out, spec, food_d2):
    turn = out[:, 0]
    if spec["speed_output"]:
        command, first_memory = out[:, 1], 2
    else:
        command, first_memory = np.full(len(cs), float(spec["fixed_speed"])), 1
    max_speed = config.CREATURE_MAX_SPEED
    target = (command + 1.0) / 2.0 * max_speed
    speed = g["speed"] + np.clip(target - g["speed"], -config.CREATURE_ACCELERATION, config.CREATURE_ACCELERATION)
    max_turn = config.CREATURE_MAX_TURN * (1.0 - config.TURN_SPEED_PENALTY * speed / max_speed)
    angle = (g["angle"] + turn * max_turn + math.pi) % (2 * math.pi) - math.pi
    xs = (np.fromiter((c.x for c in cs), float, len(cs)) + speed * np.cos(angle)) % world.width
    ys = (np.fromiter((c.y for c in cs), float, len(cs)) + speed * np.sin(angle)) % world.height
    cost = np.fromiter((c.base_cost for c in cs), float, len(cs)) + \
        np.fromiter((c.move_cost for c in cs), float, len(cs)) * speed
    blind = ~np.isfinite(food_d2)   # No available food in view (same as Creature.food_nearby)
    # Exploration measures of the whole population (read by evolution/continuous.py)
    world.blind_ticks += int(blind.sum())
    world.blind_speed += float(speed[blind].sum())
    world.blind_turn += float(np.abs(turn[blind]).sum())
    memory = out[:, first_memory:].tolist() if out.shape[1] > first_memory else None
    for i, (c, t, s, a, x, y, e, b) in enumerate(zip(cs, turn.tolist(), speed.tolist(), angle.tolist(), xs.tolist(),
                                                      ys.tolist(), cost.tolist(), blind.tolist())):
        c.speed, c.angle, c.x, c.y, c.last_turn = s, a, x, y, t
        c.energy -= e
        c.age += 1
        c.speed_sum += s
        if memory is not None:
            c.memory = memory[i]
        if b:
            c.blind_ticks += 1
            c.blind_speed_sum += s
            c.blind_turn_sum += abs(t)
            c.unseen_ticks += 1
        else:
            c.unseen_ticks = 0

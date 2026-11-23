"""Phase 1 of a tick for all the creatures at once: sensors, networks, movement, energy.

Same rules as Creature.update + World.sense applied one creature at a time (World._update_reference, checked by
tests/test_world.py), but computed with numpy, one species at a time for the networks. This is where most of the
simulation time went (a Python call per creature per tick).
"""
import math
from typing import Any

import numpy as np

from brain.profiles import PROFILE_NAMES, PROFILES
from core.sensors import SENSORS


def _group(world, store, rows, near_rows, near):
    """Attributes of the creatures at `rows` of the store (near_rows = their index in the arrays of `near`) for the
    vectorized sensors."""
    return {"angle": store.angle[rows], "speed": store.speed[rows], "energy": store.energy[rows],
            "energy_max": store.energy_max[rows], "unseen": store.unseen_ticks[rows].astype(float),
            "uid": store.uid[rows].astype(float), "touching": store.touching[rows],
            "food_value": world._food_value[near_rows],
            "near": {k: (d2[near_rows], dx[near_rows], dy[near_rows]) for k, (d2, dx, dy) in near.items()}}


_stacks: dict[str, Any] = {}   # species → (the brains, their stacked weights w1, b1, w2, b2)


def _weights(name, cs):
    """Stacked weights of the brains of `cs`, updated from the last tick's stack: the creatures that were already
    there are taken from it, only the newborns are stacked (a full np.stack each tick cost ~1 ms)."""
    brains = tuple(c.brain for c in cs)
    cached = _stacks.get(name)
    if cached is not None and cached[0] == brains:   # Tuple equality: identity first, so no array comparison
        return cached[1:]
    old = cached[0] if cached is not None else ()
    # The old stack keeps its brains alive, so an id found in it is that very brain (no reused id)
    pos = {id(b): i for i, b in enumerate(old)}
    index = [pos.get(id(b), -1) for b in brains]
    new = [b for b, i in zip(brains, index) if i < 0]
    take, j = [], len(old)
    for i in index:
        if i < 0:
            i, j = j, j + 1
        take.append(i)
    stacks = []
    for k, attr in enumerate(("w1", "b1", "w2", "b2")):
        parts = ([cached[1 + k]] if old else []) + ([np.stack([getattr(b, attr) for b in new])] if new else [])
        stack = np.concatenate(parts) if len(parts) > 1 else parts[0]
        stacks.append(stack if len(stack) == len(take) and take == list(range(len(take))) else stack[take])
    cached = (brains, *stacks)
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


def decide_and_move(world, alive, alive_rows, near):
    """`alive`: the creatures alive at the start of the tick, in the order of the arrays of `near`
    ({kind: (distance², dx, dy)}, from World.sense_all); `alive_rows`: their rows in world.store. Creatures with no
    energy left die here, the others decide and move. Collisions, food and poison come after (World.update)."""
    store = world.store
    rows = np.arange(store.n)[alive_rows]           # Store row of each creature of `alive`
    starving = store.energy[rows] <= 0
    for k in np.nonzero(starving)[0].tolist():
        alive[k].alive = False
        alive[k].death_cause = "faim"
    species = store.species[rows]
    living_species = species[~starving]
    _, first = np.unique(living_species, return_index=True)
    for code in living_species[np.sort(first)].tolist():   # Species in order of appearance
        name = PROFILE_NAMES[code]
        spec = PROFILES[name]
        near_rows = np.nonzero((species == code) & ~starving)[0]   # Index in `alive` and in the arrays of `near`
        cs = [alive[k] for k in near_rows.tolist()]
        g = _group(world, store, rows[near_rows], near_rows, near)
        parts = [SENSORS[key].vec(world, g) for key in spec["sensors"]]
        if spec["memory"]:
            parts.append(np.array([c.memory for c in cs], dtype=float))
        out = _forward(cs, np.concatenate(parts, axis=1))
        _move(world, cs, rows[near_rows], g, out, spec, near["food"][0][near_rows])


def _move(world, cs, rows, g, out, spec, food_d2):
    s = world.store
    turn = out[:, 0]
    if spec["speed_output"]:
        command, first_memory = out[:, 1], 2
    else:
        command, first_memory = np.full(len(cs), float(spec["fixed_speed"])), 1
    max_speed = world.cfg.CREATURE_MAX_SPEED
    target = (command + 1.0) / 2.0 * max_speed
    speed = g["speed"] + np.clip(target - g["speed"], -world.cfg.CREATURE_ACCELERATION, world.cfg.CREATURE_ACCELERATION)
    max_turn = world.cfg.CREATURE_MAX_TURN * (1.0 - world.cfg.TURN_SPEED_PENALTY * speed / max_speed)
    angle = (g["angle"] + turn * max_turn + math.pi) % (2 * math.pi) - math.pi
    s.x[rows] = (s.x[rows] + speed * np.cos(angle)) % world.width
    s.y[rows] = (s.y[rows] + speed * np.sin(angle)) % world.height
    s.energy[rows] -= s.base_cost[rows] + s.move_cost[rows] * speed
    s.speed[rows], s.angle[rows], s.last_turn[rows] = speed, angle, turn
    s.age[rows] += 1
    s.speed_sum[rows] += speed
    blind = ~np.isfinite(food_d2)   # No available food in view (same as Creature.food_nearby)
    # Exploration measures of the whole population (read by evolution/continuous.py); predators eat no food: left out
    if not spec.get("predator"):
        world.blind_ticks += int(blind.sum())
        world.blind_speed += float(speed[blind].sum())
        world.blind_turn += float(np.abs(turn[blind]).sum())
    if world.hunting:
        _hunt_measures(world, g, spec, speed, turn)
    b = rows[blind]
    s.blind_ticks[b] += 1
    s.blind_speed_sum[b] += speed[blind]
    s.blind_turn_sum[b] += np.abs(turn[blind])
    s.unseen_ticks[b] += 1
    s.unseen_ticks[rows[~blind]] = 0
    if out.shape[1] > first_memory:
        for c, m in zip(cs, out[:, first_memory:].tolist()):
            c.memory = m


def _hunt_measures(world, g, spec, speed, turn):
    """Hunting measures (World.hunt): for predators, what they do with a prey in view; for prey, with a predator in
    view. Toward = turn × side of the target (> 0: turns toward it, < 0: turns away)."""
    key = "prey" if spec.get("predator") else "predator"
    d2, dx, dy = g["near"][key]
    seen = np.isfinite(d2)
    rel = (np.arctan2(dy[seen], dx[seen]) - g["angle"][seen] + math.pi) % (2 * math.pi) - math.pi
    h = world.hunt[key]
    h["ticks"] += len(seen)
    h["seen"] += int(seen.sum())
    h["speed_seen"] += float(speed[seen].sum())
    h["speed_unseen"] += float(speed[~seen].sum())
    h["toward"] += float((turn[seen] * np.sign(rel)).sum())

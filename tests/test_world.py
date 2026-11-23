import math
import random

import config
from core.physics import torus_delta
from core.world import World
from brain.profiles import input_labels


def _world(seed, profiles=("complet", "prudent", "chasseur")):
    w = World(random.Random(seed))
    for p in profiles:
        w.add_population(p, 30)
    return w


def test_fast_update_matches_reference():
    """World.update (numpy) and World._update_reference (plain loops) apply the same rules."""
    config.POISON_COUNT = 8
    config.OBSTACLE_COUNT = 10
    for seed in (1, 2):
        fast, ref = _world(seed), _world(seed)
        for _ in range(300):
            fast.update()
            ref._update_reference()
        for a, b in zip(fast.creatures, ref.creatures):
            assert a.alive == b.alive
            assert a.food_eaten == b.food_eaten and a.poison_hits == b.poison_hits
            assert abs(torus_delta(a.x, b.x, fast.width)) < 1e-6 and abs(torus_delta(a.y, b.y, fast.height)) < 1e-6
        assert sum(c.food_eaten for c in fast.creatures) > 0   # The test must exercise the food phase


def test_no_creature_inside_an_obstacle():
    config.OBSTACLE_COUNT = 15
    w = _world(3)
    for _ in range(500):
        w.update()
        for c in w.creatures:
            if not c.alive:
                continue
            for o in w.obstacles:
                dx, dy = torus_delta(o.x, c.x, w.width), torus_delta(o.y, c.y, w.height)
                if math.hypot(dx, dy) <= o.radius + config.CREATURE_RADIUS:
                    assert o.edge_distance(dx, dy) >= config.CREATURE_RADIUS - 1e-6


def test_sense_length_matches_profile():
    from brain.profiles import PROFILES
    w = _world(4, profiles=tuple(PROFILES))
    w.update()
    for c in w.creatures:
        assert len(w.sense(c)) == len(input_labels(c.profile))


def test_food_and_poison_never_reappear_on_or_near_a_creature():
    config.FOOD_RESPAWN_DELAY = 5
    config.POISON_COUNT = 10
    w = _world(5)
    for _ in range(600):
        before = {id(f): f.cooldown for f in w.foods + w.poisons}
        w.update()
        for f in w.foods + w.poisons:
            if before[id(f)] == 1 and f.cooldown == 0:   # Came back during this tick: check where
                for c in w.creatures:
                    if c.alive:
                        d = math.hypot(torus_delta(c.x, f.x, w.width), torus_delta(c.y, f.y, w.height))
                        assert d >= c.radius + config.FOOD_RADIUS + config.SPAWN_CLEARANCE - 1e-9
    assert w.eaten > 0 and w.poisoned > 0


def test_hunger_and_noise_sensors():
    from core.sensors import SENSORS
    w = _world(6, profiles=("complet_faim",))
    c = w.creatures[0]
    c.unseen_ticks = config.HUNGER_SCALE // 2
    assert abs(SENSORS["hunger"].fn(w, c, {})[0] - 0.5) < 1e-9
    c.unseen_ticks = 10 * config.HUNGER_SCALE
    assert SENSORS["hunger"].fn(w, c, {})[0] == 1.0
    # Noise: in [-1, 1], changes with the tick and the creature, and never touches the world's random generator
    state = w.rng.getstate()
    values = []
    for t in range(50):
        w.tick = t
        values.append(SENSORS["noise"].fn(w, c, {})[0])
    assert w.rng.getstate() == state
    assert all(-1 <= v <= 1 for v in values) and len(set(values)) == 50
    w.tick = 3
    assert SENSORS["noise"].fn(w, c, {})[0] == values[3]


def test_unseen_ticks_count_and_reset():
    w = _world(7, profiles=("complet_faim",))
    for _ in range(300):
        w.update()
    for c in w.creatures:
        if c.alive:
            assert c.unseen_ticks == 0 if c.food_nearby else c.unseen_ticks >= 1


def test_batched_update_matches_reference_for_every_species():
    """core/batch.py (all creatures at once) against Creature.update one by one, for every profile: memory, noise,
    hunger, fixed speed and the scripted brain included."""
    from brain.profiles import PROFILES
    config.POISON_COUNT = 8
    fast, ref = _world(11, profiles=tuple(PROFILES)), _world(11, profiles=tuple(PROFILES))
    for _ in range(200):
        fast.update()
        ref._update_reference()
    # The two paths add the same numbers in a different order (matrix products vs one creature at a time), and that
    # order depends on the linear algebra library: after 200 ticks positions differ by ~4e-8 on macOS, ~3e-5 on the
    # Linux runner. A logic error (speed, sensor, collision) moves a creature by about a pixel within a few ticks.
    tol = 1e-3
    for a, b in zip(fast.creatures, ref.creatures):
        assert a.alive == b.alive and a.food_eaten == b.food_eaten and a.unseen_ticks == b.unseen_ticks
        assert abs(torus_delta(a.x, b.x, fast.width)) < tol and abs(torus_delta(a.y, b.y, fast.height)) < tol
        assert abs(a.energy - b.energy) < tol
        assert all(abs(m - n) < tol for m, n in zip(a.memory, b.memory))


def test_derived_config_follows_its_sources():
    """WORLD_WIDTH and the like are computed when read: nothing to refresh after a setting changed."""
    config.WORLD_SCALE = 2
    assert config.WORLD_WIDTH == 2 * config.SCREEN_WIDTH and config.WORLD_HEIGHT == 2 * config.SCREEN_HEIGHT
    config.ENERGY_MAX = 123.0
    assert config.ENERGY_INPUT_MAX == 123.0
    assert "WORLD_WIDTH" not in dir(config)   # Not a module attribute: it cannot be set by mistake or saved


def test_compiled_kernels_match_numpy(monkeypatch):
    """core/kernels.py (numba) and the numpy code of World give exactly the same run: vision of food, poison and
    every obstacle shape, field of view or all around, contacts."""
    import pytest

    from core import kernels
    from evolution.continuous import ContinuousSimulation
    if not kernels.ENABLED:
        pytest.skip("numba absent")
    for fov in (60, 360):
        cfg = config.Settings(VISION_FOV_DEGREES=fov, OBSTACLE_COUNT=15, POISON_COUNT=12, WORLD_SCALE=2,
                              ACTIVE_PROFILES=["complet", "scripte"])
        runs = []
        for enabled in (True, False):
            monkeypatch.setattr(kernels, "ENABLED", enabled)
            sim = ContinuousSimulation(random.Random(5), cfg=cfg)
            sim.run(400)
            runs.append([(c.uid, c.x, c.y, c.energy, c.food_eaten, c.poison_hits, c.unseen_ticks)
                         for c in sim.world.creatures] + [(f.x, f.y, f.cooldown) for f in sim.world.foods])
        assert runs[0] == runs[1]
        assert sum(r[4] for r in runs[0] if len(r) == 7) > 0   # Meals happened

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
    w = _world(4, profiles=("complet", "prudent", "chasseur", "chasseur_rassasie", "vitesse_fixe", "scripte"))
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

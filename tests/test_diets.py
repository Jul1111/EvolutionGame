"""Two kinds of food and the diet gene (FOOD_TYPES = 2, config.py)."""
import random

import numpy as np
import pytest

import config
from core import kernels
from core.food import Food
from core.world import World
from evolution.continuous import ContinuousSimulation, load_population, save_population


def _cfg(**kw):
    return config.Settings(**{"FOOD_TYPES": 2, "ACTIVE_PROFILES": ["regime", "regime_faim"], **kw})


def test_one_kind_of_food_by_default():
    w = World(random.Random(1), config.Settings())
    assert {f.kind for f in w.foods} == {0} and w.gains(np.array([0.3])) is None


def test_meal_depends_on_diet_and_kind():
    cfg = _cfg(FOOD_COUNT=0, POISON_COUNT=0, OBSTACLE_COUNT=0)
    w = World(random.Random(2), cfg)
    for diet in (0.0, 1.0, 0.5):
        c = w.add_creature(None, "regime", energy=50.0, diet=diet)
        assert w.gain(c, Food(0, 0, 30.0, kind=0)) == pytest.approx((1 - diet) ** cfg.DIET_EXPONENT)
    w.foods.append(Food(w.creatures[0].x, w.creatures[0].y, 30.0, kind=0))
    w.creatures[0].angle = w.creatures[1].angle = 0.0
    w._contacts(w.foods, w.creatures[:1], np.array([w.creatures[0].x]), np.array([w.creatures[0].y]),
                np.array([50.0]), (np.array([8.0]), np.array([200.0])), w._eat, fits=True,
                gains=w.gains(np.array([0.0])))
    assert w.creatures[0].energy == 80.0   # A specialist of kind 0 gets all of a food of kind 0


def test_diets_inherited_saved_and_loaded(tmp_path):
    sim = ContinuousSimulation(random.Random(3), cfg=_cfg(ACTIVE_PROFILES=["scripte"]))
    sim.run(1500)
    diets = sorted(c.diet for c in sim.world.creatures)
    assert sim.total_births > 0 and 0.0 <= diets[0] and diets[-1] <= 1.0 and diets[0] != diets[-1]
    path = str(tmp_path / "p.npz")
    save_population(sim, path)
    assert sorted(f[2] for fs in load_population(path).values() for f in fs) == diets
    assert "diet_mean" in sim.header and "diet__scripte" in sim.header


def test_compiled_kernels_match_numpy_with_two_kinds(monkeypatch):
    if not kernels.ENABLED:
        pytest.skip("numba absent")
    runs = []
    for enabled in (True, False):
        monkeypatch.setattr(kernels, "ENABLED", enabled)
        sim = ContinuousSimulation(random.Random(5), cfg=_cfg(ACTIVE_PROFILES=["regime", "scripte"]))
        sim.run(400)
        runs.append([(c.uid, c.x, c.y, c.energy, c.food_eaten, c.diet) for c in sim.world.creatures])
    assert runs[0] == runs[1] and sum(r[4] for r in runs[0]) > 0


def test_fast_update_matches_reference_with_two_kinds():
    from core.physics import torus_delta
    cfg = _cfg(POISON_COUNT=8)
    worlds = []
    for _ in range(2):
        w = World(random.Random(11), cfg)
        rng = random.Random(4)
        for p in ("regime", "regime_faim", "scripte"):
            for _ in range(20):
                from brain.profiles import new_brain
                b = new_brain(p)
                b.randomize(w.rng, cfg.NN_INIT_STD)
                w.add_creature(b, p, diet=rng.random())
        worlds.append(w)
    fast, ref = worlds
    for _ in range(200):
        fast.update()
        ref._update_reference()
    for a, b in zip(fast.creatures, ref.creatures):
        assert a.alive == b.alive and a.food_eaten == b.food_eaten
        assert abs(torus_delta(a.x, b.x, fast.width)) < 1e-3 and abs(a.energy - b.energy) < 1e-3
    assert sum(c.food_eaten for c in fast.creatures) > 0

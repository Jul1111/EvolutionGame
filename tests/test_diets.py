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


@pytest.mark.parametrize("kinds", [2, 4])
def test_game_shows_diets(make_app, kinds):
    """Kinds of food in the game: colour «régime», the diet curves (and the 0-1 curves, once broken), legend."""
    app = make_app(FOOD_TYPES=kinds, FOOD_ENERGY=60.0, ACTIVE_PROFILES=["regime", "regime_faim"], SAMPLE_TICKS=5)
    app.run(max_frames=2)   # First frame: the layout
    while app.scene.color_label() != "régime":
        app.do("color")
    app.do("legend")
    app.do("chart")
    for key in ("diet_low", "diet_high", "diet_mean", "blind_frac", "blind_turn"):
        app.do("series:" + key)
    app.run(max_frames=20)
    assert {f.kind for f in app.world.foods} == set(range(kinds))
    assert app.sim.diets and app.hud.rows and app.hud.rows[-1].get("diet_mean") is not None


def test_color_mode_skips_diet_with_one_kind_of_food(make_app):
    app = make_app()
    seen = set()
    for _ in range(10):
        app.do("color")
        seen.add(app.scene.color_label())
    assert "régime" not in seen and "lignée" in seen


def test_kind_pattern_spreads_the_shares():
    from core.food import kind_pattern
    assert kind_pattern(_cfg()) == [0, 1]   # As before the shares: food k of kind k % 2
    assert kind_pattern(_cfg(FOOD_TYPES=4)) == [0, 1, 2, 3]
    assert sorted(kind_pattern(_cfg(FOOD_KIND_SHARES=(1, 3)))) == [0, 1, 1, 1]
    with pytest.raises(ValueError):
        kind_pattern(_cfg(FOOD_KIND_SHARES=(1, 2, 3)))
    w = World(random.Random(1), _cfg(FOOD_KIND_SHARES=(1, 3), FOOD_COUNT=40))
    kinds = [f.kind for f in w.foods]
    assert kinds.count(0) == len(kinds) // 4
    w.resize_items(60)
    assert [f.kind for f in w.foods][:len(kinds)] == kinds and [f.kind for f in w.foods].count(0) == len(w.foods) // 4


def test_gains_with_more_kinds_and_richer_kinds():
    w = World(random.Random(1), _cfg(FOOD_TYPES=3, FOOD_KIND_ENERGY=(1.0, 2.0, 0.5), DIET_EXPONENT=1.0))
    g = w.gains(np.array([0.0, 0.5, 0.25, 1.0]))
    assert g.shape == (4, 3)
    assert g[0].tolist() == [1.0, 0.0, 0.0]   # A specialist of kind 0 gets nothing from the far kinds
    assert g[1].tolist() == [0.0, 2.0, 0.0]   # Kind 1 (diet 0.5) twice as rich
    assert g[2].tolist() == pytest.approx([0.5, 1.0, 0.0])
    assert g[3].tolist() == [0.0, 0.0, 0.5]
    assert {f.kind for f in w.foods} == {0, 1, 2}


def test_four_kinds_founders_columns_and_kernels(monkeypatch):
    cfg = _cfg(FOOD_TYPES=4, ACTIVE_PROFILES=["regime"])
    sim = ContinuousSimulation(random.Random(4), cfg=cfg)
    assert sorted({round(c.diet, 3) for c in sim.world.creatures}) == [0.0, 0.333, 0.667, 1.0]
    assert [h for h in sim.header if h.startswith("diet_kind")] == [f"diet_kind{k}" for k in range(4)]
    row = sim.sample()
    assert sum(row[f"diet_kind{k}"] for k in range(4)) == pytest.approx(1.0)
    if not kernels.ENABLED:
        return
    runs = []
    for enabled in (True, False):
        monkeypatch.setattr(kernels, "ENABLED", enabled)
        sim = ContinuousSimulation(random.Random(5), cfg=_cfg(FOOD_TYPES=4, FOOD_KIND_ENERGY=(2.0, 1.0, 1.0, 0.5)))
        sim.run(300)
        runs.append([(c.uid, c.x, c.y, c.energy, c.food_eaten, c.diet) for c in sim.world.creatures])
    assert runs[0] == runs[1] and sum(r[4] for r in runs[0]) > 0

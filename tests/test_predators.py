"""Predators (config.PREDATION, profiles marked "predator" in brain/profiles.py)."""
import math
import random

import numpy as np
import pytest

import config
from brain.profiles import new_brain
from core import kernels
from core.physics import torus_delta
from core.world import World
from evolution.continuous import PREDATION_HEADER, ContinuousSimulation


def _empty(**kw):
    return World(random.Random(1), config.Settings(**{"FOOD_COUNT": 0, "POISON_COUNT": 0, "OBSTACLE_COUNT": 0,
                                                      **kw}))


def _put(w, profile, x, y, energy=100.0, angle=0.0):
    c = w.add_creature(new_brain(profile), profile, energy=energy)   # Zero weights: turn 0, half speed
    c.x, c.y, c.angle = x, y, angle
    return c


def _phase4(w):
    """Only the predation phase, on the creatures as they are."""
    alive, rows = w.living()
    w._predation(alive, rows, np.array([bool(c._spec.get("predator")) for c in alive]))


@pytest.mark.parametrize("compiled", [True, False])
def test_capture_rule(monkeypatch, compiled):
    if compiled and not kernels.ENABLED:
        pytest.skip("numba absent")
    monkeypatch.setattr(kernels, "ENABLED", compiled)
    w = _empty()
    far = _put(w, "predateur", 100.0, 100.0, energy=50.0)    # 14 from the prey's centre, edge gap 6
    near = _put(w, "predateur", 120.0, 112.0, energy=50.0)   # 12 from it, edge gap 4: the closest wins
    prey = _put(w, "proie", 110.0, 110.0, energy=80.0)
    lone = _put(w, "proie", 400.0, 400.0)                    # Touched by nobody
    _phase4(w)
    assert not prey.alive and prey.death_cause == "mangé" and lone.alive
    assert near.energy == 50.0 + w.cfg.PREDATION_EFFICIENCY * 80.0 and near.kills == 1 and far.energy == 50.0
    assert near.digest == w.cfg.PREDATOR_DIGEST and w.predated == 1
    # Digesting: the next prey goes to the other predator; a meal that does not fit is left
    second = _put(w, "proie", 108.0, 100.0, energy=60.0)   # 8 from «far», 17 from «near»
    _phase4(w)
    assert not second.alive and far.kills == 1 and near.digest == w.cfg.PREDATOR_DIGEST - 1
    full = _put(w, "predateur", 600.0, 300.0, energy=199.0)
    third = _put(w, "proie", 610.0, 300.0, energy=60.0)
    _phase4(w)
    assert third.alive and full.kills == 0


def test_predators_never_eat_food_and_never_eat_each_other():
    w = _empty(FOOD_COUNT=1)
    hunter = _put(w, "predateur", w.foods[0].x, w.foods[0].y, energy=50.0)
    other = _put(w, "predateur", w.foods[0].x + 5, w.foods[0].y, energy=50.0)
    w.update()
    assert hunter.food_eaten == 0 and other.alive and w.foods[0].cooldown == 0


def test_sensors_see_the_other_kind_only():
    w = _empty(VISION_FOV_DEGREES=360)
    hunter = _put(w, "predateur", 100.0, 100.0)
    prey = _put(w, "proie", 150.0, 100.0, angle=math.pi / 2)   # The predator on its right side
    _put(w, "predateur", 105.0, 100.0)   # Another predator, closer: never seen as a prey
    w.sense_all()
    for c, (d, a) in ((hunter, (50.0, 0.0)), (prey, (45.0, 0.5))):
        values = w.sense(c)
        k = 0 if c is hunter else len(values) - 2   # «prey» comes first for predators, «predator» last for prey
        assert values[k] == pytest.approx(d / w.cfg.VISION_RANGE) and values[k + 1] == pytest.approx(a)
    # The plain version (interface, reference loop) gives the same values
    w._near_tick = -5
    assert w.sense(hunter)[:2] == pytest.approx([50.0 / w.cfg.VISION_RANGE, 0.0])
    assert w.sense(prey)[-2:] == pytest.approx([45.0 / w.cfg.VISION_RANGE, 0.5])


def _hunting_cfg(**kw):
    return config.Settings(**{"PREDATION": True, "PREDATOR_START": 0, "PREDATOR_FOUNDERS": 60,
                              "ACTIVE_PROFILES": ["proie", "complet"], **kw})


def test_compiled_kernels_match_numpy_with_predators(monkeypatch):
    if not kernels.ENABLED:
        pytest.skip("numba absent")
    runs = []
    for enabled in (True, False):
        monkeypatch.setattr(kernels, "ENABLED", enabled)
        sim = ContinuousSimulation(random.Random(5), cfg=_hunting_cfg(WORLD_SCALE=2, VISION_FOV_DEGREES=90))
        sim.run(600)
        runs.append([(c.uid, c.x, c.y, c.energy, c.food_eaten, c.kills, c.digest) for c in sim.world.creatures]
                    + [sim.world.predated, sim.world.hunt])
    assert runs[0] == runs[1] and runs[0][-2] > 0   # Kills happened


def test_fast_update_matches_reference_with_predators():
    cfg = _hunting_cfg(POISON_COUNT=8, VISION_FOV_DEGREES=360)
    worlds = []
    for _ in range(2):
        w = World(random.Random(11), cfg)
        for p, n in (("proie", 60), ("complet", 30), ("predateur", 40)):
            w.add_population(p, n)
        worlds.append(w)
    fast, ref = worlds
    for _ in range(300):
        fast.update()
        ref._update_reference()
    for a, b in zip(fast.creatures, ref.creatures):
        assert a.alive == b.alive and a.food_eaten == b.food_eaten and a.kills == b.kills
        assert a.death_cause == b.death_cause and a.digest == b.digest
        assert abs(torus_delta(a.x, b.x, fast.width)) < 1e-3 and abs(a.energy - b.energy) < 1e-3
    assert fast.predated == ref.predated > 0


def test_predators_arrive_at_the_start_tick_and_are_measured():
    cfg = _hunting_cfg(PREDATOR_START=30, PREDATOR_FOUNDERS=10, SAMPLE_TICKS=50, ACTIVE_PROFILES=["proie"])
    sim = ContinuousSimulation(random.Random(2), cfg=cfg)
    sim.run(30)
    assert not any(c._spec.get("predator") for c in sim.world.creatures)
    sim.run(1)
    assert sum(c.profile == "predateur" for c in sim.world.creatures) == 10
    sim.run(300)
    assert "pop__predateur" in sim.header and set(PREDATION_HEADER) <= set(sim.header)
    s = sim.last_sample
    assert s["predators"] == s["pop__predateur"] and s["prey"] == s["pop__proie"]
    assert 0.0 <= s["prey_threat_frac"] <= 1.0 and s["pred_chase_frac"] is not None


def test_no_predation_by_default():
    sim = ContinuousSimulation(random.Random(3), cfg=config.Settings(SAMPLE_TICKS=50))
    sim.run(100)
    assert not sim.predation and "deaths_eaten" not in sim.header and "pop__predateur" not in sim.header
    assert not sim.world.hunting and sim.world.predated == 0


def test_predator_cost_factor():
    w = World(random.Random(1), config.Settings(PREDATOR_COST_FACTOR=2.0))
    hunter, prey = _put(w, "predateur", 0, 0), _put(w, "proie", 50, 50)
    assert math.isclose(hunter.base_cost, 2.0 * prey.base_cost)


def test_game_shows_predators(make_app):
    """Predators in the game: crown sprite, Population panel per species, the predation curves, the settings."""
    app = make_app(PREDATION=True, PREDATOR_START=3, PREDATOR_FOUNDERS=20, ACTIVE_PROFILES=["proie"], SAMPLE_TICKS=5)
    app.run(max_frames=2)
    app.do("chart")
    for key in ("prey", "predators", "deaths_eaten", "kill_rate", "prey_threat_frac", "prey_speed_threat",
                "prey_toward", "pred_toward"):
        app.do("series:" + key)
    app.run(max_frames=20)
    assert any(c.profile == "predateur" for c in app.world.creatures)
    assert "predateur" in app.hud.profiles and app.hud.rows and app.hud.rows[-1].get("predators") is not None
    assert app.scene.predator_sprite.get_width() > 0

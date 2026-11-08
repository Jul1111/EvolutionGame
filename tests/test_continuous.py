import math
import random

import config
from core.physics import torus_delta
from evolution.continuous import ContinuousSimulation, save_population, load_population


def _sim(seed=0, **kw):
    config.INITIAL_POPULATION = 40
    return ContinuousSimulation(random.Random(seed), **kw)


def test_birth_energy_and_lineage():
    sim = _sim()
    parent = sim.world.creatures[0]
    parent.energy, parent.age = config.REPRO_THRESHOLD + 5, config.MATURITY_AGE
    before = len(sim.world.creatures)
    sim._give_birth(parent)
    child = sim.world.creatures[-1]
    assert len(sim.world.creatures) == before + 1
    assert parent.energy == config.REPRO_THRESHOLD + 5 - config.REPRO_COST
    assert child.energy == config.REPRO_CHILD_ENERGY
    assert child.parent_id == parent.uid and child.lineage_gen == parent.lineage_gen + 1
    assert child.uid != parent.uid
    d = math.hypot(torus_delta(parent.x, child.x, sim.world.width), torus_delta(parent.y, child.y, sim.world.height))
    assert d <= 4 * config.CREATURE_RADIUS + 1e-9   # Born next to its parent


def test_cooldown_and_maturity():
    sim = _sim()
    c = sim.world.creatures[0]
    c.energy, c.age = 1000, config.MATURITY_AGE - 1
    assert not sim._can_give_birth(c)
    c.age = config.MATURITY_AGE
    assert sim._can_give_birth(c)
    c.last_birth_age = c.age
    assert not sim._can_give_birth(c)


def test_cap_blocks_and_counts():
    config.POP_MAX = 40
    sim = _sim()
    for c in sim.world.creatures:
        c.energy, c.age = config.REPRO_THRESHOLD + 50, config.MATURITY_AGE
    sim.step()
    assert len(sim.world.creatures) <= config.POP_MAX
    assert sim.cap_blocked > 0


def test_old_age_and_extinction_stop():
    config.AGE_MAX = 5
    sim = _sim()
    played = sim.run(1000)
    assert sim.extinct and played < 1000
    assert sim.world.creatures == []


def test_timeline_and_population_roundtrip(tmp_path):
    config.SAMPLE_TICKS = 50
    sim = _sim(timeline_path=str(tmp_path / "t.csv"))
    sim.run(200)
    lines = (tmp_path / "t.csv").read_text().splitlines()
    assert lines[0].startswith("tick,population") and len(lines) >= 2
    path = str(tmp_path / "pop.npz")
    save_population(sim, path)
    founders = load_population(path)
    assert sum(len(g) for g in founders.values()) == len(sim.world.creatures)
    again = ContinuousSimulation(random.Random(1), founders=founders)
    assert len(again.world.creatures) == len(sim.world.creatures)


def test_resize_items_follows_config():
    sim = _sim()
    config.FOOD_COUNT, config.POISON_COUNT = 3, 0
    sim.world.resize_items()
    assert len(sim.world.foods) == 3 and sim.world.poisons == []
    config.FOOD_COUNT, config.FOOD_ENERGY = 12, 45.0
    sim.world.resize_items()
    assert len(sim.world.foods) == 12 and all(f.energy == 45.0 for f in sim.world.foods)


def test_follow_lineage_finds_a_living_descendant():
    sim = _sim()
    parent = sim.world.creatures[0]
    parent.energy, parent.age = 500, config.MATURITY_AGE
    sim._give_birth(parent)
    child = sim.world.creatures[-1]
    parent.alive = False
    assert sim.descendant_of(parent) is child

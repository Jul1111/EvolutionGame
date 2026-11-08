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


def test_size_gene_modes():
    sim = _sim()
    parent = sim.world.creatures[0]
    config.SIZE_MODE = "fixe"
    assert sim._child_size(1.3) == 1.0
    config.SIZE_MODE = "actif"
    sizes = [sim._child_size(1.0) for _ in range(200)]
    assert min(sizes) >= config.SIZE_MIN and max(sizes) <= config.SIZE_MAX and len(set(sizes)) > 100
    assert sim._child_size(10.0) == config.SIZE_MAX


def test_size_effects_actif_vs_neutre():
    from core.creature import Creature
    config.SIZE_MODE = "actif"
    big = Creature(0, 0, 0, 100, None, "complet", size=2.0)
    assert big.radius == 2 * config.CREATURE_RADIUS and big.energy_max == 2 * config.ENERGY_MAX
    assert abs(big.base_cost - config.ENERGY_BASE_COST * 2 ** 0.75) < 1e-12
    assert big.move_cost == 2 * config.ENERGY_MOVE_COST
    config.SIZE_MODE = "neutre"
    same = Creature(0, 0, 0, 100, None, "complet", size=2.0)
    assert same.size == 2.0 and same.radius == config.CREATURE_RADIUS and same.energy_max == config.ENERGY_MAX


def test_birth_scales_with_body():
    config.SIZE_MODE = "actif"
    sim = _sim()
    parent = sim.world.creatures[0]
    parent.set_size(0.5)
    parent.energy, parent.age = config.REPRO_THRESHOLD * 0.5, config.MATURITY_AGE
    assert sim._can_give_birth(parent)
    sim._give_birth(parent)
    child = sim.world.creatures[-1]
    assert parent.energy == 0.5 * (config.REPRO_THRESHOLD - config.REPRO_COST)
    assert child.energy == min(config.REPRO_CHILD_ENERGY * 0.5, child.energy_max)


def test_sizes_saved_and_loaded(tmp_path):
    config.SIZE_MODE = "actif"
    sim = _sim()
    for i, c in enumerate(sim.world.creatures):
        c.set_size(0.6 + i * 0.01)
    path = str(tmp_path / "p.npz")
    save_population(sim, path)
    founders = load_population(path)
    sizes = sorted(sz for fs in founders.values() for _, sz in fs)
    assert sizes == sorted(c.size for c in sim.world.creatures)
    again = ContinuousSimulation(random.Random(2), founders=founders)
    assert sorted(c.size for c in again.world.creatures) == sizes

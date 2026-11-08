"""Continuous evolution: no generations, no chosen parents. Natural selection only.

A creature old enough (MATURITY_AGE) with enough energy (REPRO_THRESHOLD) gives birth: it loses REPRO_COST, its
newborn starts with REPRO_CHILD_ENERGY and inherits its genome with a mutation. A creature dies of hunger
(energy 0) or of old age (AGE_MAX). POP_MAX is only a computing cap: births it blocks are counted (cap_blocked),
a run where the cap regulates the population does not show natural regulation.
An extinction ends the run.

Measures: one line of timeline.csv every SAMPLE_TICKS ticks (see SAMPLE_HEADER).
"""
import csv
import os
import statistics
import time

import numpy as np

import config
from brain.profiles import new_brain
from core.world import World
from evolution.mutation import mutate

SAMPLE_HEADER = ["tick", "population", "births", "deaths_hunger", "deaths_age", "mean_age_at_death",
                 "mean_lineage_gen", "max_lineage_gen", "food_rate", "poison_rate", "mean_speed", "mean_energy",
                 "cap_blocked", "food_available"]


class ContinuousSimulation:
    def __init__(self, rng, timeline_path=None, founders=None, verbose=False, start_tick=0, append=False,
                 log_deaths=False):
        """`founders`: {profile: [genomes]} to start from a saved population (load_population); else random founders
        of config.ACTIVE_PROFILES. `start_tick` and `append`: resume a saved run, adding to its timeline.csv."""
        self.rng = rng
        self.verbose = verbose
        self.timeline_path = timeline_path
        self.world = World(rng)
        self.world.tick = start_tick
        self.next_uid = 0
        self.extinct = False
        self.total_births = 0
        self.total_deaths = 0
        # log_deaths=True: one record per death (tick, age, mean speed over its life, children, meals, cause)
        self.death_log = [] if log_deaths else None
        self._reset_counters()
        profiles = list(founders) if founders else list(config.ACTIVE_PROFILES)
        for index, name in enumerate(profiles):
            if founders:
                for genome in founders[name]:
                    brain = new_brain(name)
                    brain.set_genome(genome)
                    self._add(brain, name)
            else:
                for _ in range(_share(round(config.INITIAL_POPULATION * self.world.area_factor), index, len(profiles))):
                    brain = new_brain(name)
                    brain.randomize(rng, config.NN_INIT_STD)
                    self._add(brain, name)
        if timeline_path and not (append and os.path.exists(timeline_path)):
            os.makedirs(os.path.dirname(timeline_path) or ".", exist_ok=True)
            with open(timeline_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(SAMPLE_HEADER)

    # ---------- one tick ----------

    def step(self):
        """One tick: the world moves, then old age, births, and removal of the dead. Returns False once extinct."""
        if self.extinct:
            return False
        world = self.world
        world.update()
        living = [c for c in world.creatures if c.alive]
        self.life_ticks += len(living)
        for c in living:
            if config.AGE_MAX and c.age >= config.AGE_MAX:
                c.alive = False
                c.death_cause = "vieillesse"
        for parent in [c for c in living if c.alive and self._can_give_birth(c)]:
            if len(world.creatures) >= self.pop_max:
                self.cap_blocked += 1
                continue
            self._give_birth(parent)
        for c in world.creatures:
            if not c.alive:
                self.deaths[c.death_cause or "faim"] += 1
                self.death_ages.append(c.age)
                self.total_deaths += 1
                if self.death_log is not None:
                    self.death_log.append({"tick": world.tick, "age": c.age, "profile": c.profile,
                                           "mean_speed": c.speed_sum / c.age if c.age else 0.0,
                                           "children": c.children, "food": c.food_eaten,
                                           "lineage_gen": c.lineage_gen, "cause": c.death_cause})
        world.creatures = [c for c in world.creatures if c.alive]
        if world.tick % config.SAMPLE_TICKS == 0:
            self._sample()
        if not world.creatures:
            self.extinct = True
            if self.world.tick % config.SAMPLE_TICKS:
                self._sample()   # Last line: the extinction itself
        return not self.extinct

    @property
    def pop_max(self):
        """Computing cap of this world: POP_MAX per screen-sized area, like food and obstacles."""
        return round(config.POP_MAX * self.world.area_factor)

    @property
    def new_sample(self):
        """True on the tick a line was just added to timeline.csv."""
        return self.world.tick % config.SAMPLE_TICKS == 0 or self.extinct

    def descendant_of(self, creature):
        """A living descendant of `creature` (youngest child first, then grandchildren...), or None."""
        family, frontier = {creature.uid}, {creature.uid}
        while frontier:
            kids = [c for c in self.world.creatures if c.parent_id in frontier and c.uid not in family]
            alive = [c for c in kids if c.alive]
            if alive:
                return max(alive, key=lambda c: c.birth_tick)
            frontier = {c.uid for c in kids}
            family |= frontier
        return None

    def run(self, ticks):
        """Runs up to `ticks` ticks, or until extinction. Returns the number of ticks played."""
        start = self.world.tick
        while self.world.tick - start < ticks and self.step():
            pass
        return self.world.tick - start

    # ---------- births ----------

    def _can_give_birth(self, c):
        return (c.energy >= config.REPRO_THRESHOLD and c.age >= config.MATURITY_AGE
                and (c.last_birth_age is None or c.age - c.last_birth_age >= config.REPRO_COOLDOWN))

    def _give_birth(self, parent):
        parent.energy -= config.REPRO_COST
        parent.last_birth_age = parent.age
        parent.children += 1
        brain = new_brain(parent.profile)
        brain.set_genome(mutate(parent.brain.get_genome(), self.rng, config.MUTATION_STD))
        self._add(brain, parent.profile, energy=config.REPRO_CHILD_ENERGY, near=(parent.x, parent.y),
                  parent_id=parent.uid, lineage_gen=parent.lineage_gen + 1)
        self.births += 1
        self.total_births += 1

    def _add(self, brain, profile, **kwargs):
        c = self.world.add_creature(brain, profile, uid=self.next_uid, birth_tick=self.world.tick, **kwargs)
        self.next_uid += 1
        return c

    # ---------- measures ----------

    def _reset_counters(self):
        self.births = 0
        self.deaths = {"faim": 0, "vieillesse": 0}
        self.death_ages = []
        self.cap_blocked = 0
        self.life_ticks = 0
        self._eaten0 = getattr(self.world, "eaten", 0)
        self._poisoned0 = getattr(self.world, "poisoned", 0)

    def sample(self):
        """Measures since the last sample (counts) and now (population state)."""
        cs = self.world.creatures
        n = len(cs)
        per_k = 1000 / self.life_ticks if self.life_ticks else 0.0
        return {
            "tick": self.world.tick,
            "population": n,
            "births": self.births,
            "deaths_hunger": self.deaths["faim"],
            "deaths_age": self.deaths["vieillesse"],
            "mean_age_at_death": statistics.mean(self.death_ages) if self.death_ages else None,
            "mean_lineage_gen": sum(c.lineage_gen for c in cs) / n if n else None,
            "max_lineage_gen": max((c.lineage_gen for c in cs), default=None),
            # Meals (and poison hits) per 1000 ticks of life: how good the creatures are at feeding, whatever their number
            "food_rate": (self.world.eaten - self._eaten0) * per_k,
            "poison_rate": (self.world.poisoned - self._poisoned0) * per_k,
            "mean_speed": sum(c.speed for c in cs) / n if n else None,
            "mean_energy": sum(c.energy for c in cs) / n if n else None,
            "cap_blocked": self.cap_blocked,
            "food_available": sum(1 for f in self.world.foods if f.cooldown <= 0),
        }

    def _sample(self):
        s = self.sample()
        self.last_sample = s
        if self.timeline_path:
            with open(self.timeline_path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([_cell(s[k]) for k in SAMPLE_HEADER])
        if self.verbose:
            print(f"t {s['tick']:>7} | pop {s['population']:>4} | naiss. {s['births']:>3} | morts faim "
                  f"{s['deaths_hunger']:>3} vieil. {s['deaths_age']:>3} | lignée {_cell(s['mean_lineage_gen'])} | "
                  f"repas/1000t {s['food_rate']:.2f} | plafond {s['cap_blocked']}")
        self._reset_counters()


# ---------- saving a population by hand ----------

def success_key(c):
    """Reproductive success: what natural selection actually rewards. Children first, then meals, then age."""
    return (c.children, c.food_eaten, c.age)


def save_population(sim, path):
    """Saves every living creature: genome per profile, plus lineage depth (for the record) and the tick.
    Restored creatures start fresh (energy, random place): only the genomes carry over."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {"tick": sim.world.tick, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    for name in {c.profile for c in sim.world.creatures}:
        members = [c for c in sim.world.creatures if c.profile == name]
        data[f"genomes__{name}"] = np.array([c.brain.get_genome() for c in members])
        data[f"lineage__{name}"] = np.array([c.lineage_gen for c in members])
    tmp = path[:-4] + "_tmp.npz" if path.endswith(".npz") else path + "_tmp.npz"
    np.savez(tmp, **data)
    os.replace(tmp, path if path.endswith(".npz") else path + ".npz")


def load_population(path, with_tick=False):
    """{profile: [genomes]} from save_population. with_tick=True: (founders, tick of the save).
    Profiles that no longer exist, or whose network changed size, are left out (message printed)."""
    from brain.profiles import PROFILES, n_params
    founders = {}
    with np.load(path) as data:
        for key in data.files:
            if not key.startswith("genomes__"):
                continue
            name, genomes = key.split("__", 1)[1], data[key]
            if name not in PROFILES or genomes.ndim != 2 or genomes.shape[1] != n_params(name):
                print(f"{os.path.basename(path)} : espèce {name} ignorée (inconnue ou réseau modifié)")
                continue
            founders[name] = list(genomes)
        tick = int(data["tick"]) if "tick" in data.files else 0
    return (founders, tick) if with_tick else founders


def populations_dir():
    return os.path.join(config.SAVE_DIR, "populations")


def snapshot_path(label):
    """saves/populations/<date>_<label>.npz: where the game keeps the populations saved by hand."""
    return os.path.join(populations_dir(), time.strftime("%Y%m%d_%H%M%S") + f"_{label}.npz")


def autosave_path():
    """Population written when the game quits, reloaded at the next launch (config.LOAD_ON_START)."""
    return os.path.join(config.SAVE_DIR, "autosave.npz")


def latest_snapshot():
    """Most recent population saved by hand, or None."""
    folder = populations_dir()
    if not os.path.isdir(folder):
        return None
    files = sorted(f for f in os.listdir(folder) if f.endswith(".npz"))
    return os.path.join(folder, files[-1]) if files else None


def _share(total, index, n):
    base, rest = divmod(total, max(1, n))
    return base + (1 if index < rest else 0)


def _cell(v):
    if v is None:
        return ""
    return round(v, 3) if isinstance(v, float) else v

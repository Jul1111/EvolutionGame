"""Do the two specialist groups of a split species behave differently? For each population file:
genome distances (within / between groups), meals on their own food, attraction to own vs other food, speed,
sensitivity of the network to each input, per group (green: diet < 0.25, yellow: diet > 0.75)."""
import glob
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, "/Users/jul/Documents/Dev/EvolutionGame")
from brain.profiles import input_labels  # noqa: E402
from core.kernels import worker_init  # noqa: E402
from core.world import World  # noqa: E402
from evolution.continuous import ContinuousSimulation, load_population  # noqa: E402
from experiments.run import population_settings  # noqa: E402

TICKS = 3000


def group(diet):
    return "vert" if diet < 0.25 else "jaune" if diet > 0.75 else None


def analyse(path):
    founders = load_population(path)
    cfg = population_settings(path)[0]
    out = {}
    # Genome distances
    for name, members in founders.items():
        g = {"vert": [], "jaune": []}
        for genome, _, diet in members:
            if group(diet):
                g[group(diet)].append(np.asarray(genome))
        if min(len(v) for v in g.values()) < 5:
            return None
        rng = np.random.default_rng(0)

        def mean_dist(a, b, n=300):
            return float(np.mean([np.linalg.norm(a[rng.integers(len(a))] - b[rng.integers(len(b))]) for _ in range(n)]))
        out["dist"] = (mean_dist(g["vert"], g["vert"]), mean_dist(g["jaune"], g["jaune"]),
                       mean_dist(g["vert"], g["jaune"]))
        profile = name
    # Replay: meals by kind, speed, inputs and outputs of watched creatures
    meals = {"vert": [0, 0], "jaune": [0, 0]}   # [own kind, other kind]
    orig = World._eat

    def eat(self, food, creature, amount):
        grp = group(creature.diet)
        if grp:
            own = (food.kind == 0) == (grp == "vert")
            meals[grp][0 if own else 1] += 1
        return orig(self, food, creature, amount)
    World._eat = eat
    try:
        sim = ContinuousSimulation(random.Random(1), founders=founders, cfg=cfg)
        watched = {grp: [c for c in sim.world.creatures if group(c.diet) == grp][:25] for grp in ("vert", "jaune")}
        states = {id(c): [] for cs in watched.values() for c in cs}
        for t in range(TICKS):
            if not sim.step():
                break
            if t % 5 == 0:
                for cs in watched.values():
                    for c in cs:
                        if c.alive:
                            states[id(c)].append(np.array(sim.world.sense(c), float))
    finally:
        World._eat = orig
    out["meals"] = {k: v[0] / max(1, sum(v)) for k, v in meals.items()}
    out["speed"] = {grp: statistics.mean(c.speed_sum / c.age for c in sim.world.creatures
                                         if group(c.diet) == grp and c.age > 100) for grp in ("vert", "jaune")}
    labels = input_labels(profile)
    i_angle, i_value = labels.index("Angle"), labels.index("Valeur nourr.")
    sens, attract = {}, {}
    for grp, cs in watched.items():
        per_input, own_corr, other_corr = [], [], []
        for c in cs:
            x = np.array(states[id(c)])
            if len(x) < 40:
                continue
            y = np.array([c.brain.forward(v)[:2] for v in x])
            lo, hi = np.percentile(x, 10, axis=0), np.percentile(x, 90, axis=0)
            row = []
            for i in range(x.shape[1]):
                a, b = x.copy(), x.copy()
                a[:, i], b[:, i] = lo[i], hi[i]
                row.append(float(np.mean(np.abs(np.array([c.brain.forward(v)[:2] for v in b])
                                                - np.array([c.brain.forward(v)[:2] for v in a])))))
            per_input.append(row)
            # Attraction: correlation between the angle of the nearest food and the turn, for own / other food
            seen = x[:, i_value] > 0.5
            other = (x[:, i_value] < 0.5) & (x[:, labels.index("Distance")] < 1.0)
            for mask, acc in ((seen, own_corr), (other, other_corr)):
                if mask.sum() > 8 and np.std(x[mask, i_angle]) > 1e-6 and np.std(y[mask, 0]) > 1e-6:
                    acc.append(float(np.corrcoef(x[mask, i_angle], y[mask, 0])[0, 1]))
        sens[grp] = np.mean(per_input, axis=0) if per_input else None
        attract[grp] = (statistics.mean(own_corr) if own_corr else float("nan"),
                        statistics.mean(other_corr) if other_corr else float("nan"))
    out["sens"], out["attract"], out["labels"] = sens, attract, labels
    return out


if __name__ == "__main__":
    paths = [p for run in sys.argv[1:] for p in sorted(glob.glob(run + "/seed_*/population_finale.npz"))]
    with ProcessPoolExecutor(8, initializer=worker_init, initargs=(8,)) as pool:
        results = [r for r in pool.map(analyse, paths) if r]
    print(f"{len(results)} populations scindées analysées ({TICKS} ticks rejoués chacune)\n")
    d = np.array([r["dist"] for r in results])
    print(f"Distance entre génomes : dans le groupe vert {d[:, 0].mean():.2f}, dans le jaune {d[:, 1].mean():.2f}, "
          f"entre les deux {d[:, 2].mean():.2f} (plus grand dans {int((d[:, 2] > d[:, :2].max(axis=1)).sum())}"
          f"/{len(d)} populations)")
    for grp in ("vert", "jaune"):
        m = [r["meals"][grp] for r in results]
        s = [r["speed"][grp] for r in results]
        a = np.array([r["attract"][grp] for r in results])
        print(f"{grp:6s}: repas sur sa nourriture {np.mean(m):.0%} (de {min(m):.0%} à {max(m):.0%}), "
              f"vitesse {np.mean(s):.2f}, attirance (corrélation angle → virage) vers la sienne "
              f"{np.nanmean(a[:, 0]):+.2f}, vers l'autre {np.nanmean(a[:, 1]):+.2f}")
    labels = results[0]["labels"]
    print("\nSensibilité de la sortie à chaque entrée (moyenne des populations) :")
    print(f"  {'entrée':16s} {'vert':>6s} {'jaune':>6s}")
    for i, lab in enumerate(labels):
        v = np.mean([r["sens"]["vert"][i] for r in results if r["sens"]["vert"] is not None])
        j = np.mean([r["sens"]["jaune"][i] for r in results if r["sens"]["jaune"] is not None])
        print(f"  {lab:16s} {v:6.3f} {j:6.3f}")
    sp = np.array([[r["speed"]["vert"], r["speed"]["jaune"]] for r in results])
    print(f"\nPar population, vitesse vert / jaune : " + "  ".join(f"{a:.2f}/{b:.2f}" for a, b in sp))

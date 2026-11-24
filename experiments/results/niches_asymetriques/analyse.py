"""Asymmetric niches: do the specialists of the rare-rich food (kind 0, diet < 0.25) and of the abundant-poor food
(kind 1, diet > 0.75) live differently? Per run folder: seeds split at the end, then for each split population
(population_finale.npz, replayed TICKS ticks): share of each group, meals per 1000 ticks and share on its own food,
energy, speed, share of life with no food in view and speed then, attraction to its own food, sensitivity to inputs.
    python asym.py RUN_DIR [RUN_DIR ...]"""
import csv
import glob
import os
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
GROUPS = ("rare", "abondant")


def group(diet):
    return "rare" if diet < 0.25 else "abondant" if diet > 0.75 else None


def analyse(path):
    founders = load_population(path)
    cfg = population_settings(path)[0]
    (profile, members), = founders.items()
    counts = {g: sum(group(d) == g for _, _, d in members) for g in GROUPS}
    if min(counts.values()) < 5:
        return None
    out = {"share": {g: counts[g] / len(members) for g in GROUPS}}
    meals = {g: [0, 0] for g in GROUPS}   # [own kind, other kind]
    orig = World._eat

    def eat(self, food, creature, amount):
        grp = group(creature.diet)
        if grp:
            meals[grp][0 if (food.kind == 0) == (grp == "rare") else 1] += 1
        return orig(self, food, creature, amount)
    World._eat = eat
    try:
        sim = ContinuousSimulation(random.Random(1), founders=founders, cfg=cfg)
        watched = {g: [c for c in sim.world.creatures if group(c.diet) == g][:25] for g in GROUPS}
        states = {id(c): [] for cs in watched.values() for c in cs}
        life = {g: 0 for g in GROUPS}
        for t in range(TICKS):
            if not sim.step():
                break
            for c in sim.world.creatures:
                grp = group(c.diet) if c.alive else None
                if grp:
                    life[grp] += 1
            if t % 5 == 0:
                for cs in watched.values():
                    for c in cs:
                        if c.alive:
                            states[id(c)].append(np.array(sim.world.sense(c), float))
    finally:
        World._eat = orig
    out["meals_own"] = {g: v[0] / max(1, sum(v)) for g, v in meals.items()}
    out["meals_rate"] = {g: 1000 * sum(meals[g]) / max(1, life[g]) for g in GROUPS}
    old = {g: [c for c in sim.world.creatures if group(c.diet) == g and c.age > 300] for g in GROUPS}
    out["speed"] = {g: statistics.mean(c.speed_sum / c.age for c in old[g]) for g in GROUPS}
    out["energy"] = {g: statistics.mean(c.energy / c.energy_max for c in old[g]) for g in GROUPS}
    out["blind"] = {g: statistics.mean(c.blind_ticks / c.age for c in old[g]) for g in GROUPS}
    out["blind_speed"] = {g: statistics.mean(c.blind_speed_sum / c.blind_ticks for c in old[g] if c.blind_ticks)
                          for g in GROUPS}
    labels = input_labels(profile)
    i_angle, i_value, i_dist = labels.index("Angle"), labels.index("Valeur nourr."), labels.index("Distance")
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
            own = x[:, i_value] > 0.3
            other = (x[:, i_value] < 0.05) & (x[:, i_dist] < 1.0)
            for mask, acc in ((own, own_corr), (other, other_corr)):
                if mask.sum() > 8 and np.std(x[mask, i_angle]) > 1e-6 and np.std(y[mask, 0]) > 1e-6:
                    acc.append(float(np.corrcoef(x[mask, i_angle], y[mask, 0])[0, 1]))
        sens[grp] = np.mean(per_input, axis=0) if per_input else None
        attract[grp] = (statistics.mean(own_corr) if own_corr else float("nan"),
                        statistics.mean(other_corr) if other_corr else float("nan"))
    out["sens"], out["attract"], out["labels"] = sens, attract, labels
    return out


def split_summary(run):
    """Extinct seeds, seeds split at the end (>= 10 % of each group), and the mean shares over the second half."""
    ext, split, shares = 0, 0, []
    for sd in glob.glob(os.path.join(run, "seed_*")):
        with open(os.path.join(sd, "timeline.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows or float(rows[-1]["population"]) == 0:
            ext += 1
            continue
        last = rows[-1]
        split += float(last["diet_low"]) >= 0.1 and float(last["diet_high"]) >= 0.1
        half = [r for r in rows if r["diet_low"] and float(r["tick"]) >= float(last["tick"]) / 2]
        shares.append((statistics.mean(float(r["diet_low"]) for r in half),
                       statistics.mean(float(r["diet_high"]) for r in half),
                       statistics.mean(float(r["population"]) for r in half)))
    return ext, split, shares


if __name__ == "__main__":
    for run in sys.argv[1:]:
        ext, split, shares = split_summary(run)
        alive = len(shares)
        sh = np.array(shares) if shares else np.zeros((1, 3))
        print(f"=== {os.path.basename(run)} : {ext} éteintes, scindées à la fin {split}/{alive}; 2e moitié : "
              f"spécialistes rare {sh[:, 0].mean():.2f}, abondant {sh[:, 1].mean():.2f}, population {sh[:, 2].mean():.0f}")
        paths = sorted(glob.glob(run + "/seed_*/population_finale.npz"))
        with ProcessPoolExecutor(8, initializer=worker_init, initargs=(8,)) as pool:
            results = [r for r in pool.map(analyse, paths) if r]
        if not results:
            print("  aucune population scindée\n")
            continue
        print(f"  {len(results)} populations scindées analysées ({TICKS} ticks rejoués)")
        print(f"  {'':10s} {'part':>5s} {'repas/1000':>10s} {'sa nourr.':>9s} {'énergie':>8s} {'vitesse':>8s}"
              f" {'sans vue':>8s} {'vit. sans':>9s} {'attir. sienne':>13s} {'autre':>6s}")
        for g in GROUPS:
            m = lambda k: np.nanmean([r[k][g] for r in results])  # noqa: E731
            a = np.array([r["attract"][g] for r in results])
            print(f"  {g:10s} {m('share'):5.2f} {m('meals_rate'):10.1f} {m('meals_own'):9.0%} {m('energy'):8.2f}"
                  f" {m('speed'):8.2f} {m('blind'):8.2f} {m('blind_speed'):9.2f} {np.nanmean(a[:, 0]):+13.2f}"
                  f" {np.nanmean(a[:, 1]):+6.2f}")
        diff = np.array([[r["speed"]["rare"] - r["speed"]["abondant"], r["blind"]["rare"] - r["blind"]["abondant"],
                          r["meals_rate"]["rare"] - r["meals_rate"]["abondant"]] for r in results])
        print(f"  rare plus rapide dans {int((diff[:, 0] > 0).sum())}/{len(diff)}, plus souvent sans nourriture en vue"
              f" dans {int((diff[:, 1] > 0).sum())}/{len(diff)}, moins de repas dans {int((diff[:, 2] < 0).sum())}"
              f"/{len(diff)}")
        labels = results[0]["labels"]
        print(f"  Sensibilité de la sortie à chaque entrée :  {'rare':>6s} {'abond.':>6s}")
        for i, lab in enumerate(labels):
            v = [np.mean([r["sens"][g][i] for r in results if r["sens"][g] is not None]) for g in GROUPS]
            print(f"    {lab:38s} {v[0]:6.3f} {v[1]:6.3f}")
        print()

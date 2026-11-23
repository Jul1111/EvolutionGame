"""Settings map: five scores for each run (survival, progress, variety, fairness between species, complexity).

    python -m experiments.carte experiments/results/<run> [<run> ...]

Survival   extinctions out of the seeds, and the population held at the end.
Progress   population at the end over population at 10-20 000 ticks (how much better the population lives once
           evolved), and generations reached.
Variety    how different the seeds end up: spread of their mean speed and mean size between seeds.
Fairness   (runs with several species) part of the seeds where every species is still there at the end, and the
           mean share of the smallest one.
Complexity measured on the final populations (needs population_finale.npz): each population is played for 1 500
           ticks in the world of its run; for 30 creatures, every input vector they meet and the outputs (turn,
           speed) of their network:
           - inputs used: inputs whose change (10th to 90th percentile of what the creatures meet) moves an output
             by more than 0.05 on average;
           - non-linearity: 1 - R² of the best linear fit of the outputs on the inputs, creature by creature
             (0: the behaviour is a weighted sum of what it senses; higher: interactions, thresholds). An output
             that barely moves (std under 0.05, e.g. a speed stuck at the maximum) is left out.
"""
import csv
import glob
import os
import random
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _seeds(run):
    out = {}
    for f in glob.glob(os.path.join(run, "seed_*", "timeline.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            out[int(f.split("seed_")[1].split(os.sep)[0])] = list(csv.DictReader(fh))
    return out


def _mean(rows, key, lo=None, hi=None):
    sel = [float(r[key]) for r in rows
           if (lo is None or float(r["tick"]) >= lo) and (hi is None or float(r["tick"]) < hi)]
    return float(np.mean(sel)) if sel else float("nan")


def timeline_scores(run):
    seeds = _seeds(run)
    alive = {s: r for s, r in seeds.items() if float(r[-1]["population"]) > 0}
    ext = len(seeds) - len(alive)
    early_ext = sum(1 for r in seeds.values() if float(r[-1]["population"]) == 0 and float(r[-1]["tick"]) < 20000)
    pop = [_mean(r[-10:], "population") for r in alive.values()]
    growth = [_mean(r[-10:], "population") / _mean(r, "population", 10000, 20000) for r in alive.values()]
    gens = [float(r[-1]["max_lineage_gen"]) for r in alive.values()]
    speed = [_mean(r[-10:], "mean_speed") for r in alive.values()]
    size = [_mean(r[-10:], "mean_size") for r in alive.values()]
    species = [k for k in (seeds[next(iter(seeds))][0] if seeds else {}) if k.startswith("pop__")]
    both, minority = [], []
    if len(species) > 1:
        for r in alive.values():
            counts = [float(r[-1][k]) for k in species]
            both.append(all(c > 0 for c in counts))
            minority.append(min(counts) / sum(counts))
    return {"seeds": len(seeds), "extinctions": ext, "early_extinctions": early_ext,
            "population": np.mean(pop) if pop else 0.0, "growth": np.mean(growth) if growth else float("nan"),
            "generations": np.mean(gens) if gens else 0.0,
            "speed": np.mean(speed) if speed else float("nan"), "speed_spread": np.std(speed) if speed else 0.0,
            "size_spread": np.std(size) / np.mean(size) if size else 0.0,
            "coexistence": np.mean(both) if both else float("nan"),
            "minority_share": np.mean(minority) if minority else float("nan")}


def complexity(path, creatures=30, ticks=1500, every=10, threshold=0.05):
    """(inputs used, non-linearity) of a saved population, see the module docstring. None if the file is missing."""
    if not os.path.exists(path):
        return None
    from evolution.continuous import ContinuousSimulation, load_population
    from experiments.run import population_settings
    sim = ContinuousSimulation(random.Random(1), founders=load_population(path), cfg=population_settings(path)[0])
    watched = random.Random(2).sample(sim.world.creatures, min(creatures, len(sim.world.creatures)))
    states = {id(c): [] for c in watched}
    for t in range(ticks):
        if not sim.step():
            break
        if t % every == 0:
            for c in watched:
                if c.alive:
                    states[id(c)].append(np.array(sim.world.sense(c), dtype=float))
    used, nonlin = [], []
    for c in watched:
        xs = states[id(c)]
        if len(xs) < 20:
            continue
        x = np.array(xs)
        y = np.array([c.brain.forward(v)[:2] for v in x])
        lo, hi = np.percentile(x, 10, axis=0), np.percentile(x, 90, axis=0)
        n_used = 0
        for i in range(x.shape[1]):
            if hi[i] - lo[i] < 1e-9:
                continue   # Never changes for this creature: not used
            a, b = x.copy(), x.copy()
            a[:, i], b[:, i] = lo[i], hi[i]
            d = np.abs(np.array([c.brain.forward(v)[:2] for v in b]) - np.array([c.brain.forward(v)[:2] for v in a]))
            n_used += d.mean(axis=0).max() > threshold
        used.append(n_used)
        design = np.column_stack([x, np.ones(len(x))])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        resid = ((y - design @ coef) ** 2).sum(axis=0)
        total = ((y - y.mean(axis=0)) ** 2).sum(axis=0)
        # An output that barely moves (a speed stuck at the maximum) is not a behaviour: left out
        r2 = [1 - r / t for r, t, sd in zip(resid, total, y.std(axis=0)) if sd > 0.05]
        if r2:
            nonlin.append(1 - float(np.mean(r2)))
    return (float(np.mean(used)) if used else float("nan"), float(np.mean(nonlin)) if nonlin else float("nan"))


def _complexity_job(path):
    return complexity(path)


def run_complexity(run, jobs=None):
    from concurrent.futures import ProcessPoolExecutor

    from core.kernels import worker_init
    paths = sorted(glob.glob(os.path.join(run, "seed_*", "population_finale.npz")))
    if not paths:
        return float("nan"), float("nan")
    with ProcessPoolExecutor(jobs or os.cpu_count(), initializer=worker_init, initargs=(jobs,)) as pool:
        res = [r for r in pool.map(_complexity_job, paths) if r]
    return float(np.mean([r[0] for r in res])), float(np.mean([r[1] for r in res]))


def main(argv=None):
    runs = sys.argv[1:] if argv is None else argv
    if not runs:
        raise SystemExit(__doc__)
    width = max(len(os.path.basename(r).split("_", 2)[-1]) for r in runs)
    print(f"{'run':<{width}}  éteintes (début)  population  progrès  générations  vitesse ± entre graines  "
          f"taille (écart rel.)  coexistence  part minorité  entrées utilisées  non-linéarité")
    for run in runs:
        s = timeline_scores(run)
        used, nonlin = run_complexity(run)
        name = os.path.basename(run).split("_", 2)[-1]
        print(f"{name:<{width}}  {s['extinctions']}/{s['seeds']} ({s['early_extinctions']})"
              f"          {s['population']:5.0f}      ×{s['growth']:.2f}   {s['generations']:6.0f}       "
              f"{s['speed']:.2f} ± {s['speed_spread']:.2f}              {s['size_spread']:.2f}              "
              f"{s['coexistence']:.2f}         {s['minority_share']:.2f}            {used:.1f}            {nonlin:.2f}",
              flush=True)


if __name__ == "__main__":
    main()

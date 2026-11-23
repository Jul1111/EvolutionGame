"""Selection gradient: in a running population, do the creatures that move slower leave more children?

    python -m experiments.gradient experiments/results/<run>/seed_*/population_finale.npz --ticks 20000 --skip 5000

Continues each population (births on), records every death after SKIP ticks, then gives the rank correlation
(Spearman) between the mean speed of a creature over its life and its number of children, and the mean children
per speed quartile. A negative correlation that holds across populations = slowness is selected at that density.
A correlation is not a cause: speed also depends on what the creature met.
A population from experiments/results/ is continued with the settings of its run (its run.json).
"""
import argparse
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def follow(source, seed, ticks, skip):
    from evolution.continuous import ContinuousSimulation, load_population
    from experiments.run import population_settings
    sim = ContinuousSimulation(random.Random(seed), founders=load_population(source), log_deaths=True,
                               cfg=population_settings(source)[0])
    sim.run(ticks)
    result = speed_vs_children(sim.death_log, skip)
    if result is not None:
        result["extinct"] = sim.extinct
    return result


def speed_vs_children(death_log, skip, min_deaths=20):
    """From the deaths after `skip` ticks (adults only, they could breed): rank correlation between mean speed and
    children, and the mean children and speed per speed quartile. None with fewer than `min_deaths` deaths."""
    deaths = [d for d in death_log if d["tick"] >= skip and d["age"] >= 600]
    if len(deaths) < min_deaths:
        return None
    speed = np.array([d["mean_speed"] for d in deaths])
    kids = np.array([d["children"] for d in deaths])
    q = np.quantile(speed, [0.25, 0.5, 0.75])
    groups = np.digitize(speed, q)
    by_quartile = [float(kids[groups == g].mean()) if (groups == g).any() else float("nan") for g in range(4)]
    speed_q = [float(speed[groups == g].mean()) if (groups == g).any() else float("nan") for g in range(4)]
    return {"n": len(deaths), "rho": spearman(speed, kids), "quartiles": by_quartile, "speed_q": speed_q}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--ticks", type=int, default=20000)
    parser.add_argument("--skip", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=os.cpu_count())
    args = parser.parse_args(argv)
    from experiments.run import population_settings
    for src in args.sources:
        print(f"{os.path.relpath(src, ROOT)} : réglages de {population_settings(src)[1]}")
    from core.kernels import worker_init   # One numba thread per worker when they fill the cores
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=worker_init, initargs=(args.jobs,)) as pool:
        results = list(pool.map(follow, args.sources, [args.seed] * len(args.sources),
                                [args.ticks] * len(args.sources), [args.skip] * len(args.sources)))
    print(f"\n{'population':<55} {'morts':>6} {'rho':>7}   petits par quart de vitesse (lent → rapide)")
    for src, r in zip(args.sources, results):
        label = os.path.relpath(src, ROOT)[-55:]
        if r is None:
            print(f"{label:<55} trop peu de morts")
            continue
        q = "  ".join(f"{k:.2f} (v {v:.2f})" for k, v in zip(r["quartiles"], r["speed_q"]))
        print(f"{label:<55} {r['n']:>6} {r['rho']:>+7.2f}   {q}")
    rhos = [r["rho"] for r in results if r]
    if len(rhos) > 1:
        print(f"rho moyen {statistics.mean(rhos):+.2f} ± {statistics.stdev(rhos):.2f} sur {len(rhos)} populations")


if __name__ == "__main__":
    main()

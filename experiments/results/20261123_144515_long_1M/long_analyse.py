"""Complexity over a long run: inputs used and non-linearity of each photo (population_<tick>.npz), per seed."""
import csv
import glob
import os
import re
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/Users/jul/Documents/Dev/EvolutionGame")
from core.kernels import worker_init  # noqa: E402
from experiments.carte import complexity  # noqa: E402

run = sys.argv[1]


def tick_of(path):
    m = re.search(r"population_(\d+)\.npz$", path)
    return int(m.group(1)) if m else 1_000_000


def timeline_at(seed_dir, tick):
    with open(os.path.join(seed_dir, "timeline.csv"), newline="") as f:
        rows = [r for r in csv.DictReader(f) if int(float(r["tick"])) <= tick]
    return rows[-1] if rows else None


if __name__ == "__main__":
    paths = sorted(glob.glob(os.path.join(run, "seed_*", "population_*.npz")))
    with ProcessPoolExecutor(8, initializer=worker_init, initargs=(8,)) as pool:
        scores = dict(zip(paths, pool.map(complexity, paths)))
    by_tick = {}
    for p, s in scores.items():
        if s:
            by_tick.setdefault(tick_of(p), []).append((os.path.basename(os.path.dirname(p)), s, p))
    print(f"{'tick':>8}  graines  entrées (± graines)  non-linéarité (±)  population  vitesse  générations")
    for tick in sorted(by_tick):
        rows = by_tick[tick]
        used = [s[0] for _, s, _ in rows]
        nonlin = [s[1] for _, s, _ in rows]
        tl = [timeline_at(os.path.dirname(p), tick) for _, _, p in rows]
        pop = statistics.mean(float(r["population"]) for r in tl if r)
        speed = statistics.mean(float(r["mean_speed"]) for r in tl if r)
        gen = statistics.mean(float(r["mean_lineage_gen"]) for r in tl if r)
        sd = lambda v: statistics.stdev(v) if len(v) > 1 else 0.0  # noqa: E731
        print(f"{tick:>8}  {len(rows):>7}  {statistics.mean(used):5.2f} ± {sd(used):4.2f}        "
              f"{statistics.mean(nonlin):5.3f} ± {sd(nonlin):5.3f}     {pop:7.0f}  {speed:7.2f}  {gen:9.0f}")
    print("\nPar graine (entrées / non-linéarité) :")
    seeds = sorted({s for rows in by_tick.values() for s, _, _ in rows}, key=lambda s: int(s.split("_")[1]))
    for seed in seeds:
        line = [f"{t // 1000}k {s[0]:.1f}/{s[1]:.2f}" for t in sorted(by_tick) for sd_, s, _ in by_tick[t] if sd_ == seed]
        print(f"  {seed}: " + "  ".join(line))

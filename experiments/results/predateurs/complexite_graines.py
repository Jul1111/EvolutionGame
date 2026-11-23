"""Complexity of the prey seed by seed (23/11), with the time the predators lasted in that seed.

    python experiments/results/predateurs/complexite_graines.py <run> [<run> ...]
"""
import csv
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from experiments.carte import complexity  # noqa: E402


def job(path):
    return path, complexity(path, profile="proie")


def predator_ticks(path):
    rows = list(csv.DictReader(open(os.path.join(os.path.dirname(path), "timeline.csv"), encoding="utf-8")))
    return sum(1 for r in rows if r.get("predators") not in (None, "", "0")) * 600


if __name__ == "__main__":
    paths = [p for run in sys.argv[1:] for p in sorted(glob.glob(os.path.join(run, "seed_*", "population_finale.npz")))]
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        for path, res in pool.map(job, paths):
            run = os.path.basename(os.path.dirname(os.path.dirname(path))).split("_", 2)[-1]
            seed = path.split("seed_")[1].split(os.sep)[0]
            if res:
                print(f"{run} {seed} {predator_ticks(path)} {res[0]:.2f} {res[1]:.4f}", flush=True)

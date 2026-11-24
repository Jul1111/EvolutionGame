"""Number of niches: how many specialist groups (>= 10 % of the population each) does one species keep with 2, 3 or
4 kinds of food? Per run folder: extinct seeds, distribution of the group count at the end and over the second half,
share of mixed diets.
    python nombre.py RUN_DIR [RUN_DIR ...]"""
import csv
import glob
import json
import os
import statistics
import sys
from collections import Counter

LOW = 0.10


def columns(kinds):
    return ["diet_low", "diet_high"] if kinds == 2 else [f"diet_kind{k}" for k in range(kinds)]


for run in sys.argv[1:]:
    with open(os.path.join(run, "run.json")) as f:
        overrides = json.load(f)["overrides"]
    kinds, mutation = int(overrides["FOOD_TYPES"]), overrides["DIET_MUTATION_STD"]
    cols = columns(kinds)
    ext, end, half_mean, mixed, lines = 0, Counter(), [], [], []
    for sd in sorted(glob.glob(os.path.join(run, "seed_*")), key=lambda d: int(d.split("_")[-1])):
        with open(os.path.join(sd, "timeline.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows or float(rows[-1]["population"]) == 0:
            ext += 1
            lines.append(f"  {os.path.basename(sd):8s} éteinte")
            continue
        rows = [r for r in rows if r[cols[0]]]
        last = rows[-1]
        shares = [float(last[c]) for c in cols]
        n = sum(s >= LOW for s in shares)
        end[n] += 1
        half = [r for r in rows if float(r["tick"]) >= float(last["tick"]) / 2]
        half_mean.append(statistics.mean(sum(float(r[c]) >= LOW for c in cols) for r in half))
        mixed.append(1 - sum(shares))
        lines.append(f"  {os.path.basename(sd):8s} pop {float(last['population']):4.0f}  groupes {n}  "
                     + " ".join(f"{s:.2f}" for s in shares) + f"  mixtes {1 - sum(shares):.2f}"
                     + f"  (2e moitié : {half_mean[-1]:.1f} groupes en moyenne)")
    alive = len(lines) - ext
    dist = ", ".join(f"{k} groupes : {end[k]}" for k in sorted(end))
    print(f"{kinds} sortes, mutation {mutation} : {ext} éteintes ; à la fin ({alive} vivantes) {dist} ; moyenne "
          f"{statistics.mean(k for k in end.elements()) if alive else float('nan'):.2f} groupes à la fin, "
          f"{statistics.mean(half_mean) if half_mean else float('nan'):.2f} sur la 2e moitié ; mixtes "
          f"{statistics.mean(mixed) if mixed else float('nan'):.2f}")
    print("\n".join(lines))
    print()

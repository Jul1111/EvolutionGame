"""Cycles of the seeds where the predators lasted (23/11): lagged correlation between prey and predator counts.

    python experiments/results/predateurs/cycles.py <run> [<run> ...]

For each seed with predators during at least 40 000 ticks: correlation between the change of prey and the number of
predators k samples later, k from -12 to +12 (one sample = SAMPLE_TICKS), on the detrended series (minus a moving
mean over 15 samples). Lotka-Volterra cycles: predators follow prey (positive correlation at k > 0, negative at k < 0),
period = twice the lag between the positive and the negative peak.
"""
import csv
import glob
import json
import os
import sys

import numpy as np


def detrend(x, w=15):
    pad = np.pad(x, w // 2, mode="edge")
    return x - np.convolve(pad, np.ones(w) / w, mode="valid")


for run in sys.argv[1:]:
    cfg = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))["config"]
    print(os.path.basename(run))
    for f in sorted(glob.glob(os.path.join(run, "seed_*", "timeline.csv")),
                    key=lambda p: int(p.split("seed_")[1].split(os.sep)[0])):
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        rows = [r for r in rows if float(r["tick"]) > cfg["PREDATOR_START"] and r["predators"] not in ("", "0")]
        if len(rows) * cfg["SAMPLE_TICKS"] < 40000:
            continue
        prey = detrend(np.array([float(r["prey"]) for r in rows]))
        pred = detrend(np.array([float(r["predators"]) for r in rows]))
        corr = {}
        for k in range(-12, 13):
            a, b = (prey[:len(prey) - k], pred[k:]) if k >= 0 else (prey[-k:], pred[:len(pred) + k])
            corr[k] = float(np.corrcoef(a, b)[0, 1])
        kp = max(range(1, 13), key=lambda k: corr[k])
        kn = min(range(-12, 0), key=lambda k: corr[k])
        seed = f.split("seed_")[1].split(os.sep)[0]
        print(f"  graine {seed:>2} : {len(rows) * cfg['SAMPLE_TICKS']:6d} ticks avec prédateurs ; prédateurs après les "
              f"proies : r {corr[kp]:+.2f} à +{kp * cfg['SAMPLE_TICKS']} ticks, r {corr[kn]:+.2f} à "
              f"{kn * cfg['SAMPLE_TICKS']} ; r {corr[0]:+.2f} à 0")

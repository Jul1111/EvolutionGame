"""Runs with predators (24/11): survival, cycles, flight and pursuit, seed by seed.

    python experiments/results/predateurs/analyse.py <run> [<run> ...] [--detail]

Per run: seeds where the prey / the predators are still alive at the end (and tick of the predators' extinction),
mean numbers after the predators' arrival, cycles (predators: coefficient of variation, number of swings, the lag
at which prey and predator counts are most correlated), then flight and pursuit early (first 20 000 ticks after the
arrival) and late (last quarter of the run): speed with / without the target in view, turn toward it.
"""
import csv
import glob
import json
import os
import sys

import numpy as np


def rows_of(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: (float(v) if v not in ("", None) else None) for k, v in r.items()} for r in csv.DictReader(f)]


def mean(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return float(np.mean(v)) if v else float("nan")


def swings(x, rel=0.25):
    """Number of rises and falls by more than `rel` × the mean (hysteresis on the smoothed series)."""
    if len(x) < 3 or np.mean(x) <= 0:
        return 0
    x = np.convolve(x, np.ones(3) / 3, mode="valid")
    step, n, ref, up = rel * np.mean(x), 0, x[0], None
    for v in x[1:]:
        if up is not False and v < ref - step:
            n, up, ref = n + 1, False, v
        elif up is not True and v > ref + step:
            n, up, ref = n + 1, True, v
        elif (up and v > ref) or (up is False and v < ref):
            ref = v
    return n


def best_lag(prey, pred, max_lag=10):
    """Lag (samples) with the highest correlation between prey now and predators later."""
    best, lag = -2.0, 0
    for k in range(0, max_lag + 1):
        a, b = prey[:len(prey) - k], pred[k:]
        if len(a) > 5 and a.std() > 0 and b.std() > 0:
            r = float(np.corrcoef(a, b)[0, 1])
            if r > best:
                best, lag = r, k
    return lag, best


def seed_stats(path, start, ticks):
    rows = rows_of(path)
    last = rows[-1]
    after = [r for r in rows if r["tick"] > start]
    pred = np.array([r["predators"] or 0 for r in after])
    prey = np.array([r["prey"] or 0 for r in after])
    gone = next((r["tick"] for r in after if not r["predators"]), None)
    alive = [r for r in after if r["predators"]]
    early = [r for r in after if r["tick"] <= start + 20000]
    late = [r for r in rows if r["tick"] > start + 0.75 * (ticks - start)]
    lag, corr = best_lag(prey[pred > 0].astype(float), pred[pred > 0].astype(float))
    return {
        "prey_end": last["prey"] or 0, "pred_end": last["predators"] or 0, "tick_end": last["tick"],
        "pred_gone": gone, "prey_mean": mean(alive, "prey"), "pred_mean": mean(alive, "predators"),
        "cv": float(pred[pred > 0].std() / pred[pred > 0].mean()) if (pred > 0).any() else float("nan"),
        "swings": swings(pred[pred > 0].astype(float)), "lag": lag, "corr": corr,
        **{f"{w}_{k}": mean(rs, k) for w, rs in (("early", early), ("late", late))
           for k in ("prey_speed_threat", "prey_speed_calm", "prey_toward", "pred_speed_chase", "pred_speed_idle",
                     "pred_toward", "prey_threat_frac", "kill_rate")},
    }


def main(argv):
    detail = "--detail" in argv
    for run in [a for a in argv if not a.startswith("--")]:
        info = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
        cfg, ticks = info["config"], info["ticks"]
        start = cfg["PREDATOR_START"]
        seeds = {}
        for f in sorted(glob.glob(os.path.join(run, "seed_*", "timeline.csv"))):
            seeds[int(f.split("seed_")[1].split(os.sep)[0])] = seed_stats(f, start, ticks)
        s = list(seeds.values())
        n = len(s)
        # The last line is the last multiple of SAMPLE_TICKS (79 800 for 80 000 ticks)
        both = sum(1 for x in s if x["prey_end"] and x["pred_end"] and x["tick_end"] > ticks - cfg["SAMPLE_TICKS"])
        prey_ok = sum(1 for x in s if x["prey_end"])
        print(f"\n{os.path.basename(run)}  (rendement {cfg['PREDATION_EFFICIENCY']}, digestion {cfg['PREDATOR_DIGEST']},"
              f" coût ×{cfg['PREDATOR_COST_FACTOR']}, échelle {cfg['WORLD_SCALE']})")
        gone = sorted(int(x["pred_gone"]) for x in s if x["pred_gone"])
        print(f"  coexistence à la fin {both}/{n}, proies vivantes {prey_ok}/{n}, prédateurs éteints {len(gone)}/{n}"
              f" (ticks {gone})")
        live = [x for x in s if np.isfinite(x["pred_mean"])]
        if live:
            print(f"  pendant la présence des prédateurs : proies {np.mean([x['prey_mean'] for x in live]):.0f},"
                  f" prédateurs {np.mean([x['pred_mean'] for x in live]):.1f}, CV prédateurs"
                  f" {np.nanmean([x['cv'] for x in live]):.2f}, oscillations {np.mean([x['swings'] for x in live]):.1f}")
        for w in ("early", "late"):
            def m(k, w=w):
                return np.nanmean([x[f"{w}_{k}"] for x in s])
            print(f"  {'début' if w == 'early' else 'fin  '} : proies vitesse {m('prey_speed_threat'):.2f} avec /"
                  f" {m('prey_speed_calm'):.2f} sans prédateur en vue, virage vers lui {m('prey_toward'):+.3f},"
                  f" en vue {m('prey_threat_frac'):.1%} ; prédateurs vitesse {m('pred_speed_chase'):.2f} /"
                  f" {m('pred_speed_idle'):.2f}, virage vers la proie {m('pred_toward'):+.3f},"
                  f" proies/1000 t {m('kill_rate'):.2f}")
        if detail:
            for k, x in seeds.items():
                print(f"    graine {k:2d} : fin {x['tick_end']:.0f}  proies {x['prey_end']:.0f}  prédateurs"
                      f" {x['pred_end']:.0f}  moy. {x['prey_mean']:.0f}/{x['pred_mean']:.1f}  CV {x['cv']:.2f}"
                      f"  oscill. {x['swings']}  décalage {x['lag']} (r {x['corr']:.2f})"
                      f"  fuite fin {x['late_prey_toward']:+.3f}  poursuite fin {x['late_pred_toward']:+.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])

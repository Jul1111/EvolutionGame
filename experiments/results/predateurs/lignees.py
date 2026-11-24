"""Evolved predators (24/11): fate of each predator lineage, seed by seed, in several runs.

    python experiments/results/predateurs/lignees.py <run> [<run> ...]

A seed's lineage: the file PREDATOR_POPULATION gives it (seed s: path (s - 1) mod n), or with --cycle its starting
population (co-evolved prey and predators). Per seed: predators still alive at the end, or the tick they died out
(measured from their arrival), and the numbers at the end.
"""
import csv
import glob
import json
import os
import sys


def lineage_of(info, seed):
    cfg = info["config"]
    files = cfg.get("PREDATOR_POPULATION") if cfg.get("PREDATION") else None
    if not files:
        files = info["from_population"] if info.get("cycle") else None
    if not files:
        return "aléatoires"
    path = files if isinstance(files, str) else files[(seed - 1) % len(files)]
    parts = path.split(os.sep)
    run = next(p for p in parts if p.startswith("2026"))
    return run.split("_", 2)[2] + " g" + next(p for p in parts if p.startswith("seed_"))[5:]


def seed_fate(path, start):
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
    after = [r for r in rows if float(r["tick"]) > start]
    gone = next((float(r["tick"]) - start for r in after if not float(r["predators"] or 0)), None)
    last = rows[-1]
    return gone, float(last["tick"]), float(last["prey"] or 0), float(last["predators"] or 0)


def main(argv):
    table = {}
    names = []
    for run in argv:
        info = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
        cfg = info["config"]
        start = cfg["PREDATOR_START"] if cfg["PREDATION"] else 0
        name = info["name"]
        names.append(name)
        print(f"\n{name}")
        for f in sorted(glob.glob(os.path.join(run, "seed_*", "timeline.csv")),
                        key=lambda p: int(p.split("seed_")[1].split(os.sep)[0])):
            seed = int(f.split("seed_")[1].split(os.sep)[0])
            lineage = lineage_of(info, seed)
            gone, end, prey, pred = seed_fate(f, start)
            last_ok = end > info["ticks"] - cfg["SAMPLE_TICKS"]
            kept = gone is None and pred > 0 and last_ok
            table.setdefault(lineage, {}).setdefault(name, []).append(kept)
            fate = "gardés" if kept else (f"éteints après {gone:.0f} ticks" if gone is not None
                                          else f"run arrêté au tick {end:.0f}")
            print(f"  graine {seed:2d}  {lineage:22s}  prédateurs {fate:28s}  fin : proies {prey:.0f}, "
                  f"prédateurs {pred:.0f}")
    print("\nPrédateurs gardés jusqu'à la fin, par lignée :")
    print(f"  {'lignée':22s}  " + "  ".join(f"{n:>24s}" for n in names))
    for lineage, runs in sorted(table.items()):
        cells = [f"{sum(runs[n])}/{len(runs[n])}" if n in runs else "-" for n in names]
        print(f"  {lineage:22s}  " + "  ".join(f"{c:>24s}" for c in cells))
    totals = [f"{sum(sum(r.get(n, [])) for r in table.values())}/{sum(len(r.get(n, [])) for r in table.values())}"
              for n in names]
    print(f"  {'total':22s}  " + "  ".join(f"{c:>24s}" for c in totals))


if __name__ == "__main__":
    main(sys.argv[1:])

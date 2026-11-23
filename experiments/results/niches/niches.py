"""Coexistence by niches: per run, extinctions, coexistence of the two species, elimination time, diets at the end."""
import csv
import glob
import os
import statistics
import sys

A, B = "regime", "regime_faim"
for run in sys.argv[1:]:
    ext = coexist = 0
    elim, wins, split, rows_out = [], {A: 0, B: 0}, 0, []
    for sd in sorted(glob.glob(os.path.join(run, "seed_*")), key=lambda d: int(d.split("_")[-1])):
        with open(os.path.join(sd, "timeline.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        last = rows[-1]
        a, b = float(last[f"pop__{A}"]), float(last[f"pop__{B}"])
        line = f"  {os.path.basename(sd):8s} pop {A} {a:4.0f}  {B} {b:4.0f}"
        if "diet_mean" in last and last["diet_mean"]:
            da = last.get(f"diet__{A}") or ""
            db = last.get(f"diet__{B}") or ""
            line += f"  régime moyen {A} {float(da):.2f}" if da else f"  régime moyen {A}   - "
            line += f"  {B} {float(db):.2f}" if db else f"  {B}   - "
            line += f"  spécialistes 0/1 : {float(last['diet_low']):.2f} / {float(last['diet_high']):.2f}"
        rows_out.append(line)
        if a == 0 and b == 0:
            ext += 1
            continue
        if a > 0 and b > 0:
            coexist += 1
            if "diet_mean" in last and last.get(f"diet__{A}") and last.get(f"diet__{B}"):
                if abs(float(last[f"diet__{A}"]) - float(last[f"diet__{B}"])) > 0.5:
                    split += 1
            continue
        wins[A if a > 0 else B] += 1
        loser = f"pop__{B}" if a > 0 else f"pop__{A}"
        elim.append(next(float(r["tick"]) for r in rows if float(r[loser]) == 0))
    alive = len(rows_out) - ext
    print(f"{os.path.basename(run)} : {ext} éteintes, coexistence {coexist}/{alive}"
          f" (dont espèces sur des nourritures différentes : {split}), victoires {A} {wins[A]} / {B} {wins[B]},"
          f" élimination médiane {statistics.median(elim) if elim else float('nan'):.0f}")
    print("\n".join(rows_out))
    print()

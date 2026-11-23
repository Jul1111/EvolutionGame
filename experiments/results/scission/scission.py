"""Does one species keep two specialist groups? Per run: extinctions, seeds split at the end (>= 10 % specialists of
each food), how long the split lasted, and the share of generalists."""
import csv
import glob
import os
import statistics
import sys


def split(r, low=0.10):
    return r["diet_low"] is not None and float(r["diet_low"]) >= low and float(r["diet_high"]) >= low


for run in sys.argv[1:]:
    ext, end_split, lines, durations = 0, 0, [], []
    for sd in sorted(glob.glob(os.path.join(run, "seed_*")), key=lambda d: int(d.split("_")[-1])):
        with open(os.path.join(sd, "timeline.csv"), newline="") as f:
            every = list(csv.DictReader(f))
        rows = [r for r in every if r["diet_low"]]
        last = rows[-1] if rows else None
        if not last or float(every[-1]["population"]) == 0:
            ext += 1
            lines.append(f"  {os.path.basename(sd):8s} éteinte")
            continue
        lo, hi = float(last["diet_low"]), float(last["diet_high"])
        is_split = split(last)
        end_split += is_split
        # Last tick at which both groups were there (the split ended there if it is not split now)
        last_split = max((float(r["tick"]) for r in rows if split(r)), default=0.0)
        if not is_split:
            durations.append(last_split)
        half = [r for r in rows if float(r["tick"]) >= float(rows[-1]["tick"]) / 2]
        share_split = sum(split(r) for r in half) / len(half)
        lines.append(f"  {os.path.basename(sd):8s} pop {float(last['population']):4.0f}  spécialistes vert {lo:.2f}"
                     f"  jaune {hi:.2f}  généralistes {1 - lo - hi:.2f}  "
                     + (f"SCINDÉE ({share_split:.0%} du temps sur la 2e moitié)" if is_split
                        else f"un seul groupe depuis ~{last_split:.0f} ticks"))
    alive = len(lines) - ext
    print(f"{os.path.basename(run)} : {ext} éteintes, scindées à la fin {end_split}/{alive}, "
          f"fin de la scission (médiane, les autres) {statistics.median(durations) if durations else float('nan'):.0f}"
          " ticks")
    print("\n".join(lines))
    print()

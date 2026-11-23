import csv, glob, os, statistics, sys
print(f"{'run':24s} complet/faim gagne   élimination médiane (ticks)")
for run in sorted(glob.glob("experiments/results/20261123_*_carte_*")):
    wins = {"complet": 0, "complet_faim": 0, "aucun": 0, "deux": 0}; elim = []
    for sd in sorted(glob.glob(run + "/seed_*")):
        rows = list(csv.DictReader(open(sd + "/timeline.csv")))
        a = [float(r["pop__complet"]) for r in rows]; b = [float(r["pop__complet_faim"]) for r in rows]
        last = rows[-1]
        if a[-1] > 0 and b[-1] > 0: wins["deux"] += 1; continue
        if a[-1] == 0 and b[-1] == 0: wins["aucun"] += 1; continue
        wins["complet" if a[-1] > 0 else "complet_faim"] += 1
        loser = b if a[-1] > 0 else a
        elim.append(next(float(r["tick"]) for r, p in zip(rows, loser) if p == 0))
    name = os.path.basename(run)[16:]
    print(f"{name:24s} {wins['complet']}/{wins['complet_faim']} (deux {wins['deux']}, aucun {wins['aucun']})   "
          f"{statistics.median(elim) if elim else float('nan'):8.0f}")

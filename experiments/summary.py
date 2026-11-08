"""Summary of one or several experiments (folders of experiments/results).

    python -m experiments.summary experiments/results/<run A> experiments/results/<run B> --last 10

For each run and profile: mean over the seeds of the last N generations, ± the standard deviation between seeds.
Two runs whose intervals overlap are not told apart: add seeds before concluding.
"""
import argparse
import csv
import glob
import os
import statistics

METRICS = ["ticks", "alive", "mean_food", "mean_speed", "blind_frac", "mean_poison", "obstacle_frac"]


def _float(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def load(run_dir):
    """{profile: {seed: [rows]}}"""
    data = {}
    for path in sorted(glob.glob(os.path.join(run_dir, "seed_*", "profiles", "*", "stats.csv"))):
        parts = path.split(os.sep)
        seed, profile = parts[-4], parts[-2]
        with open(path, newline="", encoding="utf-8") as f:
            data.setdefault(profile, {})[seed] = list(csv.DictReader(f))
    return data


def summarize(run_dir):
    """Writes summary.csv: profile, generation, then mean and std over the seeds of each metric."""
    rows = []
    for profile, seeds in load(run_dir).items():
        n_gen = max(len(r) for r in seeds.values())
        for g in range(n_gen):
            row = {"profile": profile, "generation": g + 1}
            for m in METRICS:
                values = [_float(r[g].get(m)) for r in seeds.values() if g < len(r)]
                values = [v for v in values if v is not None]
                row[m + "_mean"] = round(statistics.mean(values), 3) if values else ""
                row[m + "_std"] = round(statistics.stdev(values), 3) if len(values) > 1 else ""
            row["seeds"] = len(seeds)
            rows.append(row)
    if rows:
        with open(os.path.join(run_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return rows


def last_window(run_dir, last):
    """{profile: {metric: (mean, std between seeds, number of seeds)}} on the last `last` generations of each seed."""
    out = {}
    for profile, seeds in load(run_dir).items():
        out[profile] = {}
        for m in METRICS:
            per_seed = []
            for rows in seeds.values():
                vals = [_float(r.get(m)) for r in rows[-last:]]
                vals = [v for v in vals if v is not None]
                if vals:
                    per_seed.append(statistics.mean(vals))
            if per_seed:
                std = statistics.stdev(per_seed) if len(per_seed) > 1 else float("nan")
                out[profile][m] = (statistics.mean(per_seed), std, len(per_seed))
    return out


def print_table(run_dirs, last=10):
    print(f"\nMoyenne des {last} dernières générations, ± écart-type entre graines")
    head = f"{'expérience':<34} {'profil':<14} {'graines':>7}" + "".join(f"{m:>18}" for m in METRICS)
    print(head)
    for run_dir in run_dirs:
        for profile, metrics in last_window(run_dir, last).items():
            n = next(iter(metrics.values()))[2] if metrics else 0
            cells = "".join(f"{metrics[m][0]:>10.2f} ±{metrics[m][1]:>6.2f}" if m in metrics else f"{'':>18}"
                            for m in METRICS)
            print(f"{os.path.basename(run_dir.rstrip(os.sep))[:34]:<34} {profile:<14} {n:>7}{cells}")


# ---------- continuous evolution (timeline.csv) ----------

TIMELINE_METRICS = ["population", "births", "food_rate", "poison_rate", "mean_lineage_gen", "mean_speed",
                    "mean_age_at_death", "cap_blocked"]


def load_timelines(run_dir):
    """{seed: [rows]}"""
    out = {}
    for path in sorted(glob.glob(os.path.join(run_dir, "seed_*", "timeline.csv"))):
        with open(path, newline="", encoding="utf-8") as f:
            out[path.split(os.sep)[-2]] = list(csv.DictReader(f))
    return out


def summarize_timeline(run_dir):
    """summary.csv: per sample (tick), mean and std over the seeds still alive, and how many are extinct."""
    timelines = load_timelines(run_dir)
    n = max((len(r) for r in timelines.values()), default=0)
    rows = []
    for i in range(n):
        alive = [r[i] for r in timelines.values() if i < len(r) and _float(r[i]["population"])]
        row = {"sample": i + 1, "tick": next((r[i]["tick"] for r in timelines.values() if i < len(r)), ""),
               "seeds_alive": len(alive), "seeds": len(timelines)}
        for m in TIMELINE_METRICS:
            vals = [v for v in (_float(r.get(m)) for r in alive) if v is not None]
            row[m + "_mean"] = round(statistics.mean(vals), 3) if vals else ""
            row[m + "_std"] = round(statistics.stdev(vals), 3) if len(vals) > 1 else ""
        rows.append(row)
    if rows:
        with open(os.path.join(run_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return rows


def print_timeline_table(run_dirs, last=10):
    print(f"\nÉvolution continue : moyenne des {last} derniers relevés de chaque graine survivante, ± écart-type entre graines")
    print(f"{'expérience':<34} {'extinctions':>11}" + "".join(f"{m:>20}" for m in TIMELINE_METRICS))
    for run_dir in run_dirs:
        timelines = load_timelines(run_dir)
        extinct = sum(1 for r in timelines.values() if r and _float(r[-1]["population"]) == 0)
        cells = ""
        for m in TIMELINE_METRICS:
            per_seed = []
            for rows in timelines.values():
                if rows and _float(rows[-1]["population"]):
                    vals = [v for v in (_float(x.get(m)) for x in rows[-last:]) if v is not None]
                    if vals:
                        per_seed.append(statistics.mean(vals))
            if per_seed:
                std = statistics.stdev(per_seed) if len(per_seed) > 1 else float("nan")
                cells += f"{statistics.mean(per_seed):>12.2f} ±{std:>6.2f}"
            else:
                cells += f"{'':>20}"
        print(f"{os.path.basename(run_dir.rstrip(os.sep))[:34]:<34} {f'{extinct}/{len(timelines)}':>11}{cells}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--last", type=int, default=10)
    args = parser.parse_args()
    continuous = [r for r in args.runs if load_timelines(r)]
    generational = [r for r in args.runs if r not in continuous]
    for run in continuous:
        summarize_timeline(run)
    for run in generational:
        summarize(run)
    if generational:
        print_table(generational, args.last)
    if continuous:
        print_timeline_table(continuous, args.last)


if __name__ == "__main__":
    main()

"""Progress of experiment runs, as a bar in %: read from what each seed has already written to disk.

    python -m experiments.progress                 runs in progress (results/ folders without summary.csv)
    python -m experiments.progress <run folder>    that run
    python -m experiments.progress --suivre        refresh every 5 s until they are finished (Ctrl+C to quit)

experiments.run shows the same bar while it waits for its seeds. A seed counts the ticks of its last timeline.csv
line; it is complete once its final population is saved or it died out. A run is complete once summary.csv exists.
"""
import argparse
import csv
import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "experiments", "results")


def seed_ticks(seed_dir, ticks):
    """Ticks played by a seed (all of them once it is finished, extinction included)."""
    if os.path.exists(os.path.join(seed_dir, "population_finale.npz")):
        return ticks
    path = os.path.join(seed_dir, "timeline.csv")
    if not os.path.exists(path):
        return 0
    last = None
    with open(path, newline="", encoding="utf-8") as f:
        for last in csv.DictReader(f):
            pass
    if last is None:
        return 0
    if float(last["population"]) == 0:
        return ticks   # Died out: nothing more to play
    return min(ticks, int(float(last["tick"])))


def run_progress(out_dir):
    """(fraction done, seeds finished, seeds, seconds since start) of a run folder."""
    with open(os.path.join(out_dir, "run.json"), encoding="utf-8") as f:
        meta = json.load(f)
    ticks, seeds = meta["ticks"], meta["seeds"]
    started = os.path.getmtime(os.path.join(out_dir, "run.json"))
    if os.path.exists(os.path.join(out_dir, "summary.csv")):
        return 1.0, len(seeds), len(seeds), os.path.getmtime(os.path.join(out_dir, "summary.csv")) - started
    played = [seed_ticks(os.path.join(out_dir, f"seed_{s}"), ticks) for s in seeds]
    return (sum(played) / (ticks * len(seeds)) if seeds else 1.0, sum(p >= ticks for p in played), len(seeds),
            time.time() - started)


def duration(seconds):
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600} h {seconds % 3600 // 60:02d}"
    return f"{seconds // 60} min {seconds % 60:02d}"


def bar(fraction, done, total, elapsed, width=30):
    """[##########--------------------]  33 %  5/16 graines  12 min 04 écoulées, ~24 min 10 restantes"""
    filled = int(round(width * fraction))
    text = f"[{'#' * filled}{'-' * (width - filled)}] {100 * fraction:3.0f} %  {done}/{total} graines  " \
           f"{duration(elapsed)} écoulées"
    if 0.01 <= fraction < 1:
        text += f", ~{duration(elapsed * (1 - fraction) / fraction)} restantes"
    return text


def running_runs():
    """Run folders not finished yet (no summary.csv), oldest first."""
    return [d for d in sorted(glob.glob(os.path.join(RESULTS, "*")))
            if os.path.exists(os.path.join(d, "run.json")) and not os.path.exists(os.path.join(d, "summary.csv"))]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="*", help="Dossiers de runs (défaut : ceux en cours)")
    parser.add_argument("--suivre", action="store_true", help="Rafraîchir toutes les 5 s jusqu'à la fin")
    args = parser.parse_args(argv)
    while True:
        runs = args.runs or running_runs()
        if not runs:
            print("Aucun run en cours.")
            return
        lines = []
        for d in runs:
            fraction, done, total, elapsed = run_progress(d)
            lines.append(f"{os.path.basename(d)}\n  {bar(fraction, done, total, elapsed)}")
        print("\n".join(lines))
        if not args.suivre or all(run_progress(d)[0] >= 1 for d in runs):
            return
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            return
        if sys.stdout.isatty():
            sys.stdout.write(f"\033[{2 * len(lines)}F\033[J")   # Redraw in place


if __name__ == "__main__":
    main()

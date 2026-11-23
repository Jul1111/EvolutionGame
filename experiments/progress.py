"""Progress of experiment runs, as a bar in %: read from what each seed has already written to disk.

    python -m experiments.progress                 lots and runs in progress
    python -m experiments.progress <run folder>    that run
    python -m experiments.progress --suivre        refresh every 5 s until they are finished (Ctrl+C to quit)

A lot (experiments.lot) shows an overall bar, then one indented bar per run (finished, in progress, waiting).
experiments.run shows the bar of its run while it waits for its seeds. A seed counts the ticks of its last timeline.csv
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


def render(lot):
    """(text, overall fraction) of a lot state (experiments.lot): an overall bar, then one indented bar per run.
    Runs are weighted by their cost estimate (seed-ticks times world surface)."""
    total_w = sum(r["weight"] for r in lot["runs"]) or 1
    width = max(len(r["name"]) for r in lot["runs"])
    lines, done_w = [], 0.0
    for r in lot["runs"]:
        if r["status"] == "en attente" or not r["dir"] or not os.path.exists(os.path.join(r["dir"], "run.json")):
            fraction, line = 0.0, f"[{'-' * 30}]   0 %  {r['status']}"
        else:
            fraction, finished, total, elapsed = run_progress(r["dir"])
            line = bar(fraction, finished, total, elapsed)
            if r["status"].startswith("échec"):
                line += f"  {r['status']}"
        done_w += r["weight"] * fraction
        lines.append(f"    {r['name']:<{width}}  {line}")
    fraction = 1.0 if lot.get("finished") else done_w / total_w
    elapsed = (lot.get("finished") or time.time()) - lot["started"]
    runs_done = sum(r["status"] == "fini" for r in lot["runs"])
    head = bar(fraction, runs_done, len(lot["runs"]), elapsed).replace("graines", "runs")
    return f"Lot {os.path.basename(lot['file'])}  {head}\n" + "\n".join(lines), fraction


def running_lots():
    """States of the lots not finished, oldest first (a lot whose process was killed stays here: its file says
    so only by a run left "en cours")."""
    out = []
    for path in sorted(glob.glob(os.path.join(RESULTS, "lots", "*.json"))):
        with open(path, encoding="utf-8") as f:
            lot = json.load(f)
        if not lot.get("finished") and not any(r["status"].startswith("échec") for r in lot["runs"]):
            out.append(lot)
    return out


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
        lots = [] if args.runs else running_lots()
        in_lots = {os.path.abspath(r["dir"]) for lot in lots for r in lot["runs"] if r["dir"]}
        runs = args.runs or [d for d in running_runs() if os.path.abspath(d) not in in_lots]
        if not runs and not lots:
            print("Aucun run en cours.")
            return
        blocks = [render(lot)[0] for lot in lots]
        for d in runs:
            fraction, done, total, elapsed = run_progress(d)
            blocks.append(f"{os.path.basename(d)}\n    {bar(fraction, done, total, elapsed)}")
        text = "\n".join(blocks)
        print(text)
        if not args.suivre or (all(run_progress(d)[0] >= 1 for d in runs) and all(render(lot)[1] >= 1 for lot in lots)):
            return
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            return
        if sys.stdout.isatty():
            sys.stdout.write(f"\033[{text.count(chr(10)) + 1}F\033[J")   # Redraw in place


if __name__ == "__main__":
    main()

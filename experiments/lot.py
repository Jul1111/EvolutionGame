"""A batch (lot) of experiment runs, one after the other, with an overall progress bar and one bar per run.

    python -m experiments.lot experiments/lots/<fichier>.txt

The file: one run per line, the arguments of experiments.run (# starts a comment, a line ending with \\ goes on).
{run:NAME} is replaced by the results folder of the run of this lot named NAME (a later run can start from the
populations of an earlier one):

    --name seul_complet --profiles complet --seeds 1 2 3 4 --ticks 120000
    --name duel --profiles complet complet_faim --seeds 1 2 3 4 --ticks 120000 \\
        --from-population {run:seul_complet}/seed_{seed}/population_finale.npz <autre>.npz

The plan is written to experiments/results/lots/<date>_<fichier>.json (read by experiments.progress, also from
another terminal) and the output of the runs to the .log next to it. A run that fails stops the lot.
experiments.pause pauses the lot and its runs.
"""
import json
import os
import shlex
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
LOTS = os.path.join(ROOT, "experiments", "results", "lots")


def read_lot(path):
    """Lines of a lot file -> list of argument lists."""
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\\\n", " ")
    runs = []
    for line in text.splitlines():
        args = shlex.split(line, comments=True)
        if args:
            runs.append(args)
    return runs


def plan(runs):
    """What the lot will do, before any run: name, seeds, ticks and weight (cost estimate: seed-ticks times the
    world surface) of each run. Typos in the arguments stop here, not after hours."""
    import config
    from experiments.run import build_parser, parse_overrides
    parser = build_parser()
    out = []
    for args in runs:
        try:
            parsed = parser.parse_args(args)
        except SystemExit:
            raise SystemExit(f"Ligne invalide dans le lot : {' '.join(args)}")
        scale = parse_overrides(parsed.set).get("WORLD_SCALE", config.WORLD_SCALE)
        out.append({"name": parsed.name, "args": args, "seeds": parsed.seeds, "ticks": parsed.ticks,
                    "weight": len(parsed.seeds) * parsed.ticks * scale ** 2, "dir": None, "status": "en attente"})
    names = [r["name"] for r in out]
    if len(set(names)) != len(names):
        raise SystemExit("Deux runs du lot ont le même --name")
    return out


def resolve(args, done):
    """{run:NAME} -> results folder of that run of the lot (relative to the project)."""
    out = []
    for a in args:
        for name, d in done.items():
            a = a.replace(f"{{run:{name}}}", os.path.relpath(d, ROOT))
        if "{run:" in a:
            raise SystemExit(f"Run inconnu ou pas encore fait dans {a}")
        out.append(a)
    return out


def save(state, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__)
    from experiments.progress import render
    runs = plan(read_lot(argv[0]))
    os.makedirs(LOTS, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = os.path.join(LOTS, f"{stamp}_{os.path.splitext(os.path.basename(argv[0]))[0]}")
    state = {"file": os.path.relpath(os.path.abspath(argv[0]), ROOT), "started": time.time(), "finished": None,
             "runs": runs}
    save(state, base + ".json")
    tty = sys.stdout.isatty()
    print(f"Lot de {len(runs)} runs → {os.path.relpath(base, ROOT)}.json (sortie des runs : .log)")
    done, last_step = {}, -1
    with open(base + ".log", "a", encoding="utf-8") as log:
        for run in runs:
            run["dir"] = os.path.join(ROOT, "experiments", "results",
                                      time.strftime("%Y%m%d_%H%M%S") + "_" + run["name"])
            run["status"] = "en cours"
            save(state, base + ".json")
            args = resolve(run["args"], done) + ["--out-dir", run["dir"]]
            log.write(f"\n=== {run['name']} : {' '.join(args)}\n")
            log.flush()
            child = subprocess.Popen([sys.executable, "-m", "experiments.run", *args], cwd=ROOT, stdout=log,
                                     stderr=subprocess.STDOUT)
            while child.poll() is None:
                time.sleep(2)
                text, fraction = render(state)
                if tty:
                    sys.stdout.write("\033[H\033[J" + text + "\n")
                    sys.stdout.flush()
                elif int(fraction * 20) > last_step:   # A log: every 5 %
                    last_step = int(fraction * 20)
                    print(text.splitlines()[0], flush=True)
            run["status"] = "fini" if child.returncode == 0 else f"échec (code {child.returncode})"
            save(state, base + ".json")
            if child.returncode != 0:
                print(f"{run['name']} : échec, lot arrêté (voir {os.path.relpath(base, ROOT)}.log)")
                return 1
            done[run["name"]] = run["dir"]
    state["finished"] = time.time()
    save(state, base + ".json")
    print(render(state)[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())

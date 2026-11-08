"""Headless experiments of continuous evolution: several seeds of the same setup, run in parallel, results kept.

    python -m experiments.run --name base --seeds 1 2 3 4 --ticks 120000
    python -m experiments.run --name moins_nourr --set FOOD_COUNT=30
    python -m experiments.run --name suite --from-population saves/populations/<fichier>.npz
    python -m experiments.run --name suite --from-population experiments/results/<run>/seed_{seed}/population_finale.npz

Each run writes experiments/results/<date>_<name>/:
    run.json                    command, git commit, every constant of config.py (after --set)
    seed_<n>/timeline.csv       one line every SAMPLE_TICKS ticks
    seed_<n>/population_finale.npz   living population at the end (not after an extinction)
    summary.csv                 per sample: mean and std over the seeds still alive
Never reads saves/settings.json: a run depends only on config.py and its --set options.
Rule of thumb: no conclusion on fewer than 4-5 seeds. An extinction ends a seed and is counted.
Long runs: launch them from a terminal (about 7 min per seed for 120 000 ticks on a 2-core machine).
"""
import argparse
import ast
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RESULTS = os.path.join(ROOT, "experiments", "results")


def parse_value(text):
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text   # A bare word: a string


def apply_overrides(overrides):
    import config
    for name, value in overrides.items():
        if not hasattr(config, name):
            raise SystemExit(f"Constante inconnue dans config.py : {name}")
        default = getattr(config, name)
        if isinstance(default, float) and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        setattr(config, name, value)
    config.refresh_derived()


def run_seed(seed, out_dir, overrides, ticks, profiles, population_file):
    """One seed, in its own process (config is a module: one process = one set of settings)."""
    import config
    from evolution.continuous import ContinuousSimulation, save_population, load_population
    apply_overrides(overrides)
    config.SEED = seed
    config.ACTIVE_PROFILES = list(profiles)
    seed_dir = os.path.join(out_dir, f"seed_{seed}")
    founders = load_population(population_file.format(seed=seed)) if population_file else None
    sim = ContinuousSimulation(random.Random(seed), os.path.join(seed_dir, "timeline.csv"), founders=founders)
    start = time.time()
    played = sim.run(ticks)
    if not sim.extinct:
        save_population(sim, os.path.join(seed_dir, "population_finale.npz"))
    end = f"EXTINCTION au tick {sim.world.tick}" if sim.extinct else f"population {len(sim.world.creatures)}"
    return f"graine {seed} : {played} ticks en {time.time() - start:.0f} s, {end}"


def git_state():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,
                                         stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                             text=True, stderr=subprocess.DEVNULL).strip())
        return commit + ("-modifié" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="Nom court de l'expérience (dossier de résultats)")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--ticks", type=int, default=60000, help="Durée (arrêt avant en cas d'extinction)")
    parser.add_argument("--profiles", nargs="+", default=None, help="Espèces fondatrices (défaut : ACTIVE_PROFILES)")
    parser.add_argument("--from-population", default=None,
                        help="Population sauvegardée de départ (.npz). {seed} est remplacé par le numéro de graine")
    parser.add_argument("--set", nargs="*", default=[], metavar="NOM=VALEUR", help="Remplace une constante de config.py")
    parser.add_argument("--jobs", type=int, default=os.cpu_count(), help="Graines lancées en parallèle")
    args = parser.parse_args(argv)

    import config
    overrides = {}
    for item in args.set:
        name, _, value = item.partition("=")
        overrides[name.strip().upper()] = parse_value(value)
    apply_overrides(overrides)   # In this process too: run.json records the real values, and typos stop here
    profiles = args.profiles or config.ACTIVE_PROFILES
    from brain.profiles import PROFILES
    unknown = [p for p in profiles if p not in PROFILES]
    if unknown:
        raise SystemExit(f"Profil inconnu : {', '.join(unknown)} (disponibles : {', '.join(PROFILES)})")

    out_dir = os.path.join(RESULTS, time.strftime("%Y%m%d_%H%M%S") + "_" + args.name)
    os.makedirs(out_dir)
    meta = {"name": args.name, "ticks": args.ticks, "from_population": args.from_population,
            "command": " ".join(sys.argv), "git": git_state(), "seeds": args.seeds, "profiles": list(profiles),
            "overrides": overrides,
            "config": {n: getattr(config, n) for n in dir(config) if n.isupper() and n != "SAVE_DIR"
                       and isinstance(getattr(config, n), (int, float, str, bool, list, tuple))}}
    with open(os.path.join(out_dir, "run.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"{args.name} : {len(args.seeds)} graines × {args.ticks} ticks, profils {', '.join(profiles)} "
          f"→ {os.path.relpath(out_dir, ROOT)}")

    with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_seed, s, out_dir, overrides, args.ticks, profiles, args.from_population)
                   for s in args.seeds]
        for fut in futures:
            print(fut.result())

    from experiments.summary import summarize_timeline, print_timeline_table
    summarize_timeline(out_dir)
    print_timeline_table([out_dir])


if __name__ == "__main__":
    main()

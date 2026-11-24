"""Headless experiments of continuous evolution: several seeds of the same setup, run in parallel, results kept.

    python -m experiments.run --name base --seeds 1 2 3 4 --ticks 120000
    python -m experiments.run --name moins_nourr --set FOOD_COUNT=30
    python -m experiments.run --name suite --from-population saves/populations/<fichier>.npz
    python -m experiments.run --name duel_faim --profiles complet complet_faim --ticks 120000     (duel d'espèces)
    python -m experiments.run --name suite --from-population experiments/results/<run>/seed_{seed}/population_finale.npz
    python -m experiments.run --name duel_evolues --profiles complet complet_faim \
        --from-population experiments/results/<run A>/seed_{seed}/population_finale.npz \
                          experiments/results/<run B>/seed_{seed}/population_finale.npz
        (duel of evolved populations: INITIAL_POPULATION founders, an equal share drawn from each file)
    ... --replica 1      same founders, another chance in the world (is the winner of a duel luck or the lineages?)
    ... --shift 1 --from-population <run A>/seed_{seed}/... <run B>/seed_{pair}/...
        ({pair}: the seed `shift` places further in --seeds, cyclically: each population meets other opponents)
    ... --cycle --from-population <file 1> <file 2> ...
        (seed s starts from file (s - 1) mod n alone, instead of an equal share of each file)
    ... --from-population <prey>/seed_{seed}/... --set PREDATION=True PREDATOR_POPULATION="['<file>', ...]"
        (evolved prey; the predators of the file are left out, the arriving ones are drawn from PREDATOR_POPULATION)

Several runs in one command (one after the other, an overall progress bar and one bar per run):
    python -m experiments.run --name cout --varie ENERGY_MOVE_COST=0.015,0.03,0.06     (3 runs: cout_0.015, ...)
    python -m experiments.run --name rejeu ... --replica 1 2                           (rejeu_r1, rejeu_r2)
    python -m experiments.run --name croise ... --shift 0 1 2                          (croise_s0, croise_s1, ...)
Several --varie, --replica and --shift values: every combination.

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


def build_settings(overrides, **extra):
    """The settings of a run: config.py with the --set overrides (and `extra`, e.g. the seed). The config module is
    not touched: every run, in this process or another, has its own copy."""
    import config
    values = {}
    known = config.Settings().__dict__
    for name, value in overrides.items():
        if name not in known:
            raise SystemExit(f"Constante inconnue dans config.py : {name}")
        default = getattr(config, name)
        if isinstance(default, float) and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        values[name] = value
    return config.Settings(**values, **extra)


def population_settings(path, **extra):
    """Settings of the run a population file comes from: every value its run.json recorded (two folders up:
    results/<run>/seed_<n>/population_finale.npz), so it is continued in the world where it evolved, even if
    config.py changed since. Names that are no longer settings (removed, or derived like WORLD_WIDTH) are skipped.
    A file without run.json (saves/populations/) gets config.py. `extra` goes on top.
    Returns (settings, where they come from)."""
    import config
    known = config.Settings().__dict__
    meta_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), "run.json")
    values, source = {}, "config.py"
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            recorded = json.load(f).get("config", {})
        values = {n: v for n, v in recorded.items() if n in known and n != "SAVE_DIR"}
        source = os.path.relpath(meta_path, ROOT)
    values.update(extra)
    return config.Settings(**values), source


def mixed_founders(paths, total, rng):
    """Founders taken from several saved populations, an equal share from each: total // len(paths) creatures drawn
    without replacement from each file (all of them if it holds fewer). The species of the files are kept apart:
    {profile: [(genome, size)]}. A duel of evolved populations starts this way, without the lottery of random
    founders going through the first bottleneck."""
    from evolution.continuous import load_population
    founders = {}
    share = total // len(paths)
    for path in paths:
        pool = [(name, f) for name, fs in load_population(path).items() for f in fs]
        for name, f in rng.sample(pool, min(share, len(pool))):
            founders.setdefault(name, []).append(f)
    return founders


def world_rng(seed, replica=0):
    """Chance of the world for a seed. Replica 0 is the plain seed (earlier runs); another replica replays the same
    founders (they are drawn with their own random.Random(seed)) with other chance."""
    return random.Random(seed if not replica else seed * 1000 + replica)


def paired_seeds(seeds, shift):
    """{seed: the seed `shift` places further in the list, cyclically}: who meets whom in a crossed duel."""
    return {s: seeds[(i + shift) % len(seeds)] for i, s in enumerate(seeds)}


def run_seed(seed, out_dir, overrides, ticks, profiles, population_file, replica=0, pair=None, photos=0,
             cycle=False):
    """One seed (run in its own process by main, to use every core). In population paths {seed} is the seed and
    {pair} its paired seed (crossed duels, default: the seed itself). photos > 0: the population is also saved every
    `photos` ticks (seed_<n>/population_<tick>.npz), to follow it over the run. cycle=True: several population
    files are not mixed, seed s starts from file (s - 1) mod n.
    With PREDATION, the predators of a starting population are left out: they arrive at PREDATOR_START (random, or
    drawn from PREDATOR_POPULATION)."""
    from evolution.continuous import ContinuousSimulation, save_population, load_population, predator_source
    cfg = build_settings(overrides, SEED=seed, ACTIVE_PROFILES=list(profiles))
    seed_dir = os.path.join(out_dir, f"seed_{seed}")
    files = [] if not population_file else [population_file] if isinstance(population_file, str) else population_file
    files = [p.format(seed=seed, pair=seed if pair is None else pair) for p in files]
    if cycle and files:
        files = [files[(seed - 1) % len(files)]]
    missing = [p for p in files if not os.path.exists(p)]
    if missing:   # Typically: that seed died out in the run the population comes from
        return f"graine {seed} : ignorée, population de départ absente ({os.path.relpath(missing[0], ROOT)})"
    if not population_file:
        founders = None
    elif len(files) == 1:   # One file: the whole population
        founders = load_population(files[0])
    else:                   # Several: an equal share of each
        founders = mixed_founders(files, cfg.INITIAL_POPULATION, random.Random(seed))
    if founders and cfg.PREDATION:
        founders = {name: fs for name, fs in founders.items() if name != cfg.PREDATOR_PROFILE}
    sim = ContinuousSimulation(world_rng(seed, replica), os.path.join(seed_dir, "timeline.csv"), founders=founders,
                              cfg=cfg)
    start = time.time()
    played = 0
    while played < ticks and not sim.extinct:
        step = min(ticks - played, photos - sim.world.tick % photos) if photos else ticks - played
        played += sim.run(step)
        if photos and not sim.extinct and sim.world.tick % photos == 0 and played < ticks:
            save_population(sim, os.path.join(seed_dir, f"population_{sim.world.tick}.npz"))
    if not sim.extinct:
        save_population(sim, os.path.join(seed_dir, "population_finale.npz"))
    end = f"EXTINCTION au tick {sim.world.tick}" if sim.extinct else f"population {len(sim.world.creatures)}"
    origin = "".join(f", {what} {os.path.relpath(p, ROOT)}" for what, p in
                     (("départ", files[0] if len(files) == 1 and cycle else ""),
                      ("prédateurs", predator_source(cfg) if cfg.PREDATION else "")) if p)
    return f"graine {seed} : {played} ticks en {time.time() - start:.0f} s, {end}{origin}"


def show_progress(out_dir, futures, every=2.0):
    """Wait for the seeds, with a progress bar: redrawn in place in a terminal, one line per 10 % otherwise (a log).
    The message of each seed is printed when it ends."""
    from concurrent.futures import FIRST_COMPLETED, wait
    from experiments.progress import bar, run_progress
    tty = sys.stdout.isatty()
    pending, last_step = set(futures), -1
    while pending:
        done, pending = wait(pending, timeout=every, return_when=FIRST_COMPLETED)
        for fut in done:
            print(("\r\033[K" if tty else "") + fut.result())
        fraction, finished, total, elapsed = run_progress(out_dir)
        if not pending:
            fraction, finished = 1.0, total
        line = bar(fraction, finished, total, elapsed)
        if tty:
            print("\r\033[K" + line, end="" if pending else "\n", flush=True)
        elif int(fraction * 10) > last_step:
            last_step = int(fraction * 10)
            print(line, flush=True)


def git_state():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,
                                         stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                             text=True, stderr=subprocess.DEVNULL).strip())
        return commit + ("-modifié" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="Nom court de l'expérience (dossier de résultats)")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--ticks", type=int, default=60000, help="Durée (arrêt avant en cas d'extinction)")
    parser.add_argument("--photos", type=int, default=0, metavar="TICKS",
                        help="Sauver aussi la population tous les TICKS ticks (population_<tick>.npz)")
    parser.add_argument("--profiles", nargs="+", default=None, help="Espèces fondatrices (défaut : ACTIVE_PROFILES)")
    parser.add_argument("--from-population", nargs="+", default=None,
                        help="Population sauvegardée de départ (.npz). {seed} est remplacé par le numéro de graine. "
                             "Plusieurs fichiers : INITIAL_POPULATION fondateurs, à parts égales de chacun (duel "
                             "de populations évoluées)")
    parser.add_argument("--cycle", action="store_true",
                        help="Plusieurs --from-population : la graine s part du fichier (s - 1) mod n seul, au lieu "
                             "d'une part égale de chacun")
    parser.add_argument("--replica", type=int, nargs="+", default=[0],
                        help="Autre hasard du monde, mêmes fondateurs (0 : la graine telle quelle). Plusieurs "
                             "valeurs : un run par valeur")
    parser.add_argument("--shift", type=int, nargs="+", default=[0],
                        help="{pair} dans --from-population : la graine placée SHIFT rangs plus loin dans --seeds. "
                             "Plusieurs valeurs : un run par valeur")
    parser.add_argument("--set", nargs="*", default=[], metavar="NOM=VALEUR",
                        help="Remplace une constante de config.py")
    parser.add_argument("--varie", nargs="*", default=[], metavar="NOM=V1,V2,...",
                        help="Un run par valeur de la constante (plusieurs --varie : toutes les combinaisons)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count(), help="Graines lancées en parallèle")
    parser.add_argument("--out-dir", default=None, help=argparse.SUPPRESS)   # Chosen by experiments.lot
    return parser


def parse_overrides(items):
    """--set NAME=VALUE items -> {NAME: value}."""
    overrides = {}
    for item in items:
        name, _, value = item.partition("=")
        overrides[name.strip().upper()] = parse_value(value)
    return overrides


def expand(args):
    """The runs of one command: [(name, argv)], one per combination of the --varie, --replica and --shift values.
    A single run keeps its name; otherwise each name gets the values that change (cout_0.015, rejeu_r1, croise_s2)."""
    import itertools
    dims = []   # One list per varied option: [(what goes in argv, label in the name)]
    for item in args.varie:
        name, _, values = item.partition("=")
        dims.append([(("--set", f"{name.strip().upper()}={v.strip()}"), v.strip()) for v in values.split(",")
                     if v.strip()])
    dims.append([(("--replica", str(r)), f"r{r}") for r in args.replica])
    dims.append([(("--shift", str(k)), f"s{k}") for k in args.shift])
    out = []
    for combo in itertools.product(*dims):
        name = "_".join([args.name, *(label for dim, (_, label) in zip(dims, combo) if len(dim) > 1)])
        chosen = [pair for pair, _ in combo]
        sets = [*args.set, *(value for option, value in chosen if option == "--set")]
        argv = ["--name", name, "--seeds", *map(str, args.seeds), "--ticks", str(args.ticks), "--jobs", str(args.jobs)]
        if args.photos:
            argv += ["--photos", str(args.photos)]
        for option, value in chosen:
            if option != "--set":
                argv += [option, value]
        if args.profiles:
            argv += ["--profiles", *args.profiles]
        if args.from_population:
            argv += ["--from-population", *args.from_population]
        if args.cycle:
            argv += ["--cycle"]
        if sets:
            argv += ["--set", *sets]
        build_settings(parse_overrides(sets))   # Typos stop here, before the first run
        out.append((name, argv))
    return out


def main(argv=None):
    args = build_parser().parse_args(argv)
    runs = expand(args)
    if len(runs) > 1:
        from experiments.lot import plan, run_lot
        return run_lot(plan([a for _, a in runs]), args.name)
    args.replica, args.shift = args.replica[0], args.shift[0]

    import config
    overrides = parse_overrides(args.set)
    cfg = build_settings(overrides)   # Here too: run.json records the real values, and typos stop here
    profiles = args.profiles or cfg.ACTIVE_PROFILES
    from brain.profiles import PROFILES
    unknown = [p for p in profiles if p not in PROFILES]
    if unknown:
        raise SystemExit(f"Profil inconnu : {', '.join(unknown)} (disponibles : {', '.join(PROFILES)})")

    out_dir = args.out_dir or os.path.join(RESULTS, time.strftime("%Y%m%d_%H%M%S") + "_" + args.name)
    os.makedirs(out_dir)
    meta = {"name": args.name, "ticks": args.ticks, "from_population": args.from_population,
            "command": " ".join(sys.argv), "git": git_state(), "seeds": args.seeds, "profiles": list(profiles),
            "overrides": overrides, "replica": args.replica, "shift": args.shift, "photos": args.photos,
            "cycle": args.cycle,
            "config": {n: getattr(cfg, n) for n in [*cfg.__dict__, *config.DERIVED] if n.isupper() and n != "SAVE_DIR"
                       and isinstance(getattr(cfg, n), (int, float, str, bool, list, tuple))}}
    with open(os.path.join(out_dir, "run.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"{args.name} : {len(args.seeds)} graines × {args.ticks} ticks, profils {', '.join(profiles)} "
          f"→ {os.path.relpath(out_dir, ROOT)}")

    pairs = paired_seeds(args.seeds, args.shift)
    from core.kernels import worker_init   # One numba thread per worker when they fill the cores
    with ProcessPoolExecutor(max_workers=max(1, args.jobs), initializer=worker_init,
                             initargs=(args.jobs,)) as pool:
        futures = [pool.submit(run_seed, s, out_dir, overrides, args.ticks, profiles, args.from_population,
                               args.replica, pairs[s], args.photos, args.cycle) for s in args.seeds]
        show_progress(out_dir, futures)

    from experiments.summary import summarize_timeline, print_timeline_table, print_species_table
    summarize_timeline(out_dir)
    print_timeline_table([out_dir])
    print_species_table([out_dir])


if __name__ == "__main__":
    sys.exit(main())

"""Common garden («jardin commun»): the same genomes placed in different conditions, without births.

If a trait (here the speed) changes with the condition while the genomes are the same, it is a reaction of the
behaviour to the surroundings (plasticity), not a genetic change. Classic test in biology.

    python -m experiments.jardin experiments/results/<run>/seed_1/population_finale.npz --densities 30 280 --seeds 1 2 3
    python -m experiments.jardin aleatoire --densities 30 280          (random genomes, reference)

For each population, density and seed: N creatures drawn from the population (with replacement if N is larger),
births off, no old age, TICKS ticks; mean speed and meals per 1000 ticks of life measured after a WARMUP.
"""
import argparse
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def garden(source, density, seed, ticks, warmup, profile):
    import config
    from brain.profiles import new_brain
    from evolution.continuous import ContinuousSimulation, load_population
    config.REPRO_THRESHOLD = float("inf")   # No births: the density stays what we set
    config.AGE_MAX = 0
    rng = random.Random(seed)
    if source == "aleatoire":
        founders = None
        config.ACTIVE_PROFILES = [profile]
        config.INITIAL_POPULATION = density
    else:
        pool = [g for gs in load_population(source).values() for g in gs]
        name = next(iter(load_population(source)))
        founders = {name: [pool[rng.randrange(len(pool))] for _ in range(density)]}
    sim = ContinuousSimulation(rng, founders=founders)
    speed, alive_ticks, meals0 = 0.0, 0, None
    for t in range(ticks):
        if not sim.step():
            break
        if t == warmup:
            meals0 = sim.world.eaten
        if t >= warmup:
            cs = sim.world.creatures
            speed += sum(c.speed for c in cs)
            alive_ticks += len(cs)
    if not alive_ticks:
        return None
    return {"speed": speed / alive_ticks, "food_rate": (sim.world.eaten - meals0) * 1000 / alive_ticks,
            "alive_end": len(sim.world.creatures)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+", help="Fichiers .npz de population, ou «aleatoire»")
    parser.add_argument("--densities", type=int, nargs="+", default=[30, 280])
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--ticks", type=int, default=3000)
    parser.add_argument("--warmup", type=int, default=600, help="Ticks ignorés au début (accélération, placement)")
    parser.add_argument("--profile", default="complet", help="Espèce des génomes aléatoires")
    parser.add_argument("--jobs", type=int, default=os.cpu_count())
    args = parser.parse_args(argv)

    jobs = [(src, d, s) for src in args.sources for d in args.densities for s in args.seeds]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(garden, *zip(*jobs), *[[v] * len(jobs) for v in (args.ticks, args.warmup, args.profile)]))
    table = {}
    for (src, d, _), r in zip(jobs, results):
        if r is not None:
            table.setdefault((src, d), []).append(r)
    print(f"\n{'population':<60} {'densité':>8} {'vitesse':>16} {'repas/1000t':>16}")
    for (src, d), rs in table.items():
        label = src if src == "aleatoire" else os.path.relpath(src, ROOT)
        cells = ""
        for k in ("speed", "food_rate"):
            vals = [r[k] for r in rs]
            cells += f"{statistics.mean(vals):>9.2f} ±{statistics.stdev(vals) if len(vals) > 1 else 0:>5.2f}"
        print(f"{label[-60:]:<60} {d:>8} {cells}")


if __name__ == "__main__":
    main()

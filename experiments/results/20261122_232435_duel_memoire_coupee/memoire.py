"""Is the memory of complet_memoire used, and does it cost? (1) probe of the 16 populations evolved alone: memory
values, effect of the actual memory on the outputs, knockout (memory inputs always 0) on the population;
(2) the 15 original duels against complet replayed with the memory of complet_memoire cut."""
import json, os, random, shutil, statistics as st, sys, time
from concurrent.futures import ProcessPoolExecutor
ROOT = "/Users/jul/Documents/Dev/EvolutionGame"
sys.path.insert(0, ROOT)
import numpy as np
R = f"{ROOT}/experiments/results"
ALONE = f"{R}/20261122_151957_seul_complet_memoire/seed_{{seed}}/population_finale.npz"
COMPLET = f"{R}/20261122_150050_seul_complet/seed_{{seed}}/population_finale.npz"


def cut_memory():
    """From now on, in this process, complet_memoire creatures never remember anything (inputs 0)."""
    from evolution.continuous import ContinuousSimulation
    plain = ContinuousSimulation.step
    def step(self):
        alive = plain(self)
        for c in self.world.creatures:
            if c.profile == "complet_memoire":
                c.memory = [0.0] * len(c.memory)
        return alive
    ContinuousSimulation.step = step


def _sim(path, seed):
    from evolution.continuous import ContinuousSimulation, load_population
    from experiments.run import population_settings
    return ContinuousSimulation(random.Random(seed), founders=load_population(path), cfg=population_settings(path)[0])


def probe(seed):
    path = ALONE.format(seed=seed)
    sim = _sim(path, 1)
    mem, d_mem, d_energy = [], [], []
    from brain.profiles import input_labels
    labels = input_labels("complet_memoire")
    ie, im = labels.index("Énergie"), [i for i, l in enumerate(labels) if l.startswith("Mémoire")]
    for t in range(3000):
        sim.step()
        if t >= 600 and t % 20 == 0:
            w = sim.world
            for c in [c for c in w.creatures if c.alive][::4]:
                x = np.array(w.sense(c), dtype=float)
                mem.append(x[im])
                zero = x.copy(); zero[im] = 0.0
                d_mem.append(np.abs(c.brain.forward(x)[:2] - c.brain.forward(zero)[:2]))
                lo, hi = x.copy(), x.copy(); lo[ie], hi[ie] = 0.0, 1.0
                d_energy.append(np.abs(c.brain.forward(hi)[:2] - c.brain.forward(lo)[:2]))
    m = np.array(mem)
    return seed, float(np.abs(m).mean()), float(m.std(axis=0).mean()), np.mean(d_mem, axis=0).tolist(), \
        np.mean(d_energy, axis=0).tolist()


def knockout(args):
    seed, world, cut = args
    if cut:
        cut_memory()
    sim = _sim(ALONE.format(seed=seed), world)
    pops = []
    for t in range(20000):
        if not sim.step():
            break
        if t >= 5000 and t % 100 == 0:
            pops.append(sum(c.alive for c in sim.world.creatures))
    return seed, world, cut, st.mean(pops) if pops else 0.0


def duel(args):
    seed, out_dir = args
    cut_memory()
    from experiments.run import run_seed
    return run_seed(seed, out_dir, {}, 120000, ["complet", "complet_memoire"], [COMPLET, ALONE])


if __name__ == "__main__":
    part = sys.argv[1]
    if part == "knockout":
        with ProcessPoolExecutor(8, max_tasks_per_child=1) as pool:
            res = list(pool.map(knockout, [(s, w, c) for s in range(1, 17) for w in (7, 8) for c in (False, True)]))
        print("graine  population normale / mémoire coupée (moyenne de 2 mondes, ticks 5 000 à 20 000)")
        diffs = []
        for s in range(1, 17):
            n = st.mean(p for ss, w, c, p in res if ss == s and not c)
            k = st.mean(p for ss, w, c, p in res if ss == s and c)
            diffs.append((k - n) / n)
            print(f"  {s:2d}   {n:5.0f} / {k:5.0f}   {100 * (k - n) / n:+5.1f} %")
        print(f"moyenne {100 * st.mean(diffs):+.1f} %, coupée plus basse dans {sum(d < 0 for d in diffs)}/16")
    elif part == "probe":
        with ProcessPoolExecutor(8) as pool:
            print("graine  |mémoire| moy  écart-type  |Δsortie| mémoire réelle→0 (virage, vitesse)  |Δsortie| énergie 0→1")
            for s, a, sd, dm, de in pool.map(probe, range(1, 17)):
                print(f"  {s:2d}      {a:.2f}        {sd:.2f}        {dm[0]:.3f} {dm[1]:.3f}                         {de[0]:.3f} {de[1]:.3f}")
        with ProcessPoolExecutor(8, max_tasks_per_child=1) as pool:   # A cut must not leak into the next task
            res = list(pool.map(knockout, [(s, w, c) for s in range(1, 17) for w in (7, 8) for c in (False, True)]))
        print("\ngraine  population normale / mémoire coupée (moyenne de 2 mondes, ticks 5 000 à 20 000)")
        diffs = []
        for s in range(1, 17):
            n = st.mean(p for ss, w, c, p in res if ss == s and not c)
            k = st.mean(p for ss, w, c, p in res if ss == s and c)
            diffs.append((k - n) / n)
            print(f"  {s:2d}   {n:5.0f} / {k:5.0f}   {100 * (k - n) / n:+5.1f} %")
        print(f"moyenne {100 * st.mean(diffs):+.1f} %, coupée plus basse dans {sum(d < 0 for d in diffs)}/16")
    else:
        src = f"{R}/20261122_154315_duel_evolues_complet_memoire"
        out_dir = f"{R}/{time.strftime('%Y%m%d_%H%M%S')}_duel_memoire_coupee"
        os.makedirs(out_dir)
        meta = json.load(open(f"{src}/run.json"))
        meta.update(name="duel_memoire_coupee", command="scratchpad memoire.py duel (memory of complet_memoire "
                    "cut: its memory inputs forced to 0 after every tick); otherwise " + meta["command"])
        json.dump(meta, open(f"{out_dir}/run.json", "w"), indent=2, ensure_ascii=False)
        with ProcessPoolExecutor(8, max_tasks_per_child=1) as pool:
            for line in pool.map(duel, [(s, out_dir) for s in range(1, 17)]):
                print(line)
        shutil.copy(__file__, f"{out_dir}/memoire.py")
        print(out_dir)

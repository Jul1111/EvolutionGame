"""How the networks react to what they see of the other kind (23/11): flight of the prey, pursuit of the predators.

    python experiments/results/predateurs/capteurs.py <run with predators> [<control run without predators>]

Each final population is played 1 500 ticks in the world of its run (as experiments/carte.py does). For 30 creatures
of each kind, every 10 ticks, the inputs of their network are kept when the target is in view (prey: a predator;
predators: a prey). The response is the output with these inputs minus the output of the same network with the
target inputs set to «nothing in view» (distance 1, angle 0):
- speed: change of the speed asked (in speed units, maximum 4);
- turn: change of the turn × side of the target (> 0: turns toward it, < 0: turns away).
Control: the prey of a world without predators never saw one (the input stayed at 1, 0: its weights drifted
freely). They are shown the predator positions met by the prey of the run with predators (same seed), drawn at
random: what a network that never needed the input does with it.
"""
import glob
import os
import random
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from brain.profiles import PROFILES, input_labels  # noqa: E402

SPEED = 4.0


def target_columns(profile):
    """Index of the [distance, angle] inputs of the other kind in this profile's input vector."""
    labels = input_labels(profile)
    name = "Dist. proie" if PROFILES[profile].get("predator") else "Dist. prédateur"
    k = labels.index(name)
    return k, k + 1


def replay(path, creatures=30, ticks=1500, every=10):
    """{profile: [(brain, inputs array)]} of a saved population played in the world of its run."""
    from evolution.continuous import ContinuousSimulation, load_population
    from experiments.run import population_settings
    sim = ContinuousSimulation(random.Random(1), founders=load_population(path), cfg=population_settings(path)[0])
    rng = random.Random(2)
    watched = {}
    for p in ("proie", "predateur"):
        pool = [c for c in sim.world.creatures if c.profile == p]
        watched[p] = rng.sample(pool, min(creatures, len(pool)))
    states = {id(c): [] for cs in watched.values() for c in cs}
    for t in range(ticks):
        if not sim.step():
            break
        if t % every == 0:
            for cs in watched.values():
                for c in cs:
                    if c.alive:
                        states[id(c)].append(np.array(sim.world.sense(c), dtype=float))
    return {p: [(c.brain, np.array(states[id(c)])) for c in cs if states[id(c)]] for p, cs in watched.items()}


def response(brain, x, cols):
    """(speed change, turn toward) averaged over the rows of x (target in view), and the number of rows."""
    d, a = cols
    off = x.copy()
    off[:, d], off[:, a] = 1.0, 0.0
    out = np.array([brain.forward(v)[:2] for v in x])
    out_off = np.array([brain.forward(v)[:2] for v in off])
    speed = (out[:, 1] - out_off[:, 1]) / 2 * SPEED
    toward = (out[:, 0] - out_off[:, 0]) * np.sign(x[:, a])
    return float(speed.mean()), float(toward.mean())


def kind_stats(members, profile, inject=None, rng=None):
    """Mean response of the creatures of a kind (only rows with the target in view), or of control prey shown the
    target positions `inject` ((n, 2) array of distance, angle)."""
    cols = target_columns(profile)
    speeds, turns = [], []
    for brain, x in members:
        if inject is not None:
            if not len(inject):
                continue
            x = x.copy()
            pick = inject[rng.integers(len(inject), size=len(x))]
            x[:, cols[0]], x[:, cols[1]] = pick[:, 0], pick[:, 1]
        else:
            x = x[x[:, cols[0]] < 1.0]
        if len(x) < 5:
            continue
        s, t = response(brain, x, cols)
        speeds.append(s)
        turns.append(t)
    return (float(np.mean(speeds)) if speeds else float("nan"), float(np.mean(turns)) if turns else float("nan"),
            len(speeds))


def main(argv):
    run, control = argv[0], (argv[1] if len(argv) > 1 else None)
    rows = []
    for path in sorted(glob.glob(os.path.join(run, "seed_*", "population_finale.npz")),
                       key=lambda p: int(p.split("seed_")[1].split(os.sep)[0])):
        seed = int(path.split("seed_")[1].split(os.sep)[0])
        data = replay(path)
        prey = kind_stats(data.get("proie", []), "proie")
        pred = kind_stats(data.get("predateur", []), "predateur")
        seen = np.concatenate([x[x[:, -2] < 1.0][:, -2:] for _, x in data.get("proie", []) if len(x)] or
                              [np.zeros((0, 2))])
        ctrl = (float("nan"), float("nan"), 0)
        cpath = os.path.join(control, f"seed_{seed}", "population_finale.npz") if control else None
        if cpath and os.path.exists(cpath) and len(seen):
            cdata = replay(cpath)
            ctrl = kind_stats(cdata.get("proie", []), "proie", inject=seen, rng=np.random.default_rng(seed))
        rows.append((seed, prey, pred, ctrl))
        print(f"graine {seed:2d} : proies ({prey[2]:2d}) vitesse {prey[0]:+.2f} virage vers {prey[1]:+.3f} | "
              f"prédateurs ({pred[2]:2d}) vitesse {pred[0]:+.2f} virage vers {pred[1]:+.3f} | "
              f"témoin ({ctrl[2]:2d}) vitesse {ctrl[0]:+.2f} virage vers {ctrl[1]:+.3f}", flush=True)

    def summary(label, values):
        v = np.array([x for x in values if x == x])
        if not len(v):
            return f"{label} n/a"
        return f"{label} {v.mean():+.3f} (médiane {np.median(v):+.3f}, > 0 dans {int((v > 0).sum())}/{len(v)})"
    print()
    print("Proies    :", summary("vitesse", [r[1][0] for r in rows]), "|", summary("virage", [r[1][1] for r in rows]))
    print("Prédateurs:", summary("vitesse", [r[2][0] for r in rows]), "|", summary("virage", [r[2][1] for r in rows]))
    if control:
        print("Témoin    :", summary("vitesse", [r[3][0] for r in rows]), "|",
              summary("virage", [r[3][1] for r in rows]))


if __name__ == "__main__":
    main(sys.argv[1:])

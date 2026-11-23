"""Headless experiments (experiments/): each run has its own settings and leaves the config module alone."""
import csv
import os

import pytest

import config
from experiments import run as run_module
from experiments.jardin import garden


def test_build_settings_applies_overrides_without_touching_the_module():
    cfg = run_module.build_settings({"FOOD_COUNT": 7, "REPRO_THRESHOLD": 90}, SEED=5)
    assert cfg.FOOD_COUNT == 7 and cfg.SEED == 5
    assert isinstance(cfg.REPRO_THRESHOLD, float) and cfg.REPRO_THRESHOLD == 90.0   # An int for a float setting
    assert config.FOOD_COUNT != 7 and config.SEED != 5
    assert cfg.WORLD_WIDTH == config.WORLD_WIDTH                                       # Derived values follow


def test_build_settings_rejects_unknown_and_derived_names():
    with pytest.raises(SystemExit):
        run_module.build_settings({"NOT_A_SETTING": 1})
    with pytest.raises(SystemExit):
        run_module.build_settings({"WORLD_WIDTH": 100})   # Derived from WORLD_SCALE: not a setting


def test_run_seed_writes_its_timeline_with_its_own_settings(tmp_path):
    out = str(tmp_path)
    message = run_module.run_seed(3, out, {"INITIAL_POPULATION": 20, "SAMPLE_TICKS": 20, "WORLD_SCALE": 1},
                                  200, ["complet"], None)
    assert "graine 3" in message
    with open(os.path.join(out, "seed_3", "timeline.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and float(rows[0]["population"]) > 0 and "pop__complet" in rows[0]
    assert config.INITIAL_POPULATION != 20 and config.SAMPLE_TICKS != 20   # The module was not changed


def test_two_seeds_in_one_process_do_not_share_settings(tmp_path):
    run_module.run_seed(1, str(tmp_path), {"INITIAL_POPULATION": 10, "SAMPLE_TICKS": 10}, 20, ["complet"], None)
    run_module.run_seed(2, str(tmp_path), {"INITIAL_POPULATION": 40, "SAMPLE_TICKS": 10}, 20, ["complet"], None)
    pops = []
    for seed in (1, 2):
        with open(os.path.join(tmp_path, f"seed_{seed}", "timeline.csv"), newline="", encoding="utf-8") as f:
            pops.append(float(next(csv.DictReader(f))["population"]))
    assert pops[0] < pops[1]


def test_garden_keeps_density_without_births_or_deaths_of_old_age():
    result = garden("aleatoire", 30, 1, 60, 10, "complet")
    assert result is not None
    assert config.AGE_MAX != 0 and config.REPRO_THRESHOLD != float("inf")   # Settings of the garden stayed in it


def test_a_population_is_continued_in_the_world_of_its_run(tmp_path):
    """jardin and gradient read the run.json next to a population: every recorded value, not config.py."""
    import json
    run = tmp_path / "run"
    (run / "seed_1").mkdir(parents=True)
    recorded = {"FOOD_COUNT": 7, "WORLD_SCALE": 2, "ACTIVE_PROFILES": ["complet_faim"],
                "WORLD_WIDTH": 1, "NO_LONGER_A_SETTING": 3, "SAVE_DIR": "/elsewhere"}
    (run / "run.json").write_text(json.dumps({"config": recorded}), encoding="utf-8")
    cfg, source = run_module.population_settings(str(run / "seed_1" / "population_finale.npz"), AGE_MAX=0)
    assert cfg.FOOD_COUNT == 7 and cfg.WORLD_SCALE == 2 and cfg.ACTIVE_PROFILES == ["complet_faim"]
    assert cfg.WORLD_WIDTH == 2 * config.SCREEN_WIDTH            # Derived again from the recorded WORLD_SCALE
    assert cfg.AGE_MAX == 0 and cfg.SAVE_DIR == config.SAVE_DIR  # `extra` on top; SAVE_DIR never taken
    assert not hasattr(cfg, "NO_LONGER_A_SETTING") and source.endswith("run.json")
    # Without run.json (a population saved from the game): config.py
    cfg, source = run_module.population_settings(str(tmp_path / "saves" / "x.npz"))
    assert cfg.FOOD_COUNT == config.FOOD_COUNT and source == "config.py"


def test_garden_takes_its_own_settings():
    plain = garden("aleatoire", 20, 1, 30, 5, "complet")
    scarce = garden("aleatoire", 20, 1, 30, 5, "complet", {"FOOD_COUNT": 5})
    assert scarce["foods"] == 5 and plain["foods"] == config.FOOD_COUNT
    assert config.FOOD_COUNT != 5   # The module is left alone


def test_mixed_founders_take_an_equal_share_of_each_population(tmp_path):
    import random
    from evolution.continuous import ContinuousSimulation, save_population
    paths = []
    for profile, n in (("complet", 30), ("complet_faim", 8)):
        sim = ContinuousSimulation(random.Random(1), cfg=config.Settings(ACTIVE_PROFILES=[profile],
                                                                          INITIAL_POPULATION=n))
        paths.append(str(tmp_path / f"{profile}.npz"))
        save_population(sim, paths[-1])
    founders = run_module.mixed_founders(paths, 20, random.Random(3))
    assert len(founders["complet"]) == 10        # Half of 20, drawn from the 30
    assert len(founders["complet_faim"]) == 8    # Only 8 in that file: all of them
    again = run_module.mixed_founders(paths, 20, random.Random(3))
    assert all((a[0] == b[0]).all() for a, b in zip(founders["complet"], again["complet"]))   # Same seed, same draw


def test_run_seed_starts_a_duel_from_two_populations(tmp_path):
    import random
    from evolution.continuous import ContinuousSimulation, save_population
    paths = []
    for profile in ("complet", "complet_faim"):
        sim = ContinuousSimulation(random.Random(1), cfg=config.Settings(ACTIVE_PROFILES=[profile],
                                                                          INITIAL_POPULATION=20))
        paths.append(str(tmp_path / f"{profile}_{{seed}}.npz"))
        save_population(sim, paths[-1].format(seed=4))
    run_module.run_seed(4, str(tmp_path / "out"), {"INITIAL_POPULATION": 20, "SAMPLE_TICKS": 10}, 20,
                        ["complet", "complet_faim"], paths)
    with open(os.path.join(tmp_path, "out", "seed_4", "timeline.csv"), newline="", encoding="utf-8") as f:
        first = next(csv.DictReader(f))
    assert float(first["pop__complet"]) > 0 and float(first["pop__complet_faim"]) > 0


def test_a_seed_without_its_starting_population_is_skipped(tmp_path):
    message = run_module.run_seed(5, str(tmp_path), {"SAMPLE_TICKS": 10}, 20, ["complet"],
                                  [str(tmp_path / "a_{seed}.npz"), str(tmp_path / "b_{seed}.npz")])
    assert "ignorée" in message and not (tmp_path / "seed_5").exists()


def test_replica_and_pairs():
    """A replica replays the same founders with other chance; a shift pairs each seed with another one."""
    assert run_module.world_rng(4).random() == __import__("random").Random(4).random()   # Replica 0: as before
    assert run_module.world_rng(4, 1).random() != run_module.world_rng(4).random()
    assert run_module.paired_seeds([1, 2, 5], 1) == {1: 2, 2: 5, 5: 1}
    assert run_module.paired_seeds([1, 2, 5], 0) == {1: 1, 2: 2, 5: 5}


def test_a_crossed_duel_reads_the_paired_seed(tmp_path):
    message = run_module.run_seed(5, str(tmp_path), {"SAMPLE_TICKS": 10}, 20, ["complet"],
                                  [str(tmp_path / "a_{seed}.npz"), str(tmp_path / "b_{pair}.npz")], pair=8)
    assert "a_5.npz" in message   # {seed} for the first file...
    (tmp_path / "a_5.npz").touch()
    message = run_module.run_seed(5, str(tmp_path), {"SAMPLE_TICKS": 10}, 20, ["complet"],
                                  [str(tmp_path / "a_{seed}.npz"), str(tmp_path / "b_{pair}.npz")], pair=8)
    assert "b_8.npz" in message   # ...{pair} for the second


def test_pause_finds_the_experiments_and_their_workers():
    from experiments.pause import experiments
    table = {10: (1, "S", "python -m experiments.run --name x"), 11: (10, "R", "python -c spawn_main"),
             12: (11, "R", "python -c helper"), 20: (1, "S", "python -m pytest"), 21: (20, "R", "python worker")}
    assert experiments(table) == [10, 11, 12]


def test_progress_reads_what_the_seeds_wrote(tmp_path):
    import json
    from experiments.progress import bar, run_progress
    (tmp_path / "run.json").write_text(json.dumps({"ticks": 1000, "seeds": [1, 2, 3, 4]}), encoding="utf-8")
    header = "tick,population\n"
    for seed, text in ((1, header + "500,30\n"), (2, header + "300,0\n")):   # Half way; died out
        (tmp_path / f"seed_{seed}").mkdir()
        (tmp_path / f"seed_{seed}" / "timeline.csv").write_text(text, encoding="utf-8")
    (tmp_path / "seed_3").mkdir()
    (tmp_path / "seed_3" / "population_finale.npz").touch()                    # Finished; seed 4 not started
    fraction, done, total, _ = run_progress(str(tmp_path))
    assert (fraction, done, total) == (0.625, 2, 4)
    assert "62 %" in bar(fraction, done, total, 60) and "reste" in bar(fraction, done, total, 60)
    (tmp_path / "summary.csv").touch()
    assert run_progress(str(tmp_path))[0] == 1.0


def test_a_lot_is_planned_before_it_runs(tmp_path):
    from experiments import lot
    from experiments.progress import render
    path = tmp_path / "lot.txt"
    path.write_text("# comment\n--name a --seeds 1 2 --ticks 100 --set WORLD_SCALE=2\n"
                    "--name b --seeds 1 --ticks 100 \\\n  --from-population {run:a}/seed_{seed}/x.npz\n",
                    encoding="utf-8")
    runs = lot.plan(lot.read_lot(str(path)))
    assert [r["name"] for r in runs] == ["a", "b"]
    assert runs[0]["weight"] == 2 * 100 * 4 and runs[1]["weight"] == 100 * config.WORLD_SCALE ** 2
    assert lot.resolve(runs[1]["args"], {"a": os.path.join(lot.ROOT, "r", "a")})[-1] == "r/a/seed_{seed}/x.npz"
    with pytest.raises(SystemExit):
        lot.resolve(runs[1]["args"], {})                  # {run:a} before a is done
    path.write_text("--name a\n--name a\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        lot.plan(lot.read_lot(str(path)))                 # Two runs with the same name
    text, fraction = render({"label": "lot", "started": 0, "finished": None, "runs": runs})
    assert fraction == 0 and text.splitlines()[1].startswith("  a ") and "en attente" in text


def test_one_command_with_several_values_gives_several_runs():
    from experiments.lot import plan
    parser = run_module.build_parser()
    runs = run_module.expand(parser.parse_args(
        ["--name", "c", "--seeds", "1", "--varie", "FOOD_COUNT=30,60", "--replica", "1", "2", "--set", "AGE_MAX=9"]))
    assert [n for n, _ in runs] == ["c_30_r1", "c_30_r2", "c_60_r1", "c_60_r2"]
    last = parser.parse_args(runs[-1][1])
    assert last.set == ["AGE_MAX=9", "FOOD_COUNT=60"] and last.replica == [2] and last.shift == [0]
    assert [n for n, _ in run_module.expand(parser.parse_args(["--name", "c"]))] == ["c"]   # One run: same name
    with pytest.raises(SystemExit):
        run_module.expand(parser.parse_args(["--name", "c", "--varie", "NOT_A_SETTING=1,2"]))
    assert len(plan([["--name", "l", "--shift", "0", "1", "2"]])) == 3   # A lot line expands the same way


def test_settings_map_scores_a_run(tmp_path):
    from experiments.carte import complexity, timeline_scores
    out = str(tmp_path)
    for seed in (1, 2):
        run_module.run_seed(seed, out, {"INITIAL_POPULATION": 30, "SAMPLE_TICKS": 50}, 400,
                            ["complet", "complet_faim"], None)
    s = timeline_scores(out)
    assert s["seeds"] == 2 and s["population"] > 0 and 0 <= s["minority_share"] <= 0.5
    used, nonlin = complexity(os.path.join(out, "seed_1", "population_finale.npz"), creatures=5, ticks=300)
    assert 0 <= used <= 10 and nonlin == nonlin   # Not NaN
    assert complexity(os.path.join(out, "seed_9", "population_finale.npz")) is None

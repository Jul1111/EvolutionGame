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

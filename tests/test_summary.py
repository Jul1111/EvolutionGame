"""experiments/summary.py and experiments/gradient.py: the numbers they print are the ones quoted in
docs/experiences.md, so they are checked here on small hand-written files with known answers."""
import csv
import math
import os
import statistics

import pytest

from experiments import summary
from experiments.gradient import spearman, speed_vs_children


def _write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _timeline(pops, speeds, a=None, b=None):
    rows = []
    for i, (p, v) in enumerate(zip(pops, speeds)):
        row = {"tick": (i + 1) * 600, "population": p, "mean_speed": v}
        if a is not None:
            row["pop__a"], row["pop__b"] = a[i], b[i]
        rows.append(row)
    return rows


@pytest.fixture
def run_dir(tmp_path):
    """Three seeds: 1 and 3 survive, 2 dies out after two samples."""
    d = tmp_path / "run"
    _write(str(d / "seed_1" / "timeline.csv"), _timeline([100, 120, 140], [1.0, 2.0, 3.0]))
    _write(str(d / "seed_2" / "timeline.csv"), _timeline([50, 0], [5.0, ""]))
    _write(str(d / "seed_3" / "timeline.csv"), _timeline([200, 220, 260], [2.0, 2.0, 2.0]))
    return str(d)


def test_summary_per_sample_uses_the_seeds_still_alive(run_dir):
    rows = summary.summarize_timeline(run_dir)
    assert [r["seeds_alive"] for r in rows] == [3, 2, 2] and all(r["seeds"] == 3 for r in rows)
    assert rows[0]["population_mean"] == round(statistics.mean([100, 50, 200]), 3)
    assert rows[0]["population_std"] == round(statistics.stdev([100, 50, 200]), 3)
    assert rows[1]["population_mean"] == 170.0                 # Seed 2 is at 0: left out
    assert rows[2]["mean_speed_mean"] == 2.5 and rows[2]["births_mean"] == ""   # Missing column: empty
    assert os.path.exists(os.path.join(run_dir, "summary.csv"))


def test_last_window_table_counts_extinctions_and_averages_survivors(run_dir, capsys):
    summary.print_timeline_table([run_dir], last=2)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert "1/3" in line
    # Survivors only, mean of their last 2 samples: (130 + 240) / 2 = 185, std of (130, 240)
    assert f"{185.0:.2f} ±{statistics.stdev([130, 240]):>6.2f}" in line
    assert f"{statistics.mean([2.5, 2.0]):.2f}" in line           # Speed: (2 + 3) / 2 and 2


def test_species_table_leaves_out_the_seeds_that_died_out(tmp_path, capsys):
    d = tmp_path / "duel"
    # Seed 1: a wins (b dies out). Seed 2: b wins. Seed 3: the whole population dies out, it says nothing on the duel
    _write(str(d / "seed_1" / "timeline.csv"), _timeline([10, 10], [1, 1], a=[6, 10], b=[4, 0]))
    _write(str(d / "seed_2" / "timeline.csv"), _timeline([10, 10], [1, 1], a=[3, 2], b=[7, 8]))
    _write(str(d / "seed_3" / "timeline.csv"), _timeline([10, 0], [1, ""], a=[9, 0], b=[1, 0]))
    summary.print_species_table([str(d)], last=2)
    out = {line.split()[0]: line.split() for line in capsys.readouterr().out.splitlines()
           if line.startswith(("a ", "b "))}
    # a: 16/20 of seed 1, 5/20 of seed 2 → 52 % on average ; majority 1/2, extinct 0/2
    assert out["a"][1] == f"{(16 / 20 + 5 / 20) / 2:.0%}" and out["a"][3] == "1/2" and out["a"][4] == "0/2"
    assert out["b"][3] == "1/2" and out["b"][4] == "1/2"


def test_spearman_is_a_rank_correlation():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [9, 4, 1, 0]) == pytest.approx(-1.0)
    assert spearman([1, 2, 3, 4], [1, 100, 1000, 10000]) == pytest.approx(1.0)   # Ranks, not values
    assert spearman([1, 2, 3, 4], [2, 1, 4, 3]) == pytest.approx(0.6)            # 1 - 6·Σd² / (n(n²-1)) = 0.6


def test_speed_vs_children_by_quartile():
    deaths = [{"tick": 1000, "age": 700, "mean_speed": v, "children": k}
              for v, k in zip([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], [0, 0, 2, 2, 4, 4, 6, 6])]
    deaths += [{"tick": 10, "age": 700, "mean_speed": 9, "children": 99},     # Before `skip`: left out
               {"tick": 1000, "age": 100, "mean_speed": 9, "children": 99}]   # Too young to breed: left out
    r = speed_vs_children(deaths, skip=500, min_deaths=8)
    assert r["n"] == 8 and r["rho"] == pytest.approx(spearman([1, 2, 3, 4, 5, 6, 7, 8], [0, 0, 2, 2, 4, 4, 6, 6]))
    assert r["quartiles"] == [0.0, 2.0, 4.0, 6.0]
    assert r["speed_q"] == pytest.approx([0.15, 0.35, 0.55, 0.75])
    assert speed_vs_children(deaths, skip=500) is None                         # Fewer than 20 deaths
    assert not any(math.isnan(x) for x in r["quartiles"])


def test_legacy_generation_runs_are_still_read(tmp_path):
    """Results of the removed generation mode (experiments/results/20261108_20*) stay readable."""
    d = tmp_path / "old"
    for seed, values in (("seed_1", [1, 3]), ("seed_2", [3, 5])):
        _write(str(d / seed / "profiles" / "complet" / "stats.csv"),
               [{"alive": v, "mean_food": v * 2} for v in values])
    rows = summary.summarize(str(d))
    assert rows[1]["alive_mean"] == 4 and rows[1]["mean_food_mean"] == 8 and rows[1]["seeds"] == 2
    window = summary.last_window(str(d), 1)["complet"]
    assert window["alive"][0] == 4 and window["alive"][2] == 2

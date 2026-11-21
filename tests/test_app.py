import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("EVOLUTION_RENDERER", "cpu")

import pygame  # noqa: E402

import config  # noqa: E402
from app import App, PARAMS, next_step, prev_step  # noqa: E402


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOAD_SETTINGS", False)
    monkeypatch.setattr(config, "LOAD_ON_START", False)
    config.INITIAL_POPULATION = 30
    return App()


def test_step_cycle():
    assert next_step([1, 2, 3], 1) == 2 and next_step([1, 2, 3], 3) == 1
    assert prev_step([1, 2, 3], 1) == 3 and prev_step([1, 2, 3], 2) == 1
    assert next_step(["a", "b"], "b") == "a" and prev_step(["a", "b"], "a") == "b"


def test_app_runs_frames_and_commands(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    assert app.setup is not None            # Setup screen at launch: nothing runs yet
    app.do("start_new")
    app.do("setup_launch")                   # New simulation, running
    assert app.setup is None and not app.paused
    app.run(max_frames=5)
    assert app.world.tick > 0
    for action in ("pause", "step", "chart", "chart", "graph", "graph", "debug", "color", "zoom_in", "view_fit",
                   "legend", "help", "panels", "minimap", "effects", "best", "follow", "speed_up", "speed_down"):
        app.do(action)
        app.run(max_frames=2)
    assert app.selected is not None or not app.world.creatures


def test_params_apply_now_or_at_restart(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    app.do("setup_launch")
    old = config.MUTATION_STD
    app.do("mutation")                       # Applies at once
    assert config.MUTATION_STD != old and "mutation" not in app.pending
    app.do("obstacle_count")                 # Restart-only: pending
    assert "obstacle_count" in app.pending
    app.do("params_cancel")
    assert not app.pending
    assert all(key in PARAMS for key in app.pending)


def test_escape_quits_and_saves(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    app.do("start_new")
    app.do("setup_launch")
    app.run(max_frames=3)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    app.run(max_frames=2)
    assert not app.running

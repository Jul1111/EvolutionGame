import pygame

import config
from app import KEYS, PARAMS, next_step, prev_step
from rendering.ui.overlay.texts import TOOLBAR


def test_step_cycle():
    assert next_step([1, 2, 3], 1) == 2 and next_step([1, 2, 3], 3) == 1
    assert prev_step([1, 2, 3], 1) == 3 and prev_step([1, 2, 3], 2) == 1
    assert next_step(["a", "b"], "b") == "a" and prev_step(["a", "b"], "a") == "b"


def test_app_runs_frames_and_commands(make_app):
    app = make_app(launched=False)
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


def test_params_apply_now_or_at_restart(make_app):
    app = make_app(launched=False)
    app.do("setup_launch")
    old = config.MUTATION_STD
    app.do("mutation")                       # Applies at once
    assert config.MUTATION_STD != old and "mutation" not in app.pending
    app.do("obstacle_count")                 # Restart-only: pending
    assert "obstacle_count" in app.pending
    app.do("params_cancel")
    assert not app.pending
    assert all(key in PARAMS for key in app.pending)


def test_escape_quits_and_saves(make_app):
    app = make_app(launched=False)
    app.do("start_new")
    app.do("setup_launch")
    app.run(max_frames=3)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    app.run(max_frames=2)
    assert not app.running


def test_do_dispatch_table(make_app):
    app = make_app()
    # Every key and every tool bar button leads to a command
    toolbar = {item[0] for item in TOOLBAR if isinstance(item, tuple)}
    assert set(KEYS.values()) <= set(app._commands) and toolbar <= set(app._commands)
    assert set(PARAMS) <= set(app._commands)
    # Return value: True keeps the menu open
    assert app.do("no_such_action") is False and app.do("pause") is False
    assert app.do("mutation") is True and app.do("param:inc:mutation") is True
    assert app.do("profile:complet") is True and app.do("series:births") is True
    assert app.do("preset_prev") is True and app.do("series_default") is True
    # An unknown name after a known prefix does not crash
    assert app.do("start_load:/no/such/file.npz") is False
    app.run(max_frames=2)


def test_setup_screen_blocks_run_commands(make_app):
    app = make_app(launched=False)
    assert app.setup is not None
    app.do("pause")
    assert not app.paused or app.setup["cancel"] is False   # Blocked: the setup screen keeps the simulation stopped
    ticks = app.world.tick
    app.run(max_frames=3)
    assert app.world.tick == ticks

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
    assert app.state.setup is not None            # Setup screen at launch: nothing runs yet
    app.do("start_new")
    app.do("setup_launch")                   # New simulation, running
    assert app.state.setup is None and not app.state.paused
    app.run(max_frames=5)
    assert app.world.tick > 0
    for action in ("pause", "step", "chart", "chart", "graph", "graph", "debug", "color", "zoom_in", "view_fit",
                   "legend", "help", "panels", "minimap", "effects", "best", "follow", "speed_up", "speed_down"):
        app.do(action)
        app.run(max_frames=2)
    assert app.selection.selected is not None or not app.world.creatures


def test_params_apply_now_or_at_restart(make_app):
    app = make_app(launched=False)
    app.do("setup_launch")
    old = config.MUTATION_STD
    app.do("mutation")                       # Applies at once
    assert config.MUTATION_STD != old and "mutation" not in app.settings.pending
    app.do("obstacle_count")                 # Restart-only: pending
    assert "obstacle_count" in app.settings.pending
    app.do("params_cancel")
    assert not app.settings.pending
    assert all(key in PARAMS for key in app.settings.pending)


def test_escape_quits_and_saves(make_app):
    app = make_app(launched=False)
    app.do("start_new")
    app.do("setup_launch")
    app.run(max_frames=3)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    app.run(max_frames=2)
    assert not app.state.running


def test_do_dispatch_table(make_app):
    app = make_app()
    # Every key and every tool bar button leads to a command
    toolbar = {item[0] for item in TOOLBAR if isinstance(item, tuple)}
    assert set(KEYS.values()) <= app.commands.names and toolbar <= app.commands.names
    assert set(PARAMS) <= app.commands.names
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
    assert app.state.setup is not None
    app.do("pause")
    # Blocked: the setup screen keeps the simulation stopped
    assert not app.state.paused or app.state.setup["cancel"] is False
    ticks = app.world.tick
    app.run(max_frames=3)
    assert app.world.tick == ticks


def test_app_with_its_own_settings_leaves_the_config_module_alone(monkeypatch, tmp_path, renderer):
    """App(cfg=Settings(...)): menu changes, restarts and saves all go through cfg, never through the module."""
    import config
    from app import App
    own = config.Settings(SAVE_DIR=str(tmp_path / "mine"), LOAD_SETTINGS=False, LOAD_ON_START=False,
                          INITIAL_POPULATION=25, WORLD_SCALE=1)
    before = {name: getattr(config, name) for name in ("MUTATION_STD", "WORLD_SCALE", "ACTIVE_PROFILES", "SAVE_DIR")}
    app = App(own)
    try:
        assert app.cfg is own and app.sim.cfg is own and app.scene.cfg is own and app.hud.cfg is own
        app.do("start_new")
        app.do("setup_launch")
        app.do("mutation")                              # A setting of the menu: applied to own, not to the module
        app.do("world_scale")                           # Restart-only: pending, then applied at the restart
        app.do("restart_now")
        app.run(max_frames=3)
        assert own.MUTATION_STD != before["MUTATION_STD"] and own.WORLD_SCALE != before["WORLD_SCALE"]
        assert app.world.width == own.WORLD_WIDTH
        app.do("save_pop")
        assert (tmp_path / "mine" / "populations").is_dir() or (tmp_path / "mine").is_dir()
    finally:
        import gc
        import pygame
        del app
        gc.collect()
        pygame.quit()
    assert {name: getattr(config, name) for name in before} == before

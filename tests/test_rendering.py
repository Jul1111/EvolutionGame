"""Smoke tests of the interface: every panel, view and species is drawn for a few frames without a screen (SDL dummy
driver). They check that nothing raises and that the main on-screen states are reached, not what the pixels look
like."""
import pygame

from brain.profiles import PROFILES

PANEL_ACTIONS = ("legend", "help", "params_panel", "graph", "chart", "debug", "minimap", "effects", "panels")


def _frames(app, n=2):
    app.run(max_frames=n)


def test_every_panel_opens_and_draws(make_app):
    app = make_app()
    _frames(app, 5)
    app.do("best")                      # A selected creature: card, network, trail, debug cone
    for action in PANEL_ACTIONS:
        for _ in range(3):              # Every state of the cycle (hidden, small, large...), then back
            app.do(action)
            _frames(app)
    assert app.selected is not None


def test_every_color_mode_draws(make_app):
    app = make_app()
    app.do("best")
    labels = set()
    for _ in range(12):
        labels.add(app.scene.color_label())
        app.do("color")
        _frames(app)
    assert len(labels) >= 5
    app.do("legend")                    # The legend follows the colour mode
    for _ in range(len(labels)):
        app.do("color")
        _frames(app)


def test_every_species_network_and_card_draw(make_app):
    app = make_app(ACTIVE_PROFILES=list(PROFILES), INITIAL_POPULATION=60)
    app.do("restart_now")
    _frames(app)
    app.do("graph")
    app.do("graph")                     # Large network
    seen = set()
    for creature in list(app.world.creatures):
        if creature.profile in seen:
            continue
        seen.add(creature.profile)
        app.selected = creature
        _frames(app)
    assert seen == set(PROFILES)


def test_size_and_lineage_views(make_app):
    app = make_app()
    while app.scene.color_label() != "lignée":
        app.do("color")
    app.do("follow")                    # Follow the lineage
    for _ in range(3):
        _frames(app, 5)
    app.do("view_screen")
    app.do("view_fit")
    app.do("zoom_out")
    for _ in range(4):
        app.do("zoom_out")
    _frames(app)                        # Zoomed out beyond the map: copies of the torus


def test_start_menu_setup_and_help(make_app):
    app = make_app(launched=False)
    _frames(app, 3)                     # Start menu over the preview world
    app.do("start_load_list")
    _frames(app)
    app.do("start_back")
    app.do("start_new")                 # Settings screen of a new simulation
    _frames(app, 3)
    app.do("help")
    _frames(app)
    app.do("help")
    for key in ("mutation", "food", "fov", "size_mode"):
        app.do(key)
        _frames(app)


def test_window_changes_relayout(make_app):
    app = make_app()
    _frames(app)
    app.do("fullscreen")
    _frames(app, 3)
    app.do("fullscreen")
    pygame.event.post(pygame.event.Event(pygame.WINDOWSIZECHANGED, x=900, y=500, window=None))
    _frames(app, 3)
    assert app.layout is not None


def test_mouse_interaction(make_app):
    app = make_app()
    _frames(app, 3)
    world = app.layout.world
    center = world.center
    for ev in (pygame.event.Event(pygame.MOUSEMOTION, pos=center, rel=(0, 0), buttons=(0, 0, 0)),
               pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=center, button=1),
               pygame.event.Event(pygame.MOUSEMOTION, pos=(center[0] + 40, center[1] + 10), rel=(40, 10),
                                  buttons=(1, 0, 0)),
               pygame.event.Event(pygame.MOUSEBUTTONUP, pos=center, button=1),
               pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=2, flipped=False)):
        pygame.event.post(ev)
        _frames(app)
    app.do("params_panel")
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(200, 200), rel=(0, 0), buttons=(0, 0, 0)))
    _frames(app)


def test_extinction_is_reported(make_app):
    app = make_app()
    for creature in app.world.creatures:
        creature.energy = 0
    _frames(app, 5)
    assert app.sim.extinct and app.paused


def test_run_to_a_birth_and_a_death_with_effects(make_app):
    app = make_app(REPRO_THRESHOLD=60.0, MATURITY_AGE=5, INITIAL_ENERGY=100.0, AGE_MAX=300)
    app.do("effects")
    app.do("effects")
    app.do("speed_up")
    app.do("speed_up")
    _frames(app, 40)
    assert app.sim.total_births > 0


def test_legend_lists_every_kind_of_thing_in_the_world():
    from rendering.ui.overlay.legend import legend_entries
    kinds = {kind for kind, _, _ in legend_entries("énergie")}
    assert {"dot", "diamond", "anemone", "gradient", "cone"} <= kinds      # Food, poison, obstacle, colour, vision
    assert "gradient" not in {kind for kind, _, _ in legend_entries("lignée")}


def test_scene_and_hud_use_their_own_settings(make_app):
    """The world view and the HUD read their settings from cfg, not from the live module."""
    import config
    from rendering.ui.hud import Hud
    from rendering.world.scene import Scene
    own = config.Settings(WORLD_SCALE=2)
    scene, hud = Scene(own), Hud(own)
    assert scene.cfg is own and hud.cfg is own
    scene.world_changed()                       # Zoom limits from the 2x2 world, though the module says 1x1
    assert scene.fit_zoom == min(1.0, config.SCREEN_WIDTH / (2 * config.SCREEN_WIDTH),
                                 config.SCREEN_HEIGHT / (2 * config.SCREEN_HEIGHT))
    assert config.WORLD_SCALE == 1

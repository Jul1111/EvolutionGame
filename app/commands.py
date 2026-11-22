"""Commands: every action from the keyboard or from the menus goes through Commands.do(), a table of handlers."""
from functools import partial

import pygame

from app.settings import PARAMS


# Actions that do nothing while the setup screen is open: only its own buttons, the settings, the species and the view
SETUP_BLOCKED = ("pause", "step", "params_panel", "params_close", "end_gen", "restart_now", "save_pop", "load_pop",
                 "reset")

KEYS = {pygame.K_UP: "speed_up", pygame.K_DOWN: "speed_down", pygame.K_d: "debug", pygame.K_c: "color",
        pygame.K_SPACE: "pause", pygame.K_RIGHT: "step", pygame.K_g: "chart", pygame.K_n: "graph",
        pygame.K_f: "fullscreen", pygame.K_F11: "fullscreen", pygame.K_l: "legend", pygame.K_h: "help",
        pygame.K_p: "params_panel", pygame.K_b: "best", pygame.K_t: "follow", pygame.K_s: "save_pop",
        pygame.K_EQUALS: "zoom_in", pygame.K_PLUS: "zoom_in", pygame.K_KP_PLUS: "zoom_in",
        pygame.K_MINUS: "zoom_out", pygame.K_KP_MINUS: "zoom_out", pygame.K_0: "view_fit",
        pygame.K_KP0: "view_fit", pygame.K_1: "view_screen", pygame.K_KP1: "view_screen", pygame.K_v: "cam_follow",
        pygame.K_TAB: "panels", pygame.K_m: "minimap", pygame.K_e: "effects"}


class Commands:
    def __init__(self, cfg, display, scene, hud, overlay, state, selection, session, settings):
        self.cfg, self.display, self.scene, self.hud, self.overlay = cfg, display, scene, hud, overlay
        self.state, self.selection, self.session, self.settings = state, selection, session, settings
        self._build()

    def _cycle_panel(self, big_owner, big_attr, shown_attr, toggle):
        """Hidden → small (side bar) → large (over the world) → hidden, for the curves and the network view.
        The large view is the attribute `big_attr` of `big_owner`."""
        if getattr(big_owner, big_attr):
            setattr(big_owner, big_attr, False)
        elif getattr(self.hud, shown_attr):
            toggle()
            setattr(big_owner, big_attr, True)
        else:
            toggle()

    def _build(self):
        hud, overlay, scene, display = self.hud, self.overlay, self.scene, self.display
        state, selection, session, settings = self.state, self.selection, self.session, self.settings
        toggle, keep_open = self._toggle, self._keep_open
        self._commands = {
            # Speed and view
            "speed_up": partial(self._change_speed, +1),
            "speed_down": partial(self._change_speed, -1),
            "pause": self._pause,
            "step": self._step,
            "fullscreen": display.toggle_fullscreen,
            "zoom_in": partial(self._zoom, 1.25),
            "zoom_out": partial(self._zoom, 0.8),
            "view_fit": scene.view_all,
            "view_screen": scene.view_screen,
            "cam_follow": partial(toggle, selection, "cam_follow"),
            "cam_follow_off": partial(setattr, selection, "cam_follow", False),   # The mini-map moved the view by hand
            # What is shown
            "debug": self._cycle_debug,
            "color": scene.cycle_color_mode,
            "chart": partial(self._cycle_panel, overlay, "chart_big", "show_chart", hud.toggle_chart),
            "graph": partial(self._cycle_panel, overlay.net, "big", "show_graph", hud.toggle_graph),
            "panels": partial(toggle, hud, "visible"),
            "minimap": partial(toggle, overlay.minimap, "enabled"),
            "effects": partial(toggle, scene.effects, "enabled"),
            "legend": partial(toggle, overlay.legend, "open"),
            "help": partial(toggle, overlay.help, "open"),
            "series_default": keep_open(hud.reset_series),
            # Selection
            "best": self._best,
            "follow": self._follow,
            # Settings panel and presets
            "params_panel": partial(toggle, overlay.params, "open"),
            "params_close": partial(setattr, overlay.params, "open", False),
            "params_cancel": settings.params_cancel,
            "preset_prev": keep_open(partial(settings.move_preset, -1)),
            "preset_next": keep_open(partial(settings.move_preset, +1)),
            "preset_save": keep_open(settings.save_preset),
            "preset_apply": keep_open(settings.apply_preset),
            # Populations
            "restart_now": session.restart_random,
            "save_pop": session.save_population,
            "load_pop": session.load_last_population,
            # Start menu and setup screen
            "start_continue": session.start_continue,
            "start_load_list": session.open_load_list,
            "start_back": session.start_back,
            "start_new": session.start_new,
            "reset": partial(session.open_setup, can_cancel=True),
            "setup_launch": session.setup_launch,
            "setup_resume": session.setup_resume,
            "setup_cancel": session.setup_cancel,
            "quit": partial(setattr, state, "running", False),
            # A setting of the menu: next preset value (now, or at the next restart)
            **{key: keep_open(partial(settings.cycle_param, key)) for key in PARAMS},
        }
        # Commands with an argument after the prefix ("profile:complet")
        self._prefixed = {
            "profile:": keep_open(settings.toggle_profile),
            "param:": keep_open(settings.step_param),
            "series:": keep_open(hud.toggle_series),
            "start_load:": session.start_load,
        }

    @property
    def names(self):
        """Every action name that runs a command (without the prefixed ones)."""
        return set(self._commands)

    @staticmethod
    def _toggle(obj, attr):
        setattr(obj, attr, not getattr(obj, attr))

    @staticmethod
    def _keep_open(handler):
        def run(*args):
            handler(*args)
            return True
        return run

    def do(self, action):
        """Runs a command. Returns True to keep the menu open."""
        if self.state.setup is not None and action in SETUP_BLOCKED:
            return False   # Setup screen: only its own buttons, the settings, the species and the view
        handler = self._commands.get(action)
        if handler is not None:
            return bool(handler())
        for prefix, prefixed in self._prefixed.items():
            if action.startswith(prefix):
                return bool(prefixed(action[len(prefix):]))
        return False

    def _change_speed(self, step):
        self.state.speed_index = max(0, min(self.state.speed_index + step, len(self.cfg.SPEED_STEPS) - 1))

    def _pause(self):
        self.state.paused = not self.state.paused

    def _step(self):
        self.state.step_request = self.state.paused

    def _cycle_debug(self):
        self.selection.debug_mode = (self.selection.debug_mode + 1) % 3

    def _zoom(self, factor):
        vw, vh = self.scene.size
        self.scene.zoom_by(factor, (vw / 2, vh / 2))

    def _best(self):
        self.selection.best(self.session.world)

    def _follow(self):
        self.selection.toggle_follow(self.session.world)

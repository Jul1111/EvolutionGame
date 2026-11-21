"""One frame: simulation ticks within the time budget, selection following, drawing, and the main loop."""
import os
import time

import pygame

from brain.profiles import PROFILES
from rendering.ui.menu import profile_label
from rendering.ui.overlay.texts import PARAM_INFO
from rendering.ui.series import SERIES_BY_KEY
from utils.timefmt import format_time
from app.settings import PARAMS


class Frame:
    """One frame and the main loop: simulation ticks within the time budget, drawing, events."""

    def __init__(self, cfg, display, screen, scene, hud, menu, overlay, state, selection, session, settings, events):
        self.cfg, self.display, self.screen = cfg, display, screen
        self.scene, self.hud, self.menu, self.overlay = scene, hud, menu, overlay
        self.state, self.selection, self.session = state, selection, session
        self.settings, self.events = settings, events
        self.clock = pygame.time.Clock()

    def _run_ticks(self, ticks_to_run):
        """Runs up to `ticks_to_run` ticks within the time budget. Returns the number run.
        Time budget: at high speed the simulation only gets what the drawing leaves of a frame at MIN_FPS (the drawing
        time is measured every frame: bigger window, more panels → less simulation, same fluidity). The real speed
        (ticks per frame actually run) is shown next to the asked one."""
        state, sim = self.state, self.session.sim
        sim_budget = max(self.cfg.SIM_MIN_BUDGET_MS, 1000 / self.cfg.MIN_FPS - state.draw_ms)
        deadline = time.perf_counter() + sim_budget / 1000
        ran = 0
        for _ in range(ticks_to_run):
            if ran and time.perf_counter() > deadline:
                break
            ran += 1
            going = sim.step()
            self.selection.after_tick(sim, self.overlay)
            if not going:
                state.paused = True
                self.hud.reload_stats()
                self.overlay.toast(f"Extinction à {format_time(sim.world.tick)}. Sauvegarde → Repartir de zéro, "
                                   "ou charger une population.", 8)
                break
            if sim.new_sample:
                self.hud.reload_stats()
        return ran

    def _menu_state(self, speed, chart_state, net_state):
        """Values shown by the labels and check boxes of the menu bar."""
        pending, pending_profiles = self.settings.pending, self.settings.pending_profiles
        scene, hud, overlay, selection = self.scene, self.hud, self.overlay, self.selection
        last_saved = self.session.last_saved
        shown = self.settings.profiles_shown()
        return {
            "speed": speed, "real_speed": self.state.real_speed, "paused": self.state.paused,
            "debug": ("off", "sélection", "toutes")[selection.debug_mode],
            "color": scene.color_label(), "chart": ("non", "panneau", "grand")[chart_state],
            "graph": ("non", "petit", "grand")[net_state],
            "legend": overlay.legend_open, "follow": selection.follow,
            "fullscreen": self.display.fullscreen,
            **{"s_" + key: key in hud.chart_keys for key in SERIES_BY_KEY},
            **{a: fmt(pending.get(a, getattr(self.cfg, name))) + ("  *" if a in pending else "")
               for a, (name, _, fmt) in PARAMS.items()},
            "cam_follow": selection.cam_follow, "minimap": overlay.minimap.enabled, "effects": scene.effects.enabled,
            "panels": hud.visible,
            "load_pop": (f"Charger : {os.path.basename(last_saved)}" if last_saved
                         else "Charger une population (aucune)"),
            **{"p_" + n: n in shown for n in PROFILES},
            **{"pl_" + n: profile_label(n) + ("  *" if pending_profiles is not None
                                              and (n in pending_profiles) != (n in self.cfg.ACTIVE_PROFILES) else "")
               for n in PROFILES},
            "reset": "Nouvelle simulation...",
        }

    def _draw(self, speed, ran, ticks_to_run):
        window = self.display.surface()
        scene, hud, overlay, sim, world = self.scene, self.hud, self.overlay, self.session.sim, self.session.world
        state, selection, settings = self.state, self.selection, self.settings
        selected = selection.selected
        if selection.cam_follow and selected is not None and selected.alive:
            scene.center_on(selected.x, selected.y)

        # Draw the world, then the heads-up display (HUD)
        self.display.begin()   # Graphics card: a new picture (rendering/backend/gpu.py)
        scene.draw(self.display.canvas(self.screen.layout.world), world, selection.debug_mode, selected,
                   selection.trail)
        hud.draw(self.screen.sidebar, self.screen.strip_view, world, self.clock.get_fps(), speed,
                 {"births": sim.total_births, "deaths": sim.total_deaths, "extinct": sim.extinct,
                  "pop_max": sim.pop_max, "setup": state.setup is not None},
                 selection.debug_mode, state.paused, selected, scene.color_label())
        net_state = 2 if overlay.net_big else (1 if hud.show_graph else 0)
        chart_state = 2 if overlay.chart_big else (1 if hud.show_chart else 0)
        params_info = [(a, *PARAM_INFO.get(a, (a, "")), fmt(getattr(self.cfg, name)),
                        fmt(settings.pending[a]) if a in settings.pending else None)
                       for a, (name, _, fmt) in PARAMS.items()] if overlay.params_open else []
        state.real_speed = 0.9 * state.real_speed + 0.1 * ran if ticks_to_run else 0.0   # Smoothed ticks per frame
        overlay.draw(window, {"paused": state.paused, "speed": speed, "real_speed": state.real_speed,
                              "debug": selection.debug_mode, "follow": selection.follow, "graph": net_state,
                              "chart": chart_state, "cam_follow": selection.cam_follow,
                              "profiles": list(settings.profiles_shown()),
                              "profiles_pending": settings.pending_profiles is not None},
                     world, selected, params_info)
        self.menu.draw(window, self._menu_state(speed, chart_state, net_state))
        overlay.draw_tips(window, world, selected, self.menu.open_index is not None)
        self.display.flip()

    def run(self, max_frames=None):
        """The event loop. `max_frames`: stop after that many frames (tests)."""
        state, screen = self.state, self.screen
        frames = 0
        while state.running and (max_frames is None or frames < max_frames):
            frames += 1
            screen.update()
            self.events.handle()
            if screen.stale():
                continue   # The window changed during the events (fullscreen): relayout before drawing

            speed = self.cfg.SPEED_STEPS[state.speed_index]
            # Run several simulation ticks per frame, according to the chosen speed
            ticks_to_run = (0 if state.setup is not None else
                            1 if state.step_request else
                            0 if state.paused else speed)
            ran = self._run_ticks(ticks_to_run)

            draw_start = time.perf_counter()   # From here to the flip: drawing (measured for the simulation budget)
            self._draw(speed, ran, ticks_to_run)
            state.draw_ms = 0.8 * state.draw_ms + 0.2 * (time.perf_counter() - draw_start) * 1000   # Smoothed
            self.clock.tick(self.cfg.FPS)

"""One frame: simulation ticks within the time budget, selection following, drawing, and the main loop."""
import os
import time


import config
from brain.profiles import PROFILES
from evolution.continuous import success_key
from rendering.ui.menu import profile_label
from rendering.ui.overlay.texts import PARAM_INFO
from rendering.ui.series import SERIES_BY_KEY
from utils.timefmt import format_time
from app.settings import PARAMS


class FrameMixin:
    def _follow_selection(self):
        """After a tick: records the trail, and when the selected creature died, moves to its heir (T) or to the new
        best one (B)."""
        selected = self.selected
        if selected is None:
            return
        if selected.alive:
            self.trail.append((selected.x, selected.y))
        elif self.follow or self.auto_best:
            # T: the lineage goes on through its youngest living descendant; if the lineage is extinct,
            # or after B: the new best one (most children)
            heir = self.sim.descendant_of(selected) if self.follow else None
            if heir is None and self.world.creatures:
                heir = max((c for c in self.world.creatures if c.alive), key=success_key, default=None)
                if heir is not None:
                    self.overlay.toast(f"Morte. Nouvelle meilleure : {heir.children} petits, "
                                       f"génération {heir.lineage_gen}", 2.5)
            if heir is not None:
                self.selected = heir
                self.trail.clear()

    def _run_ticks(self, ticks_to_run):
        """Runs up to `ticks_to_run` ticks within the time budget. Returns the number run.
        Time budget: at high speed the simulation only gets what the drawing leaves of a frame at MIN_FPS (the drawing
        time is measured every frame: bigger window, more panels → less simulation, same fluidity). The real speed
        (ticks per frame actually run) is shown next to the asked one."""
        sim_budget = max(config.SIM_MIN_BUDGET_MS, 1000 / config.MIN_FPS - self.draw_ms)
        deadline = time.perf_counter() + sim_budget / 1000
        ran = 0
        for _ in range(ticks_to_run):
            if ran and time.perf_counter() > deadline:
                break
            ran += 1
            going = self.sim.step()
            self._follow_selection()
            if not going:
                self.paused = True
                self.hud.reload_stats()
                self.overlay.toast(f"Extinction à {format_time(self.world.tick)}. Sauvegarde → Repartir de zéro, "
                                   "ou charger une population.", 8)
                break
            if self.sim.new_sample:
                self.hud.reload_stats()
        return ran

    def _menu_state(self, speed, chart_state, net_state):
        """Values shown by the labels and check boxes of the menu bar."""
        pending, pending_profiles = self.pending, self.pending_profiles
        scene, hud, overlay = self.scene, self.hud, self.overlay
        shown = self._profiles_shown()
        return {
            "speed": speed, "real_speed": self.real_speed, "paused": self.paused,
            "debug": ("off", "sélection", "toutes")[self.debug_mode],
            "color": scene.color_label(), "chart": ("non", "panneau", "grand")[chart_state],
            "graph": ("non", "petit", "grand")[net_state],
            "legend": overlay.legend_open, "follow": self.follow,
            "fullscreen": self.display.fullscreen,
            **{"s_" + key: key in hud.chart_keys for key in SERIES_BY_KEY},
            **{a: fmt(pending.get(a, getattr(config, name))) + ("  *" if a in pending else "")
               for a, (name, _, fmt) in PARAMS.items()},
            "cam_follow": self.cam_follow, "minimap": overlay.minimap.enabled, "effects": scene.effects.enabled,
            "panels": hud.visible,
            "load_pop": (f"Charger : {os.path.basename(self.last_saved)}" if self.last_saved
                         else "Charger une population (aucune)"),
            **{"p_" + n: n in shown for n in PROFILES},
            **{"pl_" + n: profile_label(n) + ("  *" if pending_profiles is not None
                                              and (n in pending_profiles) != (n in config.ACTIVE_PROFILES) else "")
               for n in PROFILES},
            "reset": "Nouvelle simulation...",
        }

    def _draw(self, speed, ran, ticks_to_run):
        window = self.display.surface()
        scene, hud, overlay, sim, world = self.scene, self.hud, self.overlay, self.sim, self.world
        if self.cam_follow and self.selected is not None and self.selected.alive:
            scene.center_on(self.selected.x, self.selected.y)

        # Draw the world, then the heads-up display (HUD)
        self.display.begin()   # Graphics card: a new picture (rendering/backend/gpu.py)
        scene.draw(self.display.canvas(self.layout.world), world, self.debug_mode, self.selected, self.trail)
        hud.draw(self.sidebar, self.strip_view, world, self.clock.get_fps(), speed,
                 {"births": sim.total_births, "deaths": sim.total_deaths, "extinct": sim.extinct,
                  "pop_max": sim.pop_max, "setup": self.setup is not None},
                 self.debug_mode, self.paused, self.selected, scene.color_label())
        net_state = 2 if overlay.net_big else (1 if hud.show_graph else 0)
        chart_state = 2 if overlay.chart_big else (1 if hud.show_chart else 0)
        params_info = [(a, *PARAM_INFO.get(a, (a, "")), fmt(getattr(config, name)),
                        fmt(self.pending[a]) if a in self.pending else None)
                       for a, (name, _, fmt) in PARAMS.items()] if overlay.params_open else []
        self.real_speed = 0.9 * self.real_speed + 0.1 * ran if ticks_to_run else 0.0   # Smoothed ticks per frame
        overlay.draw(window, {"paused": self.paused, "speed": speed, "real_speed": self.real_speed,
                              "debug": self.debug_mode, "follow": self.follow, "graph": net_state,
                              "chart": chart_state, "cam_follow": self.cam_follow,
                              "profiles": list(self._profiles_shown()),
                              "profiles_pending": self.pending_profiles is not None},
                     world, self.selected, params_info)
        self.menu.draw(window, self._menu_state(speed, chart_state, net_state))
        overlay.draw_tips(window, world, self.selected, self.menu.open_index is not None)
        self.display.flip()

    def run(self, max_frames=None):
        """The event loop. `max_frames`: stop after that many frames (tests)."""
        frames = 0
        while self.running and (max_frames is None or frames < max_frames):
            frames += 1
            self._update_layout()
            self._handle_events()
            surface = self.display.surface()
            if self.display.surface_version != self.last_surface_version or surface.get_size() != self.last_size:
                continue   # The window changed during the events (fullscreen): relayout before drawing

            speed = config.SPEED_STEPS[self.speed_index]
            # Run several simulation ticks per frame, according to the chosen speed
            ticks_to_run = 0 if self.setup is not None else (1 if self.step_request else (0 if self.paused else speed))
            ran = self._run_ticks(ticks_to_run)

            draw_start = time.perf_counter()   # From here to the flip: drawing (measured for the simulation budget)
            self._draw(speed, ran, ticks_to_run)
            self.draw_ms = 0.8 * self.draw_ms + 0.2 * (time.perf_counter() - draw_start) * 1000   # Smoothed
            self.clock.tick(config.FPS)

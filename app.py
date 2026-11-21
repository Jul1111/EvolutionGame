"""The application: window, event loop, commands (keyboard and menus), settings. main.py only starts it.

App owns the state of a session (running simulation, selection, camera, pause, pending settings). Every command, from
the keyboard or from the menus, goes through App.do(action). The rendering modules never change anything: they return
action names, App runs them."""
import os
import random
import time
from collections import deque

import pygame

import config
from brain.profiles import PROFILES
from evolution.continuous import (ContinuousSimulation, success_key, save_population, load_population, snapshot_path,
                                  autosave_path, latest_snapshot, populations_dir)
from rendering.backend.display import Display
from rendering.ui.hud import Hud
from rendering.ui.series import SERIES_BY_KEY
from rendering.ui.layout import compute_layout
from rendering.ui.menu import MenuBar, profile_label
from rendering.ui.overlay import Overlay
from rendering.ui.overlay.texts import PARAM_INFO
from rendering.ui.startmenu import StartMenu
from rendering.world.scene import Scene, pick_creature
from utils.presets import PresetBrowser
from utils.settings import load_settings, save_settings
from utils.timefmt import format_time

# Settings editable from the menu: action → (config name, values it cycles through, text shown).
PARAMS = {
    "mutation": ("MUTATION_STD", [0.02, 0.05, 0.1, 0.2, 0.3], lambda v: f"{v:g}"),
    "repro": ("REPRO_THRESHOLD", [80.0, 100.0, 120.0, 150.0, 180.0], lambda v: f"{v:g}"),
    "age_max": ("AGE_MAX", [0, 3000, 6000, 12000], lambda v: format_time(v) if v else "jamais"),
    "fov": ("VISION_FOV_DEGREES", [60, 90, 120, 180, 270, 360], lambda v: "tout autour" if v >= 360 else f"{v}°"),
    "food": ("FOOD_COUNT", [5, 10, 20, 30, 40, 60], str),
    "food_min": ("FOOD_COUNT_MIN", [5, 10, 15, 20, 25, 30, 40, 60], str),
    "food_pressure": ("FOOD_PRESSURE_POP", [100, 200, 300, 400, 600], str),
    "food_adapt": ("FOOD_ADAPT_TICKS", [0, 1200, 3000, 6000, 12000], lambda v: format_time(v) if v else "aussitôt"),
    "food_energy": ("FOOD_ENERGY", [15.0, 30.0, 45.0, 60.0], lambda v: f"{v:g}"),
    "respawn": ("FOOD_RESPAWN_DELAY", [0, 30, 60, 120, 300], lambda v: f"{v} ticks"),
    "poison_count": ("POISON_COUNT", [0, 3, 5, 8, 12, 20, 30], str),
    "poison_energy": ("POISON_ENERGY", [20.0, 40.0, 60.0, 80.0], lambda v: f"{v:g}"),
    "obstacle_count": ("OBSTACLE_COUNT", [0, 3, 6, 10, 15, 25, 35], str),
    "founders": ("INITIAL_POPULATION", [50, 100, 200, 300, 400], str),
    "size_mode": ("SIZE_MODE", ["fixe", "neutre", "actif"], str),
    "world_scale": ("WORLD_SCALE", [1, 2, 3], lambda v: f"{v}×{v} écrans"),
}
# Settings that only take effect on a new world (obstacles are drawn when the world is created).
# Every other setting applies at once.
RESTART_PARAMS = {"obstacle_count", "world_scale", "size_mode", "founders"}   # size_mode: bodies are set at birth

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


def next_step(steps, current):
    """Next value of the list after `current` (the first greater one if it is not in the list), wrapping around."""
    if isinstance(current, bool):
        return not current
    if isinstance(current, str):   # Names (e.g. fitness): next in the list order
        return steps[(steps.index(current) + 1) % len(steps)] if current in steps else steps[0]
    return next((v for v in steps if v > current + 1e-9), steps[0])


def prev_step(steps, current):
    """Previous value of the list before `current`, wrapping around."""
    if isinstance(current, bool):
        return not current
    if isinstance(current, str):   # Names (e.g. fitness): previous in the list order
        return steps[(steps.index(current) - 1) % len(steps)] if current in steps else steps[0]
    return next((v for v in reversed(steps) if v < current - 1e-9), steps[-1])


class App:
    def __init__(self):
        pygame.init()
        self.rng = random.Random(config.SEED)

        # The window fits the desktop and can be resized or put in fullscreen (key F). The layout (world, side bar,
        # curves strip) is recomputed for the window size and drawn at its real resolution: no bars, no blur.
        self.display = Display("Evolution Simulator")
        self.layout = None
        self.sidebar = None
        self.strip_view = None
        self.last_generation = None
        self.last_size = None
        self.clock = pygame.time.Clock()

        # Rendering: world scene (background, food, creatures) and HUD (panel, curves)
        self.scene = Scene()
        self.hud = Hud()
        self.hud.renderer = self.display.renderer_label()   # «GPU» or «CPU», shown next to the FPS
        self.menu = MenuBar()
        self.overlay = Overlay(self.hud, self.scene)   # Tool bar, legend, help, hover tips, settings panel, large network
        self.hud.lineage = self.scene.lineage          # Living lineages in the Population panel
        self.presets = PresetBrowser()                 # Saved settings (saves/presets/), browsed in the settings panel
        self.overlay.presets = self.presets

        # View and selection
        self.cam_follow = False       # True: the camera stays on the selected creature
        self.drag_start = None        # Mouse position of a left press in the world (select on release, pan if dragged)
        self.dragging = False
        self.follow = False           # True: when the selected creature dies, its youngest living descendant is selected
        self.debug_mode = 0           # 0 = off, 1 = selected (else oldest living) creature, 2 = all living creatures
        self.selected = None          # Creature picked with a click
        self.auto_best = False        # True after B: when the selected creature dies, the new best one is selected
        self.trail = deque(maxlen=config.TRAIL_LENGTH)   # Recent positions of the selected creature, one per tick

        # Run state
        self.paused = False
        self.step_request = False
        self.speed_index = 0
        self.real_speed = 0.0   # Ticks per frame actually run (time budget), smoothed
        self.draw_ms = 10.0     # Drawing time of a frame (smoothed), for the simulation budget
        self.running = True

        # Settings chosen in an earlier session replace the values of config.py (saves/settings.json)
        restored = load_settings({name for name, _, _ in PARAMS.values()} | {"ACTIVE_PROFILES"})
        self.scene.world_changed()
        if restored:
            print("Réglages du menu repris : " + ", ".join(f"{n} {old} → {new}" for n, (old, new) in restored.items())
                  + " (valeurs de config.py ignorées ; LOAD_SETTINGS = False pour les désactiver)")
        self.pending = {}               # action → value waiting for the next restart (RESTART_PARAMS only)
        self.pending_profiles = None    # Species ticked in the menu (list), applied at the next restart from zero

        # Continuous evolution (evolution/continuous.py): births, deaths, no generations. timeline.csv feeds the curves.
        self.timeline = os.path.join(config.SAVE_DIR, "timeline.csv")
        self.hud.timeline_path = self.timeline

        # Setup screen: the simulation does not run until it is launched from the settings panel. Behind it, a preview
        # world (nothing written to timeline.csv). setup = None (running) or {"resume": bool, "cancel": bool}.
        self.sim = ContinuousSimulation(self.rng)
        # At launch: the start menu (Continuer / Charger / Nouvelle simulation), then the setup screen for a new one
        self.setup = {"resume": False, "cancel": False, "from_start": True}
        self.overlay.setup = self.setup
        self.overlay.start = StartMenu(autosave_path() if config.LOAD_ON_START else None, populations_dir())
        self.hud.reload_stats(sorted({c.profile for c in self.world.creatures}, key=list(PROFILES).index))
        self.last_saved = latest_snapshot()

    @property
    def world(self):
        return self.sim.world

    # ---------------------------------------------------------------- simulation lifecycle

    def _new_sim(self, founders=None, start_tick=0, append=False):
        return ContinuousSimulation(self.rng, self.timeline, founders=founders, start_tick=start_tick, append=append)

    def _archive_timeline(self):
        """A new population starts a new timeline: the old one is set aside (timestamped), not deleted."""
        if os.path.exists(self.timeline):
            os.replace(self.timeline, self.timeline[:-4] + time.strftime("_ancien_%Y%m%d_%H%M%S.csv"))

    def _begin(self, sim, reload_species):
        """Common end of restart / resume: the new simulation replaces the old one, selection and trail are cleared."""
        self.sim = sim
        self.selected = None
        self.paused = False
        self.trail.clear()
        self.hud.reload_stats(reload_species)

    def restart(self, founders=None):
        """New population: random founders of the ticked species, or a saved population (founders)."""
        old_scale = config.WORLD_SCALE
        self._apply_pending()
        if config.WORLD_SCALE != old_scale:
            self.scene.world_changed()
        self._archive_timeline()
        self._begin(self._new_sim(founders), list(founders) if founders else config.ACTIVE_PROFILES)

    def _resume_autosave(self):
        """Start from the population kept when the game was last closed, with its timeline."""
        founders, tick = load_population(autosave_path(), with_tick=True)
        if not founders:
            return False
        self._apply_pending()
        self.scene.world_changed()
        self._begin(self._new_sim(founders, start_tick=tick, append=True), list(founders))
        self.overlay.toast(f"Population reprise : {len(self.world.creatures)} créatures, temps {format_time(tick)}")
        return True

    def _open_setup(self, can_cancel):
        """Settings screen before a new simulation: everything set there applies when it is launched."""
        self.setup = {"resume": False, "cancel": can_cancel}
        self.overlay.setup = self.setup
        self.overlay.params_open = True
        self.paused = True

    def _close_setup(self):
        self.setup = None
        self.overlay.setup = None
        self.overlay.params_open = False

    # ---------------------------------------------------------------- settings

    def _apply_param(self, key, value):
        """Setting changed in the menu: now, or at the next restart for RESTART_PARAMS (or for every setting while
        the setup screen is open: nothing runs yet)."""
        name = PARAMS[key][0]
        if key in RESTART_PARAMS or self.setup is not None:
            if value == getattr(config, name):
                self.pending.pop(key, None)
            else:
                self.pending[key] = value
        else:
            setattr(config, name, value)
            self.sim.update_food(0)   # Food and poison counts or energies take effect now (level kept, sources resized)
            self.world.resize_items(self.sim.food_per_screen())
        self._persist_settings()

    def _settings_values(self):
        """The settings as they will be after the next restart (pending ones included)."""
        values = {name: self.pending.get(action, getattr(config, name)) for action, (name, _, _) in PARAMS.items()}
        values["ACTIVE_PROFILES"] = list(self._profiles_shown())
        return values

    def _profiles_shown(self):
        return config.ACTIVE_PROFILES if self.pending_profiles is None else self.pending_profiles

    def _persist_settings(self):
        """Keeps the settings chosen in the menu (pending ones included) for the next launch."""
        save_settings(self._settings_values())

    def _apply_pending(self):
        for action, value in self.pending.items():
            setattr(config, PARAMS[action][0], value)
        self.pending.clear()
        if self.pending_profiles is not None:
            config.ACTIVE_PROFILES = list(self.pending_profiles)
            self.pending_profiles = None

    def _toggle_profile(self, name):
        """Tick or untick a species. At least one must stay. Back to the active list = nothing pending."""
        current = list(self._profiles_shown())
        if name in current:
            if len(current) > 1:
                current.remove(name)
        else:
            current.append(name)
        current = [p for p in PROFILES if p in current]
        self.pending_profiles = None if current == config.ACTIVE_PROFILES else current
        self._persist_settings()

    def _apply_preset(self):
        values = self.presets.load()
        if not values:
            return
        for action, (name, _, _) in PARAMS.items():
            if name in values:
                self._apply_param(action, values[name])
        if values.get("ACTIVE_PROFILES"):
            wanted = [p for p in PROFILES if p in values["ACTIVE_PROFILES"]]
            self.pending_profiles = None if wanted == config.ACTIVE_PROFILES else wanted
            self._persist_settings()
        self.overlay.toast("Préréglage appliqué")

    # ---------------------------------------------------------------- commands

    def _cycle_panel(self, big_attr, shown_attr, toggle):
        """Hidden → small (side bar) → large (over the world) → hidden, for the curves and the network view."""
        if getattr(self.overlay, big_attr):
            setattr(self.overlay, big_attr, False)
        elif getattr(self.hud, shown_attr):
            toggle()
            setattr(self.overlay, big_attr, True)
        else:
            toggle()

    def _select_best(self):
        self.selected = max(self.world.creatures, key=success_key)
        self.trail.clear()
        self.cam_follow = True

    def do(self, action):
        """Runs a command. Returns True to keep the menu open."""
        if self.setup is not None and action in SETUP_BLOCKED:
            return False
        overlay, hud, scene = self.overlay, self.hud, self.scene
        if action == "speed_up":
            self.speed_index = min(self.speed_index + 1, len(config.SPEED_STEPS) - 1)
        elif action == "speed_down":
            self.speed_index = max(self.speed_index - 1, 0)
        elif action == "debug":
            self.debug_mode = (self.debug_mode + 1) % 3
        elif action == "color":
            scene.cycle_color_mode()
        elif action == "pause":
            self.paused = not self.paused
        elif action == "step":
            self.step_request = self.paused
        elif action == "chart":
            self._cycle_panel("chart_big", "show_chart", hud.toggle_chart)
        elif action == "graph":
            self._cycle_panel("net_big", "show_graph", hud.toggle_graph)
        elif action == "panels":
            hud.visible = not hud.visible
        elif action == "minimap":
            overlay.minimap.enabled = not overlay.minimap.enabled
        elif action == "effects":
            scene.effects.enabled = not scene.effects.enabled
        elif action == "cam_follow_off":
            self.cam_follow = False   # The mini-map moved the view by hand
        elif action in ("preset_prev", "preset_next"):
            self.presets.refresh()
            self.presets.move(-1 if action == "preset_prev" else 1)
            return True
        elif action == "preset_save":
            overlay.toast(f"Préréglage enregistré : saves/presets/{self.presets.save(self._settings_values())}")
            return True
        elif action == "preset_apply":
            self._apply_preset()
            return True
        elif action == "legend":
            overlay.legend_open = not overlay.legend_open
        elif action == "help":
            overlay.help_open = not overlay.help_open
        elif action == "params_panel":
            overlay.params_open = not overlay.params_open
        elif action == "params_close":
            overlay.params_open = False
        elif action == "params_cancel":
            self.pending.clear()
            self._persist_settings()
        elif action.startswith("profile:"):
            self._toggle_profile(action[len("profile:"):])
            return True
        elif action in ("zoom_in", "zoom_out"):
            vw, vh = scene.size
            scene.zoom_by(1.25 if action == "zoom_in" else 0.8, (vw / 2, vh / 2))
        elif action == "view_fit":
            scene.view_all()
        elif action == "view_screen":
            scene.view_screen()
        elif action == "cam_follow":
            self.cam_follow = not self.cam_follow
        elif action.startswith("param:"):
            # Arrows of the settings panel: previous / next preset. Back to the value in force = nothing pending.
            _, direction, key = action.split(":")
            name, steps, _ = PARAMS[key]
            current = self.pending.get(key, getattr(config, name))
            self._apply_param(key, prev_step(steps, current) if direction == "dec" else next_step(steps, current))
            return True
        elif action == "best":
            if self.world.creatures:
                self._select_best()
                self.auto_best = True   # Stays on «the best»: at its death, the new best one
        elif action == "follow":
            self.follow = not self.follow
            if self.follow and self.selected is None and self.world.creatures:
                self._select_best()
        elif action == "fullscreen":
            self.display.toggle_fullscreen()
        elif action == "restart_now":
            self.restart()
            overlay.toast("Nouvelle population tirée au hasard")
        elif action == "save_pop":
            if self.world.creatures:
                self.last_saved = snapshot_path("manuelle")
                save_population(self.sim, self.last_saved)
                overlay.toast(f"Population sauvegardée : saves/populations/{os.path.basename(self.last_saved)}")
        elif action == "load_pop":
            if self.last_saved and os.path.exists(self.last_saved):
                founders = load_population(self.last_saved)
                if founders:
                    self.restart(founders)
                    overlay.toast(f"Population chargée : {os.path.basename(self.last_saved)}")
            else:
                overlay.toast("Aucune population sauvegardée (S pour sauvegarder)")
        elif action.startswith("series:"):
            hud.toggle_series(action[len("series:"):])
            return True   # Menu stays open to pick several curves
        elif action == "series_default":
            hud.reset_series()
            return True
        elif action in PARAMS:
            # Menu click: next preset value (now, or at the next restart). The menu stays open to click again.
            name, steps, _ = PARAMS[action]
            self._apply_param(action, next_step(steps, self.pending.get(action, getattr(config, name))))
            return True
        elif action == "start_continue":
            if self._resume_autosave():
                overlay.start = None
                self._close_setup()
        elif action == "start_load_list":
            overlay.start.view = "load"
        elif action == "start_back":
            overlay.params_open = False   # Back from the settings of a new simulation, or from the load list
            if overlay.start is None:
                overlay.start = StartMenu(autosave_path() if config.LOAD_ON_START else None, populations_dir())
            overlay.start.view = "main"
        elif action == "start_new":
            overlay.start = None
            overlay.params_open = True
        elif action.startswith("start_load:"):
            path = action[len("start_load:"):]
            founders = load_population(path)
            if founders:
                self.restart(founders)
                self.last_saved = path
                overlay.start = None
                self._close_setup()
                self.paused = False
                overlay.toast(f"Population chargée : {os.path.basename(path)}")
        elif action == "quit":
            self.running = False
        elif action == "reset":
            self._open_setup(can_cancel=True)
        elif action == "setup_launch":
            self.restart()
            self._close_setup()
        elif action == "setup_resume":
            if self._resume_autosave():
                self._close_setup()
        elif action == "setup_cancel":
            self.pending.clear()
            self.pending_profiles = None
            self._persist_settings()
            self._close_setup()
            self.paused = False
        return False

    # ---------------------------------------------------------------- events

    def _update_layout(self):
        """Recomputes the layout when the window changed. Returns True when it did not change (drawing can go on)."""
        window = self.display.surface()
        if self.display.generation != self.last_generation or window.get_size() != self.last_size:
            self.layout = layout = compute_layout(*window.get_size())
            self.scene.resize(layout.scale, layout.world.size)
            self.hud.relayout(layout)
            self.menu.relayout(layout)
            self.overlay.relayout(layout)
            self.sidebar = window.subsurface(layout.sidebar)
            self.strip_view = window.subsurface(layout.strip) if layout.strip is not None else None
            self.last_generation, self.last_size = self.display.generation, window.get_size()
            return False
        return True

    def _on_escape(self):
        menu, overlay, setup = self.menu, self.overlay, self.setup
        if menu.open_index is not None:
            menu.close()               # First Escape closes the open menu
        elif setup is not None and overlay.help_open:
            overlay.help_open = False
        elif setup is not None:
            if setup["cancel"]:
                self.do("setup_cancel")     # Setup opened from «Nouvelle simulation»: back to the running one
            elif overlay.start is not None and overlay.start.view == "load":
                self.do("start_back")       # Load list: back to the start menu
            elif overlay.start is None and setup.get("from_start"):
                self.do("start_back")       # Settings of a new simulation: back to the start menu
            else:
                self.running = False        # Start menu: Escape quits
        elif overlay.any_modal():
            overlay.close_modals()          # Then the help or the settings panel
        elif self.display.fullscreen:
            self.display.toggle_fullscreen()   # Then leaves fullscreen
        else:
            self.running = False

    def _on_key(self, event):
        if event.key == pygame.K_ESCAPE:
            self._on_escape()
        elif self.overlay.start is not None and not self.overlay.params_open \
                and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.do(self.overlay.start.default_action())   # Start menu: Enter = Continuer (or Nouvelle simulation)
        elif event.key in KEYS:
            self.do(KEYS[event.key])
        elif event.unicode == "?":
            self.do("help")

    def _on_mouse_motion(self, event):
        display = self.display
        self.menu.hover(*display.to_pixels(event.pos))
        self.overlay.hover(*display.to_pixels(event.pos))
        if self.drag_start is not None and event.buttons[0]:
            mx, my = display.to_pixels(event.pos)
            if self.dragging or abs(mx - self.drag_start[0]) + abs(my - self.drag_start[1]) > 6:
                self.dragging = True      # Dragging the world moves the view
                self.cam_follow = False   # Moving the view by hand stops following (V or a new selection: again)
                ratio = display.pixel_ratio()
                self.scene.pan_pixels(event.rel[0] * ratio, event.rel[1] * ratio)

    def _on_mouse_wheel(self, event):
        mx, my = self.display.to_pixels(pygame.mouse.get_pos())
        if self.layout.world.collidepoint(mx, my) and self.menu.open_index is None \
                and not self.overlay.blocks(mx, my):
            self.scene.zoom_by(1.15 ** event.y, (mx - self.layout.world.x, my - self.layout.world.y))

    def _on_mouse_down(self, event):
        mx, my = self.display.to_pixels(event.pos)   # Window points → surface pixels (2x on Retina)
        consumed, action = self.menu.click(mx, my)
        if action is not None and not self.do(action):
            self.menu.close()
        if not consumed:
            consumed, action = self.overlay.click(mx, my)   # Tool bar, legend, large network, modal panels
            if action is not None:
                self.do(action)
        if not consumed and self.layout.world.collidepoint(mx, my):   # Click in the world (not in the panels)
            self.drag_start, self.dragging = (mx, my), False   # Selection happens on release, unless it was a drag

    def _on_mouse_up(self, event):
        if self.drag_start is not None and not self.dragging:
            # A click without drag: select the creature under the pointer
            layout, scene = self.layout, self.scene
            wx, wy = scene.screen_to_world(self.drag_start[0] - layout.world.x, self.drag_start[1] - layout.world.y)
            self.selected = pick_creature(self.world, wx, wy, scene.pick_radius())
            self.auto_best = False   # A creature chosen by hand: no automatic switch (except T, lineage)
            self.trail.clear()
            self.cam_follow = self.selected is not None   # The camera follows the creature just selected
        self.drag_start, self.dragging = None, False

    def _handle_events(self):
        self.step_request = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._on_key(event)
            elif event.type == pygame.MOUSEMOTION:
                self._on_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._on_mouse_wheel(event)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._on_mouse_up(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_mouse_down(event)

    # ---------------------------------------------------------------- simulation step

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

    # ---------------------------------------------------------------- drawing

    def _menu_state(self, speed, chart_state, net_state):
        """Values shown by the labels and check boxes of the menu bar."""
        pending, pending_profiles, scene, hud, overlay = self.pending, self.pending_profiles, self.scene, self.hud, self.overlay
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

    # ---------------------------------------------------------------- main loop

    def _save_on_exit(self):
        """The population is kept for the next launch (LOAD_ON_START). After an extinction there is nothing to keep.
        Quitting from the setup screen at launch keeps the saved one untouched (the preview world is not a run)."""
        if self.setup is not None and not self.setup["cancel"]:
            return
        if self.sim.extinct or not self.world.creatures:
            if os.path.exists(autosave_path()):
                os.remove(autosave_path())
        else:
            save_population(self.sim, autosave_path())

    def run(self, max_frames=None):
        """The event loop. `max_frames`: stop after that many frames (tests)."""
        frames = 0
        while self.running and (max_frames is None or frames < max_frames):
            frames += 1
            self._update_layout()
            self._handle_events()
            if self.display.generation != self.last_generation or self.display.surface().get_size() != self.last_size:
                continue   # The window changed during the events (fullscreen): relayout before drawing

            speed = config.SPEED_STEPS[self.speed_index]
            # Run several simulation ticks per frame, according to the chosen speed
            ticks_to_run = 0 if self.setup is not None else (1 if self.step_request else (0 if self.paused else speed))
            ran = self._run_ticks(ticks_to_run)

            draw_start = time.perf_counter()   # From here to the flip: drawing (measured for the simulation budget)
            self._draw(speed, ran, ticks_to_run)
            self.draw_ms = 0.8 * self.draw_ms + 0.2 * (time.perf_counter() - draw_start) * 1000   # Smoothed
            self.clock.tick(config.FPS)

    def close(self):
        """End of the session: keeps the population for the next launch, closes the window."""
        self._save_on_exit()
        pygame.quit()

"""The application: window, session state, commands and event loop. main.py only starts it.

App owns the state of a session (running simulation, selection, camera, pause, pending settings). Every command, from
the keyboard or from the menus, goes through App.do(action). The rendering modules never change anything: they return
action names, App runs them. The behaviour is split by theme into mixins: settings, session, commands, events, frame."""
import os
import random
from collections import deque

import pygame

import config
from app.commands import CommandsMixin, KEYS  # noqa: F401  (KEYS: re-exported)
from app.events import EventsMixin
from app.frame import FrameMixin
from app.session import SessionMixin
from app.settings import SettingsMixin, PARAMS, next_step, prev_step  # noqa: F401  (re-exported)
from brain.profiles import PROFILES
from evolution.continuous import ContinuousSimulation, latest_snapshot
from rendering.backend.display import Display
from rendering.ui.hud import Hud
from rendering.ui.menu import MenuBar
from rendering.ui.overlay import Overlay
from rendering.world.scene import Scene
from utils.presets import PresetBrowser
from utils.settings import load_settings


class App(SettingsMixin, SessionMixin, CommandsMixin, EventsMixin, FrameMixin):
    def __init__(self, cfg=config):
        self.cfg = cfg   # Settings in force (the live config module by default, or a config.Settings copy)
        pygame.init()
        self.rng = random.Random(self.cfg.SEED)

        # The window fits the desktop and can be resized or put in fullscreen (key F). The layout (world, side bar,
        # curves strip) is recomputed for the window size and drawn at its real resolution: no bars, no blur.
        self.display = Display("Evolution Simulator", self.cfg)
        self.layout = None
        self.sidebar = None
        self.strip_view = None
        self.last_surface_version = None
        self.last_size = None
        self.clock = pygame.time.Clock()

        # Rendering: world scene (background, food, creatures) and HUD (panel, curves)
        self.scene = Scene(self.cfg)
        self.hud = Hud(self.cfg)
        self.hud.renderer = self.display.renderer_label()   # «GPU» or «CPU», shown next to the FPS
        self.menu = MenuBar()
        # Tool bar, legend, help, hover tips, settings panel, large network
        self.overlay = Overlay(self.hud, self.scene)
        self.hud.lineage = self.scene.lineage          # Living lineages in the Population panel
        self.presets = PresetBrowser(self.cfg)         # Saved settings (saves/presets/), browsed in the settings panel
        self.overlay.presets = self.presets

        # View and selection
        self.cam_follow = False       # True: the camera stays on the selected creature
        self.drag_start = None        # Mouse position of a left press in the world (select on release, pan if dragged)
        self.dragging = False
        self.follow = False           # True: when the selected creature dies, its youngest living descendant is
                                      # selected
        self.debug_mode = 0           # 0 = off, 1 = selected (else oldest living) creature, 2 = all living creatures
        self.selected = None          # Creature picked with a click
        self.auto_best = False        # True after B: when the selected creature dies, the new best one is selected
        self.trail = deque(maxlen=self.cfg.TRAIL_LENGTH)   # Recent positions of the selected creature, one per tick

        # Run state
        self.paused = False
        self.step_request = False
        self.speed_index = 0
        self.real_speed = 0.0   # Ticks per frame actually run (time budget), smoothed
        self.draw_ms = 10.0     # Drawing time of a frame (smoothed), for the simulation budget
        self.running = True

        # Settings chosen in an earlier session replace the values of config.py (saves/settings.json)
        restored = load_settings({name for name, _, _ in PARAMS.values()} | {"ACTIVE_PROFILES"}, self.cfg)
        self.scene.world_changed()
        if restored:
            print("Réglages du menu repris : " + ", ".join(f"{n} {old} → {new}" for n, (old, new) in restored.items())
                  + " (valeurs de config.py ignorées ; LOAD_SETTINGS = False pour les désactiver)")
        self.pending = {}               # action → value waiting for the next restart (RESTART_PARAMS only)
        self.pending_profiles = None    # Species ticked in the menu (list), applied at the next restart from zero

        # Continuous evolution (evolution/continuous.py): births, deaths, no generations. timeline.csv feeds the curves.
        self.timeline = os.path.join(self.cfg.SAVE_DIR, "timeline.csv")
        self.hud.timeline_path = self.timeline

        # Setup screen: the simulation does not run until it is launched from the settings panel. Behind it, a preview
        # world (nothing written to timeline.csv). setup = None (running) or {"resume": bool, "cancel": bool}.
        self.sim = ContinuousSimulation(self.rng, cfg=self.cfg)
        # At launch: the start menu (Continuer / Charger / Nouvelle simulation), then the setup screen for a new one
        self.setup = {"resume": False, "cancel": False, "from_start": True}
        self.overlay.setup = self.setup
        self.overlay.start = self._start_menu()
        self.hud.reload_stats(sorted({c.profile for c in self.world.creatures}, key=list(PROFILES).index))
        self.last_saved = latest_snapshot(self.cfg)
        self._build_commands()

    def close(self):
        """End of the session: keeps the population for the next launch, closes the window."""
        self._save_on_exit()
        pygame.quit()

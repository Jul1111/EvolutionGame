"""The application: window, session, commands and event loop. main.py only starts it.

App is the assembly point: it builds the parts and hands each one what it needs, nothing more.
  state.py     RunState (loop, pause, speed, setup screen) and Selection (picked creature, camera): shared values
  settings.py  MenuSettings: the settings the menu edits, pending ones, species, presets
  session.py   Session: the simulation, new / resume / save / load, start menu and setup screen
  commands.py  Commands: every command, from the keyboard or from the menus, goes through Commands.do(action)
  screen.py    Screen: the layout of the window
  events.py    Events: keyboard and mouse
  frame.py     Frame: ticks within the time budget, drawing, main loop
The rendering modules never change anything: they return action names, Commands runs them."""
import random

import pygame

import config
from app.commands import Commands, KEYS  # noqa: F401  (KEYS: re-exported)
from app.events import Events
from app.frame import Frame
from app.screen import Screen
from app.session import Session
from app.settings import MenuSettings, PARAMS, next_step, prev_step  # noqa: F401  (re-exported)
from app.state import RunState, Selection
from rendering.backend.display import Display
from rendering.ui.hud import Hud
from rendering.ui.menu import MenuBar
from rendering.ui.overlay import Overlay
from rendering.world.scene import Scene
from utils.presets import PresetBrowser
from utils.settings import load_settings


class App:
    def __init__(self, cfg=config):
        self.cfg = cfg   # Settings in force (the live config module by default, or a config.Settings copy)
        pygame.init()
        rng = random.Random(cfg.SEED)

        # The window fits the desktop and can be resized or put in fullscreen (key F). The layout (world, side bar,
        # curves strip) is recomputed for the window size and drawn at its real resolution: no bars, no blur.
        self.display = Display("Evolution Simulator", cfg)

        # Rendering: world scene (background, food, creatures), HUD (panel, curves), menu bar, and the overlay (tool
        # bar, legend, help, hover tips, settings panel, large network)
        self.scene = Scene(cfg)
        self.hud = Hud(cfg)
        self.hud.renderer = self.display.renderer_label()   # «GPU» or «CPU», shown next to the FPS
        self.menu = MenuBar()
        self.overlay = Overlay(self.hud, self.scene)
        self.hud.lineage = self.scene.lineage          # Living lineages in the Population panel
        presets = PresetBrowser(cfg)                   # Saved settings (saves/presets/), browsed in the settings panel
        self.overlay.presets = presets
        self.screen = Screen(self.display, self.scene, self.hud, self.menu, self.overlay)

        # Settings chosen in an earlier session replace the values of config.py (saves/settings.json)
        restored = load_settings({name for name, _, _ in PARAMS.values()} | {"ACTIVE_PROFILES"}, cfg)
        self.scene.world_changed()
        if restored:
            print("Réglages du menu repris : " + ", ".join(f"{n} {old} → {new}" for n, (old, new) in restored.items())
                  + " (valeurs de config.py ignorées ; LOAD_SETTINGS = False pour les désactiver)")

        # The parts, from the least to the most dependent
        self.state = RunState()
        self.selection = Selection(cfg)
        self.settings = MenuSettings(cfg, self.state, presets, self.overlay.toast)
        self.session = Session(cfg, rng, self.scene, self.hud, self.overlay, self.settings, self.state, self.selection)
        self.settings.on_live_change = self.session.refresh_food
        self.commands = Commands(cfg, self.display, self.scene, self.hud, self.overlay, self.state, self.selection,
                                 self.session, self.settings)
        self.events = Events(self.display, self.screen, self.menu, self.overlay, self.scene, self.state,
                             self.selection, self.session, self.commands)
        self.frame = Frame(cfg, self.display, self.screen, self.scene, self.hud, self.menu, self.overlay, self.state,
                           self.selection, self.session, self.settings, self.events)
        self.session.open_launch_screens()

    @property
    def sim(self):
        return self.session.sim

    @property
    def world(self):
        return self.session.world

    def do(self, action):
        """Runs a command (see Commands.do). Returns True to keep the menu open."""
        return self.commands.do(action)

    def run(self, max_frames=None):
        """The event loop. `max_frames`: stop after that many frames (tests)."""
        self.frame.run(max_frames)

    def close(self):
        """End of the session: keeps the population for the next launch, closes the window."""
        self.session.save_on_exit()
        pygame.quit()

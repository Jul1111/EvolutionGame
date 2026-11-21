"""The state of a session, declared once. Every mixin of App inherits it, so a reader of any app/ module sees what
`self` holds. The values are set in App.__init__ (and by the session and command handlers); nothing is assigned here."""
from collections import deque
from random import Random

import pygame

from evolution.continuous import ContinuousSimulation
from rendering.backend.display import Display
from rendering.ui.hud import Hud
from rendering.ui.layout import Layout
from rendering.ui.menu import MenuBar
from rendering.ui.overlay import Overlay
from rendering.world.scene import Scene
from utils.presets import PresetBrowser


class AppState:
    cfg: object                    # Settings in force: the live config module, or a config.Settings copy

    # Window and drawing
    display: Display               # The window (processor or graphics card)
    clock: pygame.time.Clock
    layout: Layout                 # Where the world, the side bar and the curves strip are (see rendering/ui/layout.py)
    sidebar: pygame.Surface        # The parts of the window the HUD draws on (sub-surfaces, rebuilt with the layout)
    strip_view: pygame.Surface
    last_surface_version: int      # Display.surface_version and window size at the last layout: a change = relayout
    last_size: tuple
    scene: Scene                   # The world: background, food, creatures, camera
    hud: Hud                       # Side bar and curves
    menu: MenuBar
    overlay: Overlay               # Tool bar, legend, help, hover tips, settings panel, large network
    presets: PresetBrowser         # Saved settings (saves/presets/)

    # Simulation
    rng: Random
    sim: ContinuousSimulation      # The running simulation (or the preview world behind the setup screen)
    timeline: str                  # Path of timeline.csv, which feeds the curves

    # Selection and camera
    selected: object               # Creature picked with a click, or None
    trail: deque                   # Recent positions of the selected creature, one per tick
    cam_follow: bool               # The camera stays on the selected creature
    follow: bool                   # At its death, the selection moves to its youngest living descendant (key T)
    auto_best: bool                # At its death, the selection moves to the new best creature (key B)
    debug_mode: int                # 0 = off, 1 = selected (else oldest living) creature, 2 = all living creatures
    drag_start: tuple              # Mouse position of a left press in the world, or None
    dragging: bool                 # The press became a drag: the view moves, nothing is selected

    # Run state
    running: bool                  # False ends the main loop
    paused: bool
    step_request: bool             # One tick asked while paused
    speed_index: int               # Index in config.SPEED_STEPS
    real_speed: float              # Ticks per frame actually run (time budget), smoothed
    draw_ms: float                 # Drawing time of a frame, smoothed, for the simulation budget
    setup: dict                    # Setup screen: {"resume": bool, "cancel": bool, ...}, or None while running

    # Settings
    pending: dict                  # Setting action → value waiting for the next restart (RESTART_PARAMS only)
    pending_profiles: list         # Species ticked in the menu, applied at the next restart from zero, or None
    last_saved: str                # Path of the last saved population, or None

    # Commands (see app/commands.py)
    _commands: dict                # Action name → handler
    _prefixed: dict                # Action prefix → handler taking the rest of the name

    @property
    def world(self):
        return self.sim.world

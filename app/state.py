"""The two small bundles of state that several parts of the app share: how the run goes, and what is selected.
They hold values and a few one-line helpers, no behaviour of their own: the parts that use them receive them in their
constructor, so what each one reads and writes is visible in its signature."""
from collections import deque

from evolution.continuous import success_key


class RunState:
    """How the run goes: loop, pause, speed, setup screen."""

    def __init__(self):
        self.running = True            # False ends the main loop
        self.paused = False
        self.step_request = False      # One tick asked while paused
        self.speed_index = 0           # Index in cfg.SPEED_STEPS
        self.real_speed = 0.0          # Ticks per frame actually run (time budget), smoothed
        self.draw_ms = 10.0            # Drawing time of a frame, smoothed, for the simulation budget
        self.setup = None              # Setup screen: {"resume": bool, "cancel": bool, ...}, None while running


class Selection:
    """The creature picked by the player, and how the view follows it."""

    def __init__(self, cfg):
        self.selected = None           # Creature picked with a click, or None
        self.trail = deque(maxlen=cfg.TRAIL_LENGTH)   # Recent positions of the selected creature, one per tick
        self.cam_follow = False        # The camera stays on the selected creature
        self.follow = False            # At its death, the selection moves to its youngest living descendant (key T)
        self.auto_best = False         # At its death, the selection moves to the new best creature (key B)
        self.debug_mode = 0            # 0 = off, 1 = selected (else oldest living) creature, 2 = all living creatures
        self.drag_start = None         # Mouse position of a left press in the world, or None
        self.dragging = False          # The press became a drag: the view moves, nothing is selected

    def clear(self):
        self.selected = None
        self.trail.clear()

    def pick(self, creature):
        """A creature chosen by hand (or None): no automatic switch (except T, lineage), the camera follows it."""
        self.selected = creature
        self.auto_best = False
        self.trail.clear()
        self.cam_follow = creature is not None

    def select_best(self, world):
        self.selected = max(world.creatures, key=success_key)
        self.trail.clear()
        self.cam_follow = True

    def best(self, world):
        if world.creatures:
            self.select_best(world)
            self.auto_best = True   # Stays on «the best»: at its death, the new best one

    def toggle_follow(self, world):
        self.follow = not self.follow
        if self.follow and self.selected is None and world.creatures:
            self.select_best(world)

    def after_tick(self, sim, overlay):
        """After a tick: records the trail, and when the selected creature died, moves to its heir (T) or to the new
        best one (B)."""
        selected = self.selected
        if selected is None:
            return
        world = sim.world
        if selected.alive:
            self.trail.append((selected.x, selected.y))
        elif self.follow or self.auto_best:
            # T: the lineage goes on through its youngest living descendant; if the lineage is extinct,
            # or after B: the new best one (most children)
            heir = sim.descendant_of(selected) if self.follow else None
            if heir is None and world.creatures:
                heir = max((c for c in world.creatures if c.alive), key=success_key, default=None)
                if heir is not None:
                    overlay.toast(f"Morte. Nouvelle meilleure : {heir.children} petits, "
                                  f"génération {heir.lineage_gen}", 2.5)
            if heir is not None:
                self.selected = heir
                self.trail.clear()

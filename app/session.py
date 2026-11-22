"""Life of a session: new simulation, resume, save and load of populations, start menu and setup screen."""
import os
import time

from brain.profiles import PROFILES
from evolution.continuous import (ContinuousSimulation, save_population, load_population, snapshot_path,
                                  autosave_path, populations_dir, latest_snapshot)
from rendering.ui.startmenu import StartMenu
from utils.timefmt import format_time


class Session:
    """The life of a session: the simulation, new / resume / save / load, start menu and setup screen."""

    def __init__(self, cfg, rng, scene, hud, overlay, settings, state, selection):
        self.cfg, self.rng = cfg, rng
        self.scene, self.hud, self.overlay = scene, hud, overlay
        self.settings, self.state, self.selection = settings, state, selection
        self.timeline = os.path.join(cfg.SAVE_DIR, "timeline.csv")   # Feeds the curves
        hud.timeline_path = self.timeline
        # Behind the setup screen, a preview world (nothing written to timeline.csv)
        self.sim = ContinuousSimulation(rng, cfg=cfg)
        self.last_saved = None   # Path of the last saved population, or None

    @property
    def world(self):
        return self.sim.world

    def open_launch_screens(self):
        """At launch: the start menu (Continuer / Charger / Nouvelle simulation), then the setup screen for a new one.
        The simulation does not run until it is launched from the settings panel."""
        self.state.setup = {"resume": False, "cancel": False, "from_start": True}
        self.overlay.params.setup = self.state.setup
        self.overlay.start = self._start_menu()
        self.hud.reload_stats(sorted({c.profile for c in self.world.creatures}, key=list(PROFILES).index))
        self.last_saved = latest_snapshot(self.cfg)

    def refresh_food(self):
        """Food and poison counts or energies changed: sources resized, level kept."""
        self.sim.update_food(0)
        self.world.resize_items(self.sim.food_per_screen())

    def _new_sim(self, founders=None, start_tick=0, append=False):
        return ContinuousSimulation(self.rng, self.timeline, founders=founders, start_tick=start_tick, append=append,
                                    cfg=self.cfg)

    def _start_menu(self):
        """The start menu at launch: Continuer (if there is an autosave and LOAD_ON_START), Charger, Nouvelle."""
        autosave = autosave_path(self.cfg) if self.cfg.LOAD_ON_START else None
        return StartMenu(autosave, populations_dir(self.cfg))

    def _archive_timeline(self):
        """A new population starts a new timeline: the old one is set aside (timestamped), not deleted."""
        if os.path.exists(self.timeline):
            os.replace(self.timeline, self.timeline[:-4] + time.strftime("_ancien_%Y%m%d_%H%M%S.csv"))

    def _begin(self, sim, reload_species):
        """Common end of restart / resume: the new simulation replaces the old one, selection and trail are cleared."""
        self.sim = sim
        self.selection.clear()
        self.state.paused = False
        self.hud.reload_stats(reload_species)

    def restart(self, founders=None):
        """New population: random founders of the ticked species, or a saved population (founders)."""
        old_scale = self.cfg.WORLD_SCALE
        self.settings.apply_pending()
        if self.cfg.WORLD_SCALE != old_scale:
            self.scene.world_changed()
        self._archive_timeline()
        self._begin(self._new_sim(founders), list(founders) if founders else self.cfg.ACTIVE_PROFILES)

    def _resume_autosave(self):
        """Start from the population kept when the game was last closed, with its timeline."""
        founders, tick = load_population(autosave_path(self.cfg), with_tick=True)
        if not founders:
            return False
        self.settings.apply_pending()
        self.scene.world_changed()
        self._begin(self._new_sim(founders, start_tick=tick, append=True), list(founders))
        self.overlay.toast(f"Population reprise : {len(self.world.creatures)} créatures, temps {format_time(tick)}")
        return True

    def open_setup(self, can_cancel):
        """Settings screen before a new simulation: everything set there applies when it is launched."""
        self.state.setup = {"resume": False, "cancel": can_cancel}
        self.overlay.params.setup = self.state.setup
        self.overlay.params.open = True
        self.state.paused = True

    def _close_setup(self):
        self.state.setup = None
        self.overlay.params.setup = None
        self.overlay.params.open = False

    def restart_random(self):
        self.restart()
        self.overlay.toast("Nouvelle population tirée au hasard")

    def save_population(self):
        if self.world.creatures:
            self.last_saved = snapshot_path("manuelle", self.cfg)
            save_population(self.sim, self.last_saved)
            self.overlay.toast(f"Population sauvegardée : saves/populations/{os.path.basename(self.last_saved)}")

    def load_last_population(self):
        if self.last_saved and os.path.exists(self.last_saved):
            founders = load_population(self.last_saved)
            if founders:
                self.restart(founders)
                self.overlay.toast(f"Population chargée : {os.path.basename(self.last_saved)}")
        else:
            self.overlay.toast("Aucune population sauvegardée (S pour sauvegarder)")

    def start_continue(self):
        if self._resume_autosave():
            self.overlay.start = None
            self._close_setup()

    def open_load_list(self):
        self.overlay.start.view = "load"

    def start_back(self):
        overlay = self.overlay
        overlay.params.open = False   # Back from the settings of a new simulation, or from the load list
        if overlay.start is None:
            overlay.start = self._start_menu()
        overlay.start.view = "main"

    def start_new(self):
        self.overlay.start = None
        self.overlay.params.open = True

    def start_load(self, path):
        if not os.path.exists(path):   # Deleted since the list was made
            self.overlay.toast(f"Fichier introuvable : {os.path.basename(path)}")
            return
        founders = load_population(path)
        if founders:
            self.restart(founders)
            self.last_saved = path
            self.overlay.start = None
            self._close_setup()
            self.state.paused = False
            self.overlay.toast(f"Population chargée : {os.path.basename(path)}")

    def setup_launch(self):
        self.restart()
        self._close_setup()

    def setup_resume(self):
        if self._resume_autosave():
            self._close_setup()

    def setup_cancel(self):
        self.settings.discard_pending()
        self._close_setup()
        self.state.paused = False

    def save_on_exit(self):
        """The population is kept for the next launch (LOAD_ON_START). After an extinction there is nothing to keep.
        Quitting from the setup screen at launch keeps the saved one untouched (the preview world is not a run)."""
        if self.state.setup is not None and not self.state.setup["cancel"]:
            return
        if self.sim.extinct or not self.world.creatures:
            if os.path.exists(autosave_path(self.cfg)):
                os.remove(autosave_path(self.cfg))
        else:
            save_population(self.sim, autosave_path(self.cfg))

"""Life of a session: new simulation, resume, save and load of populations, start menu and setup screen."""
import os
import time


import config
from evolution.continuous import (ContinuousSimulation, save_population, load_population, snapshot_path,
                                  autosave_path, populations_dir)
from rendering.ui.startmenu import StartMenu
from utils.timefmt import format_time


class SessionMixin:
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

    def _restart_random(self):
        self.restart()
        self.overlay.toast("Nouvelle population tirée au hasard")

    def _save_population(self):
        if self.world.creatures:
            self.last_saved = snapshot_path("manuelle")
            save_population(self.sim, self.last_saved)
            self.overlay.toast(f"Population sauvegardée : saves/populations/{os.path.basename(self.last_saved)}")

    def _load_last_population(self):
        if self.last_saved and os.path.exists(self.last_saved):
            founders = load_population(self.last_saved)
            if founders:
                self.restart(founders)
                self.overlay.toast(f"Population chargée : {os.path.basename(self.last_saved)}")
        else:
            self.overlay.toast("Aucune population sauvegardée (S pour sauvegarder)")

    def _start_continue(self):
        if self._resume_autosave():
            self.overlay.start = None
            self._close_setup()

    def _open_load_list(self):
        self.overlay.start.view = "load"

    def _start_back(self):
        overlay = self.overlay
        overlay.params_open = False   # Back from the settings of a new simulation, or from the load list
        if overlay.start is None:
            overlay.start = StartMenu(autosave_path() if config.LOAD_ON_START else None, populations_dir())
        overlay.start.view = "main"

    def _start_new(self):
        self.overlay.start = None
        self.overlay.params_open = True

    def _start_load(self, path):
        if not os.path.exists(path):   # Deleted since the list was made
            self.overlay.toast(f"Fichier introuvable : {os.path.basename(path)}")
            return
        founders = load_population(path)
        if founders:
            self.restart(founders)
            self.last_saved = path
            self.overlay.start = None
            self._close_setup()
            self.paused = False
            self.overlay.toast(f"Population chargée : {os.path.basename(path)}")

    def _setup_launch(self):
        self.restart()
        self._close_setup()

    def _setup_resume(self):
        if self._resume_autosave():
            self._close_setup()

    def _setup_cancel(self):
        self.pending.clear()
        self.pending_profiles = None
        self._persist_settings()
        self._close_setup()
        self.paused = False

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

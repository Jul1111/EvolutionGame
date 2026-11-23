"""Settings editable from the menu: which ones, how they cycle, when they apply, and their persistence."""
from brain.profiles import PROFILES
from utils.settings import save_settings
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
    "food_types": ("FOOD_TYPES", [1, 2], lambda v: "une" if v == 1 else "deux (régimes)"),
    "world_scale": ("WORLD_SCALE", [1, 2, 3], lambda v: f"{v}×{v} écrans"),
}
# Settings that only take effect on a new world (obstacles are drawn when the world is created).
# Every other setting applies at once.
# size_mode: bodies are set at birth; food_types: the kind of each food and the diets are set at creation
RESTART_PARAMS = {"obstacle_count", "world_scale", "size_mode", "founders", "food_types"}


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


class MenuSettings:
    """The settings as the menu edits them: pending ones (waiting for a restart), species ticked, presets."""

    def __init__(self, cfg, state, presets, toast):
        self.cfg = cfg
        self.state = state          # RunState: while the setup screen is open every setting waits for the launch
        self.presets = presets      # PresetBrowser
        self.toast = toast          # Shows a message to the player
        self.on_live_change = None  # Called after a setting that applies now (the session resizes food and poison)
        self.pending = {}           # Setting action → value waiting for the next restart (RESTART_PARAMS only)
        self.pending_profiles = None   # Species ticked in the menu (list), applied at the next restart from zero

    def apply_param(self, key, value):
        """Setting changed in the menu: now, or at the next restart for RESTART_PARAMS (or for every setting while
        the setup screen is open: nothing runs yet)."""
        name = PARAMS[key][0]
        if key in RESTART_PARAMS or self.state.setup is not None:
            if value == getattr(self.cfg, name):
                self.pending.pop(key, None)
            else:
                self.pending[key] = value
        else:
            setattr(self.cfg, name, value)
            if self.on_live_change:
                self.on_live_change()   # Food and poison counts or energies take effect now
        self.persist()

    def values(self):
        """The settings as they will be after the next restart (pending ones included)."""
        values = {name: self.pending.get(action, getattr(self.cfg, name)) for action, (name, _, _) in PARAMS.items()}
        values["ACTIVE_PROFILES"] = list(self.profiles_shown())
        return values

    def profiles_shown(self):
        return self.cfg.ACTIVE_PROFILES if self.pending_profiles is None else self.pending_profiles

    def persist(self):
        """Keeps the settings chosen in the menu (pending ones included) for the next launch."""
        save_settings(self.values(), self.cfg)

    def apply_pending(self):
        for action, value in self.pending.items():
            setattr(self.cfg, PARAMS[action][0], value)
        self.pending.clear()
        if self.pending_profiles is not None:
            self.cfg.ACTIVE_PROFILES = list(self.pending_profiles)
            self.pending_profiles = None

    def discard_pending(self):
        """Cancels what waits for the next restart (species included)."""
        self.pending.clear()
        self.pending_profiles = None
        self.persist()

    def toggle_profile(self, name):
        """Tick or untick a species. At least one must stay. Back to the active list = nothing pending."""
        current = list(self.profiles_shown())
        if name in current:
            if len(current) > 1:
                current.remove(name)
        else:
            current.append(name)
        current = [p for p in PROFILES if p in current]
        self.pending_profiles = None if current == self.cfg.ACTIVE_PROFILES else current
        self.persist()

    def apply_preset(self):
        values = self.presets.load()
        if not values:
            return
        for action, (name, _, _) in PARAMS.items():
            if name in values:
                self.apply_param(action, values[name])
        if values.get("ACTIVE_PROFILES"):
            wanted = [p for p in PROFILES if p in values["ACTIVE_PROFILES"]]
            self.pending_profiles = None if wanted == self.cfg.ACTIVE_PROFILES else wanted
            self.persist()
        self.toast("Préréglage appliqué")

    def params_cancel(self):
        self.pending.clear()
        self.persist()

    def move_preset(self, step):
        self.presets.refresh()
        self.presets.move(step)

    def save_preset(self):
        self.toast(f"Préréglage enregistré : saves/presets/{self.presets.save(self.values())}")

    def cycle_param(self, key):
        """Menu click: next preset value (now, or at the next restart)."""
        name, steps, _ = PARAMS[key]
        self.apply_param(key, next_step(steps, self.pending.get(key, getattr(self.cfg, name))))

    def step_param(self, arg):
        """Arrows of the settings panel ("dec:<key>" / "inc:<key>"): previous / next preset. Back to the value in force
        = nothing pending."""
        direction, key = arg.split(":")
        name, steps, _ = PARAMS[key]
        current = self.pending.get(key, getattr(self.cfg, name))
        self.apply_param(key, prev_step(steps, current) if direction == "dec" else next_step(steps, current))

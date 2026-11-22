"""Configuration: the single reference for every setting.

- The game may override some values from its menu: they are kept in saves/settings.json, which only holds the
  values that differ from this file, and they are listed in the terminal at launch.
- Headless experiments (experiments/run.py) never read settings.json: they use this file plus their --set options.
- Headless runs write every constant in their run.json.

World values (08/11/2026): back to the last world where evolution worked (one screen, 10 foods), keeping the poison,
the cone of vision and the obstacles. The hardened world (×2, 5 foods, 20 poisons at 80, 25 obstacles per screen)
ended every generation at ~2500 ticks with parents nearly still: see the README, section «Expériences».
"""
import os
import sys

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

#Configuration for creatures
CREATURE_RADIUS = 8

# Configuration for world
WORLD_SCALE = 1             # Side of the world in screens (a screen = SCREEN_WIDTH x SCREEN_HEIGHT). 2 = 4 times the
                            # area, food, obstacles and computing cap included (not the founders); about 4 times slower
                            # once the population has grown. The view opens at the scale of one screen.
                            # Menu Paramètres, next restart
# FOOD_COUNT, POISON_COUNT and OBSTACLE_COUNT are given per screen-sized area: the world holds WORLD_SCALE² times more

# Configuration for food
SEED = 42
FOOD_COUNT = 60             # Food sources per screen when the population is small (and at the start: random
                            # founders need plenty to get through the first bottleneck: 4 extinctions out of 8 seeds at
                            # 40, 0 out of 8 at 60, docs/experiences.md, 22/11)
FOOD_COUNT_MIN = 15         # Food sources per screen when the population is large: food follows the population, no
                            # calendar (evolution/continuous.py). Same value as FOOD_COUNT = food never changes
FOOD_PRESSURE_POP = 300     # Living creatures born in this world, per screen (the whole world: FOOD_PRESSURE), at
                            # which the food is down to FOOD_COUNT_MIN; in between, straight line from FOOD_COUNT
                            # (0 creature) to FOOD_COUNT_MIN. Per screen since 22/11, like the food it regulates
FOOD_ADAPT_TICKS = 3000     # The food moves toward that level over about this time (50 s), not at once: no yo-yo
FOOD_RADIUS = 4

# Configuration for energy
FOOD_ENERGY = 30.0
INITIAL_ENERGY = 100.0
ENERGY_MAX = 200.0          # Satiety: a creature only eats if the whole meal fits (energy + food <= max).
                            # Starting value, to tune


# Configuration for simulation speed
SPEED_STEPS = [1, 2, 5, 10, 20, 50, 100]
RENDERER = "auto"          # "auto": the graphics card draws (rendering/backend/gpu.py) if SDL finds a hardware
                           # renderer (Metal, OpenGL, Direct3D), else the processor. "gpu": graphics card even
                           # without hardware (software renderer, slower). "cpu": the processor. Also the
                           # EVOLUTION_RENDERER environment variable
MIN_FPS = 30               # At high speed the simulation only takes what drawing leaves of a frame at this rate
SIM_MIN_BUDGET_MS = 4      # ...but always at least this much per frame, however slow the drawing

# Configuration for senses
VISION_RANGE = 200          # Maximum distance at which a creature sees food
VISION_FOV_DEGREES = 120    # Field of view, centred on the heading. 360 = sees all around (the former behaviour).
                            # Starting value, to tune

# Configuration for variable speed
CREATURE_MAX_SPEED = 4.0
ENERGY_BASE_COST = 0.04     # Energy lost per tick, even when standing still
ENERGY_MOVE_COST = 0.03     # Extra energy lost per tick, per unit of speed
                            # (at speed 2: 0.04 + 0.03 x 2 = 0.10)

# Configuration for the neural network
# The network itself (sensors, outputs, hidden layer, memory) is set by each profile: see brain/profiles.py
# Profiles (species) of the founders: INITIAL_POPULATION split between them (menu Réseau, applied at the next restart)
ACTIVE_PROFILES = ["complet"]
NN_INIT_STD = 0.5           # Std of the initial random weights
CREATURE_MAX_TURN = 0.25    # Max rotation per tick (radians) at rest, when the turn output is +/-1
                            # (starting value, to tune)
TURN_SPEED_PENALTY = 0.5    # The faster the creature, the wider its turns: max turn x (1 - penalty x speed / max
                            # speed). Starting value, to tune
CREATURE_ACCELERATION = 0.25  # Max change of speed per tick, accelerating or braking (starting value, to tune)

# Configuration for continuous evolution (evolution/continuous.py): no generations, creatures are born and die.
# Starting values, to tune (see the project doc conception-evolution-continue.md)
INITIAL_POPULATION = 200    # Random creatures at the start, whatever the world size (split between ACTIVE_PROFILES)
REPRO_THRESHOLD = 120.0     # Energy needed to give birth (150: random founders rarely reach it, extinction)
REPRO_COST = 60.0           # Energy the parent loses at a birth
REPRO_CHILD_ENERGY = 50.0   # Energy of the newborn (less than the cost: no perpetual motion)
MATURITY_AGE = 600          # Ticks before a creature can give birth (10 s)
REPRO_COOLDOWN = 300        # Ticks between two births of the same creature
AGE_MAX = 6000              # Death of old age (100 s). 0 = never
POP_MAX = 400               # Computing cap per screen: the whole world holds WORLD_SCALE² times more (POP_CAP). At
                            # the cap births are blocked and counted (cap_blocked). Per screen since 22/11: a 2×2 world
                            # with a fixed cap of 400 was held by the cap, not by the food (docs/experiences.md)
SAMPLE_TICKS = 600          # One line of timeline.csv every SAMPLE_TICKS ticks

# Configuration for the body gene: size (core/creature.py). Founders have size 1; a newborn gets the size of its
# parent × exp(N(0, SIZE_MUTATION_STD)), kept in [SIZE_MIN, SIZE_MAX].
# SIZE_MODE: "fixe" = everyone 1, no mutation. "neutre" = the size mutates but changes nothing (drift control).
# "actif" = trade-offs: contact radius, energy reserve and the energy of a birth ∝ size; base cost ∝
# size^SIZE_BASE_EXPONENT (Kleiber's law: a big body is cheaper to keep per unit of size); cost of moving ∝ size.
# Starting values, to tune
SIZE_MODE = "actif"
SIZE_MUTATION_STD = 0.05
SIZE_MIN = 0.5
SIZE_MAX = 2.0
SIZE_BASE_EXPONENT = 0.75

# Configuration for mutation
MUTATION_STD = 0.1          # Std of the gaussian noise added to each weight of a child (0.2 was chosen on one seed
                            # only)

# Configuration for saving and logging
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
LOAD_ON_START = True        # The game resumes the population it had when it was closed (saves/autosave.npz)
LOAD_SETTINGS = True        # Reuse the settings changed from the menu (saves/settings.json). False = values of this
                            # file

# Configuration for the interface (colours are in rendering/theme.py)
TRAIL_LENGTH = 600                   # Ticks of trajectory kept for the selected creature

# Configuration for food respawn
FOOD_RESPAWN_DELAY = 60     # Ticks before an eaten food is available again, always at a new random place
HUNGER_SCALE = 600          # Sensor «faim»: ticks without seeing food for the input to reach 1 (10 s)
SPAWN_CLEARANCE = 20        # Food and poison never reappear closer than this to the edge of a creature (never on one)
POISON_COUNT = 5            # Poison sources in the world (0 = no poison). The network sees the nearest one
POISON_ENERGY = 40.0        # Energy lost by the creature that touches a poison (starting value, to tune)

# Configuration for obstacles
OBSTACLE_COUNT = 6          # Solid obstacles, drawn at random at the creation of each world (0 = none)
OBSTACLE_SHAPES = ("circle", "square", "triangle")   # Shapes drawn at random (one entry = only that shape)
OBSTACLE_RADIUS_MIN = 20    # Radius range of the circle around the shape (world units)
OBSTACLE_RADIUS_MAX = 45
OBSTACLE_MIN_GAP = 30       # Minimum free space between two obstacles (a creature is 16 wide: it can always pass)


# Values derived from others (WORLD_WIDTH from WORLD_SCALE…). They are computed when read, so they can never be out of
# date after a setting changed: nothing to refresh. They are not module attributes, so they cannot be set or saved.
DERIVED = {
    "WORLD_WIDTH": lambda c: round(c.SCREEN_WIDTH * c.WORLD_SCALE),
    "WORLD_HEIGHT": lambda c: round(c.SCREEN_HEIGHT * c.WORLD_SCALE),
    "ENERGY_INPUT_MAX": lambda c: c.ENERGY_MAX,   # Energy at which the network input saturates at 1.0 (= satiety)
    "POP_CAP": lambda c: c.POP_MAX * c.WORLD_SCALE ** 2,   # Computing cap of the whole world
    "FOOD_PRESSURE": lambda c: c.FOOD_PRESSURE_POP * c.WORLD_SCALE ** 2,   # Born creatures of the whole world at which
                                                                           # the food is at its minimum
}


def __getattr__(name):
    if name in DERIVED:
        return DERIVED[name](sys.modules[__name__])
    raise AttributeError(f"module 'config' has no attribute {name!r}")


class Settings:
    """A copy of the settings, with optional overrides: `Settings(FOOD_COUNT=3, WORLD_SCALE=2)`.

    World and ContinuousSimulation take it as `cfg` (default: this module, the live settings): two simulations with
    different settings can live in the same process, and a simulation is not affected by later changes of the module.
    Anything with the same attribute names works as `cfg`."""

    def __init__(self, **overrides):
        module = sys.modules[__name__]
        for name in dir(module):
            if name.isupper() and name != "DERIVED":
                setattr(self, name, getattr(module, name))
        for name, value in overrides.items():
            if name not in self.__dict__:
                raise AttributeError(f"Unknown setting: {name}")
            setattr(self, name, value)

    def __getattr__(self, name):   # Only reached for names that are not attributes: the derived values
        if name in DERIVED:
            return DERIVED[name](self)
        raise AttributeError(name)

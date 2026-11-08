#Configuration file for the game
import os

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
BACKGROUND_COLOR = (18, 20, 26)

#Configuration for creatures
CREATURE_RADIUS = 8
CREATURE_COLOR = (240, 200, 80)
DEAD_COLOR = (90, 90, 90)

# Configuration for world
WORLD_SCALE = 2             # Side of the world in screens (a screen = SCREEN_WIDTH x SCREEN_HEIGHT): 1 = as big as the window area
WORLD_WIDTH = round(SCREEN_WIDTH * WORLD_SCALE)
WORLD_HEIGHT = round(SCREEN_HEIGHT * WORLD_SCALE)
# FOOD_COUNT, POISON_COUNT and OBSTACLE_COUNT are given per screen-sized area: the world holds WORLD_SCALE² times more

# Configuration for food
SEED = 42
FOOD_COUNT = 5
FOOD_RADIUS = 4
FOOD_COLOR = (90, 200, 110)

# Configuration for energy
FOOD_ENERGY = 30.0
INITIAL_ENERGY = 100.0
ENERGY_MAX = 200.0          # Satiety: a creature only eats if the whole meal fits (energy + food <= max). Starting value, to tune

# Configuration for population
POPULATION_SIZE = 100       # Creatures in the whole world, split evenly between the active profiles

# Configuration for evolution
GEN_MAX_TICKS = 36000  # Safety cap: 10 simulated minutes (600 s x TICKS_PER_SECOND)
PARENTS_COUNT = 20          # Parents kept in the whole world: each species keeps its share (same ratio as its population)


def species_size(index, n_species):
    """Creatures of the species number `index` (0-based) when `n_species` share POPULATION_SIZE; the remainder goes to the first ones."""
    base, rest = divmod(POPULATION_SIZE, max(1, n_species))
    return base + (1 if index < rest else 0)


def parents_for(size):
    """Parents kept by a species of `size` creatures: PARENTS_COUNT / POPULATION_SIZE of it (at least 1, fewer than size)."""
    return max(1, min(size - 1, round(size * PARENTS_COUNT / POPULATION_SIZE))) if size > 1 else size

# Configuration for time display
TICKS_PER_SECOND = 60

# Configuration for simulation speed
SPEED_STEPS = [1, 2, 5, 10, 20, 50, 100]

# Configuration for senses
VISION_RANGE = 200          # Maximum distance at which a creature sees food
VISION_FOV_DEGREES = 120    # Field of view, centred on the heading. 360 = sees all around (the former behaviour). Starting value, to tune
ENERGY_INPUT_MAX = ENERGY_MAX  # Energy at which the network input saturates at 1.0 (= satiety, so the input covers the full range)

# Configuration for variable speed
CREATURE_MAX_SPEED = 4.0
ENERGY_BASE_COST = 0.04     # Energy lost per tick, even when standing still
ENERGY_MOVE_COST = 0.03     # Extra energy lost per tick, per unit of speed
                            # (at speed 2: 0.04 + 0.03 x 2 = 0.10)

# Configuration for the neural network
# The network itself (sensors, outputs, hidden layer, memory) is set by each profile: see brain/profiles.py
# Profiles living in the same world, sharing POPULATION_SIZE creatures (menu Réseau, saved in settings.json)
ACTIVE_PROFILES = ["chasseur", "chasseur_rassasie", "prudent", "vitesse_fixe"]
NN_INIT_STD = 0.5           # Std of the initial random weights
CREATURE_MAX_TURN = 0.25    # Max rotation per tick (radians) at rest, when the turn output is +/-1 (starting value, to tune)
TURN_SPEED_PENALTY = 0.5    # The faster the creature, the wider its turns: max turn x (1 - penalty x speed / max speed). Starting value, to tune
CREATURE_ACCELERATION = 0.25  # Max change of speed per tick, accelerating or braking (starting value, to tune)

# Configuration for mutation
MUTATION_STD = 0.2          # Std of the gaussian noise added to each weight of a child

# Configuration for saving and logging
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
# Each profile saves its population and its CSV in saves/profiles/<name>/ (brain/profiles.py)
LOAD_ON_START = True        # Each profile resumes from its own save (saves/profiles/<name>/latest.npz) if it exists
LOAD_SETTINGS = True        # Reuse the settings changed from the menu (saves/settings.json). False = values of this file

# Configuration for rendering (organic style)
BG_CENTER_COLOR = (30, 40, 46)       # Centre of the "petri dish" background
BG_EDGE_COLOR = (9, 11, 15)          # Darker vignette on the edges
ENERGY_LOW_COLOR = (222, 96, 78)     # Creature colour when energy is near 0
ENERGY_MID_COLOR = (240, 196, 92)
ENERGY_HIGH_COLOR = (120, 224, 176)  # Creature colour when energy is at ENERGY_INPUT_MAX
DEBUG_VISION_COLOR = (70, 120, 130)
DEBUG_LINK_COLOR = (150, 235, 200)
HUD_PANEL_COLOR = (25, 31, 37, 255)
SIDEBAR_BG_COLOR = (15, 18, 22)
PANEL_WIDTH = 320                    # Side bar on the right of the world view
WINDOW_WIDTH = SCREEN_WIDTH + PANEL_WIDTH
TRAIL_LENGTH = 600                   # Ticks of trajectory kept for the selected creature
HUD_LABEL_COLOR = (150, 165, 170)
HUD_VALUE_COLOR = (235, 240, 240)

# Configuration for food respawn
FOOD_RESPAWN_DELAY = 60     # Ticks before an eaten food is available again (starting value, to tune)
FOOD_FIXED_POSITIONS = True  # True: food comes back at the same place; False: at a new random place
POISON_COUNT = 20           # Poison sources in the world (0 = no poison). The network sees the nearest one
POISON_ENERGY = 40.0        # Energy lost by the creature that touches a poison (starting value, to tune)
POISON_COLOR = (176, 96, 214)

# Configuration for obstacles
OBSTACLE_COUNT = 25         # Solid obstacles, drawn at random at the start of each generation (0 = none)
OBSTACLE_SHAPES = ("circle", "square", "triangle")   # Shapes drawn at random (one entry = only that shape)
OBSTACLE_RADIUS_MIN = 20    # Radius range of the circle around the shape (world units)
OBSTACLE_RADIUS_MAX = 45
OBSTACLE_MIN_GAP = 30       # Minimum free space between two obstacles (a creature is 16 wide: it can always pass)
OBSTACLE_COLOR = (92, 102, 112)
FOOD_MAX_EATS = 3           # Times a source can be eaten before it moves elsewhere (starting value, to tune)

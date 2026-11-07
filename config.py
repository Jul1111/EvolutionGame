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
WORLD_WIDTH = SCREEN_WIDTH
WORLD_HEIGHT = SCREEN_HEIGHT

# Configuration for food
SEED = 42
FOOD_COUNT = 10
FOOD_RADIUS = 4
FOOD_COLOR = (90, 200, 110)

# Configuration for energy
FOOD_ENERGY = 30.0
INITIAL_ENERGY = 100.0

# Configuration for population
POPULATION_SIZE = 100

# Configuration for evolution
GEN_MAX_TICKS = 36000  # Safety cap: 10 simulated minutes (600 s x TICKS_PER_SECOND)
PARENTS_COUNT = 20

# Configuration for time display
TICKS_PER_SECOND = 60

# Configuration for simulation speed
SPEED_STEPS = [1, 2, 5, 10, 20, 50, 100]

# Configuration for senses
VISION_RANGE = 200          # Maximum distance at which a creature sees food
ENERGY_INPUT_MAX = 200.0    # Energy at which the network input saturates at 1.0

# Configuration for variable speed
CREATURE_MAX_SPEED = 4.0
ENERGY_BASE_COST = 0.04     # Energy lost per tick, even when standing still
ENERGY_MOVE_COST = 0.03     # Extra energy lost per tick, per unit of speed
                            # (at speed 2: 0.04 + 0.03 x 2 = 0.10)

# Configuration for the neural network
NN_INPUTS = 3               # distance, relative angle, energy
NN_HIDDEN = 6
NN_OUTPUTS = 2              # turn, speed
NN_INIT_STD = 0.5           # Std of the initial random weights
CREATURE_MAX_TURN = 0.15    # Max rotation per tick (radians) when the turn output is +/-1

# Configuration for mutation
MUTATION_STD = 0.1          # Std of the gaussian noise added to each weight of a child

# Configuration for saving and logging
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
GENOMES_FILE = os.path.join(SAVE_DIR, "latest.npz")
STATS_FILE = os.path.join(SAVE_DIR, "stats.csv")
LOAD_ON_START = True        # Resume from saves/latest.npz if it exists

# Configuration for rendering (organic style)
BG_CENTER_COLOR = (30, 40, 46)       # Centre of the "petri dish" background
BG_EDGE_COLOR = (9, 11, 15)          # Darker vignette on the edges
ENERGY_LOW_COLOR = (222, 96, 78)     # Creature colour when energy is near 0
ENERGY_MID_COLOR = (240, 196, 92)
ENERGY_HIGH_COLOR = (120, 224, 176)  # Creature colour when energy is at ENERGY_INPUT_MAX
DEBUG_VISION_COLOR = (70, 120, 130)
DEBUG_LINK_COLOR = (150, 235, 200)
HUD_PANEL_COLOR = (12, 16, 20, 190)
HUD_LABEL_COLOR = (150, 165, 170)
HUD_VALUE_COLOR = (235, 240, 240)

# Configuration for food respawn
FOOD_RESPAWN_DELAY = 60     # Ticks before an eaten food is available again (starting value, to tune)
FOOD_FIXED_POSITIONS = True  # True: food comes back at the same place; False: at a new random place
FOOD_MAX_EATS = 3           # Times a source can be eaten before it moves elsewhere (starting value, to tune)

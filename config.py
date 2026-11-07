#Configuration file for the game
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
FOOD_COUNT = 50
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

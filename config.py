#Configuration file for the game
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
BACKGROUND_COLOR = (18, 20, 26)

#Configuration for creatures
CREATURE_RADIUS = 8
CREATURE_COLOR = (240, 200, 80)
DEAD_COLOR = (90, 90, 90)
CREATURE_SPEED = 2

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
ENERGY_COST_PER_TICK = 0.1

# Configuration for population
POPULATION_SIZE = 100

# Configuration for evolution
GEN_MAX_TICKS = 36000  # Safety cap: 10 simulated minutes (600 s x TICKS_PER_SECOND)
PARENTS_COUNT = 20

# Configuration for time display
TICKS_PER_SECOND = 60

# Configuration for simulation speed
SPEED_STEPS = [1, 2, 5, 10, 20, 50, 100]

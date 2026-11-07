import math

import config
from core.food import Food
from core.physics import torus_delta, normalize_angle
from core.creature import Creature
from brain.network import NeuralNetwork

class World:
    def __init__(self, rng):
        self.rng = rng
        self.width = config.WORLD_WIDTH
        self.height = config.WORLD_HEIGHT
        self.creatures = []
        self.foods = [
            Food(rng.uniform(0, self.width), rng.uniform(0, self.height), config.FOOD_ENERGY)
            for _ in range(config.FOOD_COUNT)
        ]
        self.tick = 0

    def update(self):

        if self.is_over():
            return

        # Phase 1: Update all creatures
        for creature in self.creatures:
            if creature.alive:
                inputs = self.sense(creature)
                creature.update(inputs, self.width, self.height)

        # Phase 2: Check for food consumption
        for food in self.foods:
            best = None
            best_distance2 = (config.CREATURE_RADIUS + config.FOOD_RADIUS) ** 2
            
            for creature in self.creatures:
                if not creature.alive:
                    continue
                dx = torus_delta(creature.x, food.x, self.width)
                dy = torus_delta(creature.y, food.y, self.height)
                distance2 = dx * dx + dy * dy
                if distance2 < best_distance2:
                    best_distance2 = distance2
                    best = creature

            if best is not None:
                best.eat_food(food.energy)
                # Reposition the food to a new random location
                food.x = self.rng.uniform(0, self.width)
                food.y = self.rng.uniform(0, self.height)

        self.tick += 1

    def add_creature(self, brain):
        x = self.rng.uniform(0, self.width)
        y = self.rng.uniform(0, self.height)
        angle = self.rng.uniform(-math.pi, math.pi)
        creature = Creature(x, y, angle, config.INITIAL_ENERGY, brain)
        self.creatures.append(creature)

    def add_population(self,count):
        for _ in range(count):
            brain = NeuralNetwork(config.NN_INPUTS, config.NN_HIDDEN, config.NN_OUTPUTS)
            brain.randomize(self.rng, config.NN_INIT_STD)
            self.add_creature(brain)

    def sense(self, creature):
        """Retourne les entrées du réseau : [distance, angle relatif, énergie], toutes normalisées."""
        # Find the closest food within the vision range
        best_distance2 = config.VISION_RANGE ** 2
        best_dx = None
        best_dy = None
        for food in self.foods:
            dx = torus_delta(creature.x, food.x, self.width)
            dy = torus_delta(creature.y, food.y, self.height)
            distance2 = dx * dx + dy * dy
            if distance2 <= best_distance2:
                best_distance2 = distance2
                best_dx = dx
                best_dy = dy

        energy = max(0.0, min(creature.energy / config.ENERGY_INPUT_MAX, 1.0))

        # Nothing in sight: maximum distance, straight ahead
        if best_dx is None:
            return [1.0, 0.0, energy]

        distance = math.sqrt(best_distance2) / config.VISION_RANGE
        angle = normalize_angle(math.atan2(best_dy, best_dx) - creature.angle) / math.pi
        return [distance, angle, energy]

    def is_over(self):
        alive = sum(1 for c in self.creatures if c.alive)
        # The parents threshold only makes sense if the population is bigger than it
        threshold = config.PARENTS_COUNT if len(self.creatures) > config.PARENTS_COUNT else 0
        return alive <= threshold or self.tick >= config.GEN_MAX_TICKS


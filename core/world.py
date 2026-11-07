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
        # Poison: same kind of object as food, but its `energy` is the damage. Seen through its own two inputs
        self.poisons = [
            Food(rng.uniform(0, self.width), rng.uniform(0, self.height), config.POISON_ENERGY)
            for _ in range(config.POISON_COUNT)
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
            # A food that was eaten recently is not there yet: count down and skip it
            if food.cooldown > 0:
                food.cooldown -= 1
                continue

            best = None
            best_distance2 = (config.CREATURE_RADIUS + config.FOOD_RADIUS) ** 2
            
            for creature in self.creatures:
                if not creature.alive or creature.energy + food.energy > config.ENERGY_MAX:
                    continue  # Dead, or the meal would not fit: leaves the food to the others
                dx = torus_delta(creature.x, food.x, self.width)
                dy = torus_delta(creature.y, food.y, self.height)
                distance2 = dx * dx + dy * dy
                if distance2 < best_distance2:
                    best_distance2 = distance2
                    best = creature

            if best is not None:
                best.eat_food(food.energy)
                # The food comes back after a delay. A source that has been eaten FOOD_MAX_EATS
                # times is exhausted: it comes back at a new random place instead
                food.cooldown = config.FOOD_RESPAWN_DELAY
                food.eats += 1
                if not config.FOOD_FIXED_POSITIONS or food.eats >= config.FOOD_MAX_EATS:
                    food.x = self.rng.uniform(0, self.width)
                    food.y = self.rng.uniform(0, self.height)
                    food.eats = 0

        # Phase 3: poison. The closest creature touching it is hurt; the poison then moves to a new random place
        for poison in self.poisons:
            if poison.cooldown > 0:
                poison.cooldown -= 1
                continue
            victim = None
            best_distance2 = (config.CREATURE_RADIUS + config.FOOD_RADIUS) ** 2
            for creature in self.creatures:
                if not creature.alive:
                    continue
                dx = torus_delta(creature.x, poison.x, self.width)
                dy = torus_delta(creature.y, poison.y, self.height)
                distance2 = dx * dx + dy * dy
                if distance2 < best_distance2:
                    best_distance2 = distance2
                    victim = creature
            if victim is not None:
                victim.hit_by_poison(poison.energy)
                poison.cooldown = config.FOOD_RESPAWN_DELAY
                poison.x = self.rng.uniform(0, self.width)
                poison.y = self.rng.uniform(0, self.height)

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

    def _nearest(self, creature, items):
        """Nearest available item within the vision range: (distance², dx, dy), or None.
        Also returns whether any item is in range, available or not."""
        best = None
        best_distance2 = config.VISION_RANGE ** 2
        in_range = False
        for item in items:
            dx = torus_delta(creature.x, item.x, self.width)
            dy = torus_delta(creature.y, item.y, self.height)
            distance2 = dx * dx + dy * dy
            if distance2 <= config.VISION_RANGE ** 2:
                in_range = True
            if item.cooldown > 0:
                continue  # Not available yet: the network cannot see it
            if distance2 <= best_distance2:
                best_distance2 = distance2
                best = (distance2, dx, dy)
        return best, in_range

    def _direction(self, creature, found):
        """Network inputs for one kind of target: [distance, relative angle]. Nothing in sight: maximum distance, ahead."""
        if found is None:
            return [1.0, 0.0]
        distance2, dx, dy = found
        distance = math.sqrt(distance2) / config.VISION_RANGE
        angle = normalize_angle(math.atan2(dy, dx) - creature.angle) / math.pi
        return [distance, angle]

    def sense(self, creature):
        """Retourne les entrées du réseau, normalisées :
        [distance, angle relatif, énergie, vitesse, peut manger, distance poison, angle poison]."""
        food, in_range = self._nearest(creature, self.foods)
        creature.food_nearby = in_range  # Any food in range, even one that is not available yet (metric only)
        poison, _ = self._nearest(creature, self.poisons)

        energy = max(0.0, min(creature.energy / config.ENERGY_INPUT_MAX, 1.0))
        speed = creature.speed / config.CREATURE_MAX_SPEED
        # 1.0 if a meal would fit (same rule as the food phase), else 0.0
        can_eat = 1.0 if creature.energy + config.FOOD_ENERGY <= config.ENERGY_MAX else 0.0

        return (self._direction(creature, food) + [energy, speed, can_eat]
                + self._direction(creature, poison))

    def is_over(self):
        alive = sum(1 for c in self.creatures if c.alive)
        # The parents threshold only makes sense if the population is bigger than it
        threshold = config.PARENTS_COUNT if len(self.creatures) > config.PARENTS_COUNT else 0
        return alive <= threshold or self.tick >= config.GEN_MAX_TICKS


import config
from core.food import Food
from core.physics import torus_delta

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

    def update(self):
        for creature in self.creatures:
            creature.update(self.width, self.height)
            if not creature.alive:
                continue
            for food in self.foods:
                dx = torus_delta(creature.x, food.x, self.width)
                dy = torus_delta(creature.y, food.y, self.height)
                if dx * dx + dy * dy < (config.CREATURE_RADIUS + config.FOOD_RADIUS)**2:
                    creature.eat_food(food.energy)
                    food.x = self.rng.uniform(0, self.width)
                    food.y = self.rng.uniform(0, self.height)


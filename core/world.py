import math

import config
from core.food import Food
from core.obstacle import Obstacle
from core.physics import torus_delta, normalize_angle
from core.creature import Creature
from brain.network import NeuralNetwork

class World:
    def __init__(self, rng):
        self.rng = rng
        self.width = config.WORLD_WIDTH
        self.height = config.WORLD_HEIGHT
        self.creatures = []
        # Obstacles first: food, poison and creatures are never placed inside one
        self.obstacles = self._make_obstacles()
        reach = config.CREATURE_RADIUS + config.FOOD_RADIUS   # Far enough from an obstacle for a creature to touch it
        self.foods = [Food(*self._free_position(reach), config.FOOD_ENERGY) for _ in range(config.FOOD_COUNT)]
        # Poison: same kind of object as food, but its `energy` is the damage. Seen through its own two inputs
        self.poisons = [Food(*self._free_position(reach), config.POISON_ENERGY) for _ in range(config.POISON_COUNT)]
        self.tick = 0

    def _make_obstacles(self):
        """Random obstacles (shapes from OBSTACLE_SHAPES), kept apart so that there is always room to pass between two."""
        obstacles = []
        for _ in range(config.OBSTACLE_COUNT):
            for _attempt in range(100):
                radius = self.rng.uniform(config.OBSTACLE_RADIUS_MIN, config.OBSTACLE_RADIUS_MAX)
                x, y = self.rng.uniform(0, self.width), self.rng.uniform(0, self.height)
                if all(math.hypot(torus_delta(x, o.x, self.width), torus_delta(y, o.y, self.height))
                       >= radius + o.radius + config.OBSTACLE_MIN_GAP for o in obstacles):
                    shape = self.rng.choice(config.OBSTACLE_SHAPES)
                    obstacles.append(Obstacle(x, y, radius, shape, self.rng.uniform(0, 2 * math.pi)))
                    break   # No room found after 100 tries: this obstacle is skipped
        return obstacles

    def _blocked(self, x, y, margin):
        """True if the point is inside an obstacle, or closer than `margin` to its edge."""
        for o in self.obstacles:
            dx, dy = torus_delta(o.x, x, self.width), torus_delta(o.y, y, self.height)   # From the obstacle to the point
            if math.hypot(dx, dy) <= o.radius + margin:   # Inside the bounding circle: look at the real shape
                cx, cy, inside = o.closest(dx, dy)
                if inside or math.hypot(dx - cx, dy - cy) <= margin:
                    return True
        return False

    def _free_position(self, margin):
        """Random position outside every obstacle (last try if the world is too crowded)."""
        for _ in range(100):
            x, y = self.rng.uniform(0, self.width), self.rng.uniform(0, self.height)
            if not self._blocked(x, y, margin):
                break
        return x, y

    def _collide(self, creature):
        """A creature cannot enter an obstacle: it is pushed back to the edge, so it slides along it."""
        touched = False
        for _ in range(2):   # Two passes: pushed out of one obstacle, it must not end up inside a neighbour
            for o in self.obstacles:
                dx = torus_delta(o.x, creature.x, self.width)   # From the obstacle to the creature
                dy = torus_delta(o.y, creature.y, self.height)
                if dx * dx + dy * dy >= (o.radius + config.CREATURE_RADIUS) ** 2:
                    continue   # Outside the bounding circle
                pushed = o.push(dx, dy, config.CREATURE_RADIUS)
                if pushed:
                    creature.x = (o.x + pushed[0]) % self.width
                    creature.y = (o.y + pushed[1]) % self.height
                    touched = True
        if touched:
            creature.obstacle_ticks += 1

    def update(self):

        if self.is_over():
            return

        # Phase 1: Update all creatures
        for creature in self.creatures:
            if creature.alive:
                inputs = self.sense(creature)
                creature.update(inputs, self.width, self.height)
                self._collide(creature)

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
                    food.x, food.y = self._free_position(config.CREATURE_RADIUS + config.FOOD_RADIUS)
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
                poison.x, poison.y = self._free_position(config.CREATURE_RADIUS + config.FOOD_RADIUS)

        self.tick += 1

    def add_creature(self, brain):
        x, y = self._free_position(config.CREATURE_RADIUS)
        angle = self.rng.uniform(-math.pi, math.pi)
        creature = Creature(x, y, angle, config.INITIAL_ENERGY, brain)
        self.creatures.append(creature)

    def add_population(self,count):
        for _ in range(count):
            brain = NeuralNetwork(config.NN_INPUTS, config.NN_HIDDEN, config.NN_OUTPUTS)
            brain.randomize(self.rng, config.NN_INIT_STD)
            self.add_creature(brain)

    def nearest(self, creature, items):
        """Nearest available item in the creature's field of view: ((distance², dx, dy) or None, in_view).
        In view = within the vision range AND within VISION_FOV_DEGREES centred on the heading.
        in_view says whether any item is in view, available or not. Also used by the debug overlay."""
        best = None
        range2 = config.VISION_RANGE ** 2
        best_distance2 = range2
        in_view = False
        all_around = config.VISION_FOV_DEGREES >= 360
        half_fov = math.radians(config.VISION_FOV_DEGREES) / 2.0
        for item in items:
            dx = torus_delta(creature.x, item.x, self.width)
            dy = torus_delta(creature.y, item.y, self.height)
            distance2 = dx * dx + dy * dy
            if item.radius:
                # Obstacle: the distance is measured to its edge, the angle stays the one of its centre
                if distance2 > (range2 ** 0.5 + item.radius) ** 2:
                    continue   # Too far even for its bounding circle
                edge = item.edge_distance(-dx, -dy)   # The point (creature) relative to the obstacle centre
                distance2 = edge * edge
            if distance2 > range2:
                continue
            # Range is tested first: the angle (atan2) is only computed for the few items that are close enough
            if not all_around and abs(normalize_angle(math.atan2(dy, dx) - creature.angle)) > half_fov:
                continue  # Outside the field of view
            in_view = True
            if item.cooldown > 0:
                continue  # Not available yet: the network cannot see it
            if distance2 <= best_distance2:
                best_distance2 = distance2
                best = (distance2, dx, dy)
        return best, in_view

    def _direction(self, creature, found):
        """Network inputs for one kind of target: [distance, relative angle]. Nothing in view: maximum distance, ahead."""
        if found is None:
            return [1.0, 0.0]
        distance2, dx, dy = found
        distance = math.sqrt(distance2) / config.VISION_RANGE
        angle = normalize_angle(math.atan2(dy, dx) - creature.angle) / math.pi
        return [distance, angle]

    def sense(self, creature):
        """Retourne les entrées du réseau, normalisées :
        [distance, angle relatif, énergie, vitesse, peut manger, distance poison, angle poison,
        distance obstacle, angle obstacle]."""
        food, in_view = self.nearest(creature, self.foods)
        creature.food_nearby = in_view  # Any food in view, even one that is not available yet (metric only)
        poison, _ = self.nearest(creature, self.poisons)
        obstacle, _ = self.nearest(creature, self.obstacles)

        energy = max(0.0, min(creature.energy / config.ENERGY_INPUT_MAX, 1.0))
        speed = creature.speed / config.CREATURE_MAX_SPEED
        # 1.0 if a meal would fit (same rule as the food phase), else 0.0
        can_eat = 1.0 if creature.energy + config.FOOD_ENERGY <= config.ENERGY_MAX else 0.0

        return (self._direction(creature, food) + [energy, speed, can_eat]
                + self._direction(creature, poison) + self._direction(creature, obstacle))

    def is_over(self):
        alive = sum(1 for c in self.creatures if c.alive)
        # The parents threshold only makes sense if the population is bigger than it
        threshold = config.PARENTS_COUNT if len(self.creatures) > config.PARENTS_COUNT else 0
        return alive <= threshold or self.tick >= config.GEN_MAX_TICKS


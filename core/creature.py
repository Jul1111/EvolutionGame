import math

import config
from core.physics import normalize_angle

class Creature:
    def __init__(self, x, y, angle, energy, brain):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.speed = 0.0  # Current speed, decided by the network at each tick
        self.energy = energy
        self.brain = brain
        self.alive = True
        self.food_eaten = 0 
        self.poison_hits = 0
        self.age = 0
        # Exploration metrics: what the creature does when it sees no food
        self.food_nearby = True  # Set by World.sense each tick
        self.blind_ticks = 0
        self.blind_speed_sum = 0.0
        self.blind_turn_sum = 0.0

    def update(self, inputs, world_width, world_height):
        if not self.alive:
            return
        if self.energy <= 0:
            self.alive = False
            return

        # The network decides: outputs are in [-1, 1] (tanh)
        outputs = self.brain.forward(inputs)
        turn = float(outputs[0])
        speed_command = float(outputs[1])

        # Inertia: the network asks for a target speed, the speed moves toward it with limited acceleration
        target_speed = (speed_command + 1.0) / 2.0 * config.CREATURE_MAX_SPEED
        change = max(-config.CREATURE_ACCELERATION, min(config.CREATURE_ACCELERATION, target_speed - self.speed))
        self.speed += change

        # The faster the creature goes, the less it can turn
        max_turn = config.CREATURE_MAX_TURN * (1.0 - config.TURN_SPEED_PENALTY * self.speed / config.CREATURE_MAX_SPEED)
        self.angle = normalize_angle(self.angle + turn * max_turn)

        # Blind = no food at all within range, available or not (waiting next to a source is not exploring)
        if not self.food_nearby:
            self.blind_ticks += 1
            self.blind_speed_sum += self.speed
            self.blind_turn_sum += abs(turn)

        # Update the creature's position based on its speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Keep the creature within the bounds of the world
        self.x  %= world_width
        self.y  %= world_height

        # Moving costs energy: base cost + cost proportional to speed
        self.energy -= config.ENERGY_BASE_COST + config.ENERGY_MOVE_COST * self.speed

        self.age += 1 #Added age increment to track how long the creature has been alive

    def hit_by_poison(self, amount):
        """Touching a poison costs energy. The creature dies at its next update if the energy reaches 0."""
        if not self.alive:
            return
        self.energy -= amount
        self.poison_hits += 1

    def eat_food(self,amount):
        if not self.alive:
            return
        self.energy = min(self.energy + amount, config.ENERGY_MAX)  # The excess is lost
        self.food_eaten += 1
        

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
        self.age = 0

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

        self.angle = normalize_angle(self.angle + turn * config.CREATURE_MAX_TURN)
        self.speed = (speed_command + 1.0) / 2.0 * config.CREATURE_MAX_SPEED

        # Update the creature's position based on its speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Keep the creature within the bounds of the world
        self.x  %= world_width
        self.y  %= world_height

        # Moving costs energy: base cost + cost proportional to speed
        self.energy -= config.ENERGY_BASE_COST + config.ENERGY_MOVE_COST * self.speed

        self.age += 1 #Added age increment to track how long the creature has been alive

    def eat_food(self,amount):
        if not self.alive:
            return
        self.energy += amount
        self.food_eaten += 1
        

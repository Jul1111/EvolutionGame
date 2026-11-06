import math

class Creature:
    def __init__(self, x, y, angle, speed,energy,energy_cost_per_tick):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.speed = speed
        self.energy = energy
        self.energy_cost_per_tick = energy_cost_per_tick
        self.alive = True
        self.food_eaten = 0 
        self.age = 0

    def update(self, world_width, world_height):
        if not self.alive:
            return
        if self.energy <= 0:
            self.alive = False
            return
        # Update the creature's position based on its speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Keep the creature within the bounds of the world
        self.x  %= world_width
        self.y  %= world_height
        self.energy = self.energy - self.energy_cost_per_tick

        self.age += 1 #Added age increment to track how long the creature has been alive

    def eat_food(self,amount):
        if not self.alive:
            return
        self.energy += amount
        self.food_eaten += 1
        

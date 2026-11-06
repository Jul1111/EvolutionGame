import math

class Creature:
    def __init__(self, x, y, angle, speed):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.speed = speed
        

    def update(self):
        # Update the creature's position based on its speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

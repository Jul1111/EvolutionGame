class Food:
    radius = 0.0   # Points, not discs: World.nearest measures distance to the edge only for items that have a radius
    def __init__(self, x, y, energy):
        self.x = x
        self.y = y
        self.energy = energy
        self.cooldown = 0  # Ticks left before the food is available again (0 = available)
        self.eats = 0      # Times eaten at the current position

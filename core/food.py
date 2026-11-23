class Food:
    radius = 0.0   # Points, not discs: World.nearest measures distance to the edge only for items that have a radius
    def __init__(self, x, y, energy, kind=0):
        self.x = x
        self.y = y
        self.energy = energy
        self.kind = kind   # 0 or 1 (FOOD_TYPES = 2): which diet it feeds
        self.cooldown = 0  # Ticks left before the food is available again (0 = available)

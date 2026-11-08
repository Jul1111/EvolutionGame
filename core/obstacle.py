import math

import numpy as np

SIDES = {"triangle": 3, "square": 4}   # Any other shape name is a disc


class Obstacle:
    """Solid obstacle (disc, square or triangle). Creatures cannot enter it; the network sees its nearest edge.
    `radius` is the radius of the circle around the shape: used to space obstacles, to cull and to draw wrapped copies.
    Points handed to the methods are relative to the obstacle centre."""
    cooldown = 0   # Always there: lets World.nearest treat it like food and poison

    def __init__(self, x, y, radius, shape="circle", rotation=0.0):
        self.x = x
        self.y = y
        self.radius = radius
        self.shape = shape if shape in SIDES else "circle"
        self.rotation = rotation
        n = SIDES.get(self.shape)
        # Counter-clockwise corners (regular polygon inscribed in the circle); None for a disc
        self.vertices = ([(radius * math.cos(rotation + 2 * math.pi * k / n),
                           radius * math.sin(rotation + 2 * math.pi * k / n)) for k in range(n)] if n else None)

    def closest(self, px, py):
        """Closest point of the outline to (px, py): (x, y, point_is_inside)."""
        if self.vertices is None:
            d = math.hypot(px, py)
            if d < 1e-9:
                return self.radius, 0.0, True
            return px / d * self.radius, py / d * self.radius, d < self.radius
        best, best_d2 = None, float("inf")
        inside = True
        n = len(self.vertices)
        for i in range(n):
            ax, ay = self.vertices[i]
            bx, by = self.vertices[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            if ex * (py - ay) - ey * (px - ax) < 0:
                inside = False   # On the outer side of this edge
            t = max(0.0, min(1.0, ((px - ax) * ex + (py - ay) * ey) / (ex * ex + ey * ey)))
            cx, cy = ax + t * ex, ay + t * ey
            d2 = (px - cx) ** 2 + (py - cy) ** 2
            if d2 < best_d2:
                best, best_d2 = (cx, cy), d2
        return best[0], best[1], inside

    def edge_distance(self, px, py):
        """Distance from the point to the shape (0 when inside)."""
        cx, cy, inside = self.closest(px, py)
        return 0.0 if inside else math.hypot(px - cx, py - cy)

    def edge_distance_np(self, px, py):
        """edge_distance for arrays of points (relative to the centre): same result, computed all at once."""
        if self.vertices is None:
            return np.maximum(0.0, np.hypot(px, py) - self.radius)
        best = np.full(px.shape, np.inf)
        inside = np.ones(px.shape, dtype=bool)
        n = len(self.vertices)
        for i in range(n):
            ax, ay = self.vertices[i]
            bx, by = self.vertices[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            inside &= ex * (py - ay) - ey * (px - ax) >= 0
            t = np.clip(((px - ax) * ex + (py - ay) * ey) / (ex * ex + ey * ey), 0.0, 1.0)
            best = np.minimum(best, np.hypot(px - (ax + t * ex), py - (ay + t * ey)))
        return np.where(inside, 0.0, best)

    def push(self, px, py, margin):
        """New position when the point is closer than `margin` to the shape (or inside it), else None."""
        cx, cy, inside = self.closest(px, py)
        d = math.hypot(px - cx, py - cy)
        if not inside and d >= margin:
            return None
        if d < 1e-9:
            ux, uy = (px / math.hypot(px, py), py / math.hypot(px, py)) if math.hypot(px, py) > 1e-9 else (1.0, 0.0)
        else:
            ux, uy = ((cx - px) / d, (cy - py) / d) if inside else ((px - cx) / d, (py - cy) / d)
        return cx + ux * margin, cy + uy * margin

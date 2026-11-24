class Food:
    radius = 0.0   # Points, not discs: World.nearest measures distance to the edge only for items that have a radius
    def __init__(self, x, y, energy, kind=0):
        self.x = x
        self.y = y
        self.energy = energy
        self.kind = kind   # 0 .. FOOD_TYPES - 1: which diet it feeds (kind_position)
        self.cooldown = 0  # Ticks left before the food is available again (0 = available)


def kind_position(kind, kinds):
    """Diet that a food of this kind feeds best: the kinds spread evenly over [0, 1] (two kinds: 0 and 1)."""
    return kind / (kinds - 1) if kinds > 1 else 0.0


def kind_pattern(cfg):
    """Kind of the food of each index, repeating: FOOD_KIND_SHARES (whole numbers, one per kind; empty = equal shares)
    spread as evenly as possible along the list. Equal shares: 0, 1, .., FOOD_TYPES - 1 (food k is of kind
    k % FOOD_TYPES, as before the shares)."""
    n = cfg.FOOD_TYPES
    shares = [int(s) for s in cfg.FOOD_KIND_SHARES] or [1] * n
    if len(shares) != n or min(shares) < 1:
        raise ValueError(f"FOOD_KIND_SHARES: {n} whole numbers >= 1 expected, got {cfg.FOOD_KIND_SHARES}")
    total, counts, pattern = sum(shares), [0] * n, []
    for t in range(total):
        # The kind furthest behind its share so far (ties: the lowest kind)
        k = max(range(n), key=lambda k: ((t + 1) * shares[k] / total - counts[k], -k))
        counts[k] += 1
        pattern.append(k)
    return pattern

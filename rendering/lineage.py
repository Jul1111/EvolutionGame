"""Lineages, for display only: which founder each living creature descends from.
The simulation keeps parent_id but not the founder, and dead parents leave the world. The tracker remembers the
founder of every creature it has seen: a newborn inherits its parent's founder. A parent is at least MATURITY_AGE
ticks old when it gives birth, so it has always been seen on an earlier frame, even at high speed.
Creatures loaded from a save start new lineages (their ancestors are unknown).
Never touches the simulation and draws no random number."""
import colorsys

import config


def lineage_color(founder):
    """Stable colour of a lineage. Hues are spread with the golden ratio and the green band is skipped: green is food."""
    h = (founder * 0.6180339887) % 1.0
    hue = (h * 0.75 + 0.47) % 1.0          # Uses 0.47 → 1.22: skips 0.22-0.47 (yellow-green to green-cyan)
    sat = 0.55 + 0.25 * ((founder * 0.381966) % 1.0)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, 0.95)
    return (int(r * 255), int(g * 255), int(b * 255))


class LineageTracker:
    def __init__(self):
        self._world = None
        self.founder = {}       # uid → uid of the founder of its lineage
        self._summary = (0, 0.0, None)
        self._summary_tick = None

    def update(self, world):
        """Call once per frame, before drawing. Restarts when the world is a new one."""
        if world is not self._world:
            self._world = world
            self.founder = {}
            self._summary_tick = None
        founder = self.founder
        for c in world.creatures:
            if c.uid not in founder:
                founder[c.uid] = founder.get(c.parent_id, c.uid) if c.parent_id is not None else c.uid

    def of(self, creature):
        return self.founder.get(creature.uid, creature.uid)

    def summary(self, world):
        """(living lineages, share of the largest one, founder of the largest one). Recomputed once per tick."""
        if self._summary_tick != world.tick:
            counts = {}
            for c in world.creatures:
                if c.alive:
                    f = self.of(c)
                    counts[f] = counts.get(f, 0) + 1
            n = sum(counts.values())
            if counts:
                top = max(counts, key=counts.get)
                self._summary = (len(counts), counts[top] / n, top)
            else:
                self._summary = (0, 0.0, None)
            self._summary_tick = world.tick
        return self._summary

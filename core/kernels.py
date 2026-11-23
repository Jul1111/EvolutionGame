"""Compiled versions (numba) of the two heaviest steps of a tick, when numba is installed.

- nearest_points: nearest available food, poison or obstacle (distance to its outline) in view of each creature,
  the creatures shared out over the cores (one thread per core, parallel loop).
- contact_winners: which creature gets each food or poison (closest one in contact, items in list order).

Same formulas, same order of operations as the numpy code of core/world.py, which stays as the fallback (numba
missing, or EVOLUTION_NUMBA=0) and as the reference the tests compare to. Compiled once, then cached on disk
(__pycache__): the first launch after a change takes a few seconds.
"""
import math
import os

import numpy as np

from core.grid import _neighbour_offsets, cell_counts

try:
    if os.environ.get("EVOLUTION_NUMBA", "1") == "0":
        raise ImportError
    import numba
    from numba import njit, prange
    ENABLED = True
except ImportError:
    numba = None   # type: ignore[assignment]
    ENABLED = False


def set_threads(n):
    """Threads of the parallel loops (1 in the experiment workers: the seeds already fill the cores)."""
    if ENABLED:
        numba.set_num_threads(max(1, min(n, numba.config.NUMBA_NUM_THREADS)))


def _cells(bx, by, width, height, reach):
    """Grid of the points b (core/grid.py): (nx, ny, b sorted by cell, start and count of each cell, offsets)."""
    nx, ny = cell_counts(width, height, reach)
    cw, ch = width / nx, height / ny
    bcell = (np.floor_divide(bx, cw).astype(np.int64) % nx) * ny + np.floor_divide(by, ch).astype(np.int64) % ny
    order = np.argsort(bcell, kind="stable")
    counts = np.bincount(bcell, minlength=nx * ny)
    starts = np.cumsum(counts) - counts
    return (nx, ny, order, starts, counts, np.array(_neighbour_offsets(nx), np.int64),
            np.array(_neighbour_offsets(ny), np.int64))


def _shapes(items):
    """Obstacle outlines as arrays: (radius, number of corners (0 = disc), corners (m, 4, 2))."""
    m = len(items)
    radius = np.zeros(m)
    sides = np.zeros(m, np.int64)
    corners = np.zeros((m, 4, 2))
    for j, o in enumerate(items):
        radius[j] = getattr(o, "radius", 0.0)
        if getattr(o, "vertices", None):
            sides[j] = len(o.vertices)
            corners[j, :sides[j]] = o.vertices
    return radius, sides, corners


if ENABLED:
    @njit(cache=True)
    def _edge_distance(px, py, radius, sides, corners):  # pragma: no cover (compiled)
        """Obstacle.edge_distance_np for one point (relative to the centre)."""
        if sides == 0:
            return max(0.0, math.hypot(px, py) - radius)
        best = np.inf
        inside = True
        for k in range(sides):
            ax, ay = corners[k, 0], corners[k, 1]
            bx, by = corners[(k + 1) % sides, 0], corners[(k + 1) % sides, 1]
            ex, ey = bx - ax, by - ay
            if not ex * (py - ay) - ey * (px - ax) >= 0:
                inside = False
            t = min(max(((px - ax) * ex + (py - ay) * ey) / (ex * ex + ey * ey), 0.0), 1.0)
            best = min(best, math.hypot(px - (ax + t * ex), py - (ay + t * ey)))
        return 0.0 if inside else best

    @njit(parallel=True, cache=True)
    def _nearest_points(cx, cy, heading, ix, iy, available, range_, fov, half_fov, width, height, shaped, iradius,
                        sides, corners, nx, ny, order, starts, counts, offx, offy):  # pragma: no cover (compiled)
        range2 = range_ ** 2
        n = len(cx)
        best = np.full(n, np.inf)
        bdx = np.zeros(n)
        bdy = np.zeros(n)
        cw, ch = width / nx, height / ny
        for i in prange(n):
            acx = int(math.floor(cx[i] / cw)) % nx
            acy = int(math.floor(cy[i] / ch)) % ny
            b, bj, bx_, by_ = np.inf, -1, 0.0, 0.0
            for ox in offx:
                for oy in offy:
                    cell = ((acx + ox) % nx) * ny + (acy + oy) % ny
                    for k in range(starts[cell], starts[cell] + counts[cell]):
                        j = order[k]
                        if not available[j]:
                            continue
                        dx = (ix[j] - cx[i]) % width
                        if dx > width / 2:
                            dx -= width
                        dy = (iy[j] - cy[i]) % height
                        if dy > height / 2:
                            dy -= height
                        d2 = dx * dx + dy * dy
                        if shaped and d2 <= (range_ + iradius[j]) ** 2:   # Distance to the outline
                            edge = _edge_distance(-dx, -dy, iradius[j], sides[j], corners[j])
                            d2 = edge * edge
                        if d2 > range2:
                            continue
                        if fov:
                            rel = (math.atan2(dy, dx) - heading[i] + math.pi) % (2 * math.pi) - math.pi
                            if abs(rel) > half_fov:
                                continue
                        if d2 < b or (d2 == b and j > bj):   # An exact tie goes to the last item
                            b, bj, bx_, by_ = d2, j, dx, dy
            if bj >= 0:
                best[i], bdx[i], bdy[i] = b, bx_, by_
        return best, bdx, bdy

    @njit(cache=True)
    def _contact_winners(ix, iy, energy, available, X, Y, E, radius, emax, reach2, food_radius, fits, width,
                         height, nx, ny, order, starts, counts, offx, offy):  # pragma: no cover (compiled)
        m = len(ix)
        win = np.full(m, -1, np.int64)
        cw, ch = width / nx, height / ny
        for j in range(m):   # In list order: an item changes E, which matters for the next one
            if not available[j]:
                continue
            acx = int(math.floor(ix[j] / cw)) % nx
            acy = int(math.floor(iy[j] / ch)) % ny
            g, gi = np.inf, -1
            for ox in offx:
                for oy in offy:
                    cell = ((acx + ox) % nx) * ny + (acy + oy) % ny
                    for k in range(starts[cell], starts[cell] + counts[cell]):
                        i = order[k]
                        dx = (ix[j] - X[i] + width / 2) % width - width / 2
                        dy = (iy[j] - Y[i] + height / 2) % height - height / 2
                        d2 = dx * dx + dy * dy
                        if not d2 < reach2[i]:
                            continue
                        if fits and not E[i] + energy[j] <= emax[i]:
                            continue
                        gap = math.sqrt(d2) - radius[i]
                        if gap < g or (gap == g and i < gi):   # A tie goes to the first creature
                            g, gi = gap, i
            if gi >= 0:
                win[j] = gi
                E[gi] = min(E[gi] + energy[j], emax[gi]) if fits else E[gi] - energy[j]
        return win


def nearest_points(items, cx, cy, heading, ix, iy, cool, cfg, width, height):
    """(distance², dx, dy) of the nearest available item in view of each creature (inf when none); for an obstacle
    the distance to its outline."""
    radius, sides, corners = _shapes(items)
    shaped = bool(radius.any())
    grid = _cells(ix, iy, width, height, cfg.VISION_RANGE + (float(radius.max()) if shaped else 0.0))
    return _nearest_points(cx, cy, heading, ix, iy, cool <= 0, float(cfg.VISION_RANGE), cfg.VISION_FOV_DEGREES < 360,
                           math.radians(cfg.VISION_FOV_DEGREES) / 2.0, float(width), float(height), shaped, radius,
                           sides, corners, *grid)


def contact_winners(ix, iy, energy, available, X, Y, E, radius, emax, food_radius, fits, width, height):
    """Index of the creature that gets each item (-1: nobody). Updates E as the effects will (meal capped at the
    reserve, or poison damage)."""
    reach2 = (radius + food_radius) ** 2
    grid = _cells(X, Y, width, height, float(np.sqrt(reach2.max())))
    return _contact_winners(ix, iy, energy, available, X, Y, E, radius, emax, reach2, float(food_radius), fits,
                            float(width), float(height), *grid)


def worker_init(jobs):
    """Initializer of the experiment process pools: the cores are shared out between the `jobs` workers (one
    thread each when there are as many workers as cores: the seeds already fill them)."""
    set_threads((os.cpu_count() or 1) // max(1, jobs or os.cpu_count() or 1))

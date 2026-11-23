"""Spatial grid on the torus: the pairs (a, b) of two point sets that may be closer than a given reach.

The world is cut into cells at least `reach` wide; a point can only be within reach of the points of its own cell
and of the 8 around it, so only those pairs are returned (instead of every pair). The caller then computes the exact
distances of these pairs with its usual formula: same values as with the full matrix, just fewer of them.
"""
import numpy as np


def cell_counts(width, height, reach):
    """Cells per side, each at least `reach` wide (with a small margin against rounding at the borders)."""
    return max(1, int(width // (reach * 1.001))), max(1, int(height // (reach * 1.001)))


def _neighbour_offsets(n):
    """Distinct cell offsets -1, 0, 1 on a side of n cells (fewer when n < 3: the neighbours wrap onto each
    other)."""
    return sorted({o % n for o in (-1, 0, 1)})


def near_pairs(ax, ay, bx, by, reach, width, height):
    """(index in a, index in b) of every pair of points whose cells touch (3×3 neighbourhood on the torus). Every
    pair closer than `reach` is in it, each pair once; their order is unspecified. Coordinates in [0, width) and
    [0, height)."""
    nx, ny = cell_counts(width, height, reach)
    cw, ch = width / nx, height / ny
    acx = np.floor_divide(ax, cw).astype(np.int64) % nx
    acy = np.floor_divide(ay, ch).astype(np.int64) % ny
    bcell = (np.floor_divide(bx, cw).astype(np.int64) % nx) * ny + np.floor_divide(by, ch).astype(np.int64) % ny
    order = np.argsort(bcell, kind="stable")              # b sorted by cell
    counts = np.bincount(bcell, minlength=nx * ny)
    starts = np.cumsum(counts) - counts
    ia, ib = [], []
    rows = np.arange(len(ax))
    for ox in _neighbour_offsets(nx):
        for oy in _neighbour_offsets(ny):
            cell = ((acx + ox) % nx) * ny + (acy + oy) % ny
            cnt = counts[cell]
            total = int(cnt.sum())
            if not total:
                continue
            first = np.repeat(starts[cell], cnt)
            within = np.arange(total) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            ia.append(np.repeat(rows, cnt))
            ib.append(order[first + within])
    if not ia:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    return np.concatenate(ia), np.concatenate(ib)

import numpy as np

from core.grid import near_pairs


def _torus_d2(ax, ay, bx, by, w, h):
    dx = (bx[None, :] - ax[:, None]) % w
    dx = np.where(dx > w / 2, dx - w, dx)
    dy = (by[None, :] - ay[:, None]) % h
    dy = np.where(dy > h / 2, dy - h, dy)
    return dx * dx + dy * dy


def test_near_pairs_hold_every_close_pair_once():
    rng = np.random.default_rng(0)
    # Big world, one cell wide on a side, two cells, exactly reach-wide cells
    for w, h, reach in ((2560, 1440, 200), (300, 1440, 200), (390, 390, 200), (1000, 600, 100), (50, 50, 200)):
        ax, ay = rng.uniform(0, w, 300), rng.uniform(0, h, 300)
        bx, by = rng.uniform(0, w, 200), rng.uniform(0, h, 200)
        ax[:5], bx[:5] = 0.0, np.nextafter(w, 0)   # Points on the borders of the torus
        ia, ib = near_pairs(ax, ay, bx, by, reach, w, h)
        pairs = set(zip(ia.tolist(), ib.tolist()))
        assert len(pairs) == len(ia)   # No pair twice
        close = np.argwhere(_torus_d2(ax, ay, bx, by, w, h) <= reach ** 2)
        assert {(int(i), int(j)) for i, j in close} <= pairs


def test_near_pairs_empty_sets():
    ia, ib = near_pairs(np.zeros(0), np.zeros(0), np.ones(3), np.ones(3), 50, 500, 500)
    assert len(ia) == len(ib) == 0

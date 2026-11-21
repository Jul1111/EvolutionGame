import math


def torus_delta(a,b,size):
    """Shortest signed displacement from a to b on an axis that wraps around.
    Positive = to the right / down, negative = to the left / up."""
    delta = (b - a) % size
    if delta > size / 2:
        delta -= size
    return delta


def normalize_angle(angle):
    """Brings an angle in radians into [-π, π)."""
    return (angle + math.pi) % (2 * math.pi) - math.pi

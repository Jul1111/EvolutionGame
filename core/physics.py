import math


def torus_delta(a,b,size):
    """Déplacement signé le plus court de a vers b sur un axe qui boucle.
    Positif = vers la droite / le bas, négatif = vers la gauche / le haut."""
    delta = (b - a) % size
    if delta > size / 2:
        delta -= size
    return delta


def normalize_angle(angle):
    """Ramène un angle en radians dans [-π, π)."""
    return (angle + math.pi) % (2 * math.pi) - math.pi

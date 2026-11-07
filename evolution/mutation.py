import numpy as np


def mutate(genome, rng, std):
    """Retourne un NOUVEAU génome : chaque poids reçoit un bruit gaussien (moyenne 0, écart-type std)."""
    return np.array([w + rng.gauss(0, std) for w in genome])

import random

import numpy as np

from brain.profiles import PROFILES, new_brain, input_labels, n_params
from evolution.mutation import mutate


def test_genome_roundtrip_every_profile():
    rng = random.Random(0)
    for name in PROFILES:
        brain = new_brain(name)
        brain.randomize(rng)
        genome = brain.get_genome()
        assert len(genome) == n_params(name)
        other = new_brain(name)
        other.set_genome(genome)
        x = [0.3] * len(input_labels(name))
        assert np.allclose(brain.forward(x), other.forward(x))


def test_known_sizes():
    assert n_params("complet") == 74   # 9 inputs, 6 hidden, 2 outputs: the network of the documented runs
    assert n_params("chasseur") == 6
    assert n_params("scripte") == 0


def test_mutation_is_a_copy():
    g = np.zeros(10)
    child = mutate(g, random.Random(1), 0.1)
    assert np.all(g == 0) and not np.all(child == 0)


def test_scripted_heads_for_food():
    brain = new_brain("scripte")
    # Food on the right (positive angle), can eat, no poison or obstacle in view
    turn, _ = brain.forward([0.5, 0.2, 1.0, 1.0, 0.0, 1.0, 0.0])
    assert turn > 0

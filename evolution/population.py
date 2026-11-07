import config
from brain.network import NeuralNetwork
from evolution.mutation import mutate


def select_parents(creatures, count):
    """Retourne les `count` meilleures créatures, classées par (âge, énergie restante)."""
    return sorted(creatures, key=lambda c: (c.age, c.energy), reverse=True)[:count]


def _brain_from_genome(genome):
    brain = NeuralNetwork(config.NN_INPUTS, config.NN_HIDDEN, config.NN_OUTPUTS)
    brain.set_genome(genome)
    return brain


def brains_from_genomes(genomes, rng):
    """Retourne POPULATION_SIZE cerveaux : les parents (élitisme) puis des enfants mutés."""
    # Élitisme : copies des parents, créatures neuves (âge, énergie, position remis à zéro)
    brains = [_brain_from_genome(g) for g in genomes]

    # Enfants : un parent après l'autre, copie + bruit
    for i in range(config.POPULATION_SIZE - config.PARENTS_COUNT):
        parent_genome = genomes[i % len(genomes)]
        brains.append(_brain_from_genome(mutate(parent_genome, rng, config.MUTATION_STD)))
    return brains

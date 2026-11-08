import config
from brain.profiles import new_brain
from evolution.mutation import mutate


def rank_key(creature):
    """Ranking: age, then food eaten, then energy left (only to break exact ties).
    Food eaten comes before energy: once many creatures reach the time cap, ranking by energy rewards the ones
    that barely move (they spend less), and evolution drifts toward immobility."""
    return (creature.age, creature.food_eaten, creature.energy)


def select_parents(creatures, count):
    """Retourne les `count` meilleures créatures, classées par rank_key (âge, nourriture mangée, énergie)."""
    return sorted(creatures, key=rank_key, reverse=True)[:count]


def _brain_from_genome(genome, profile):
    brain = new_brain(profile)
    brain.set_genome(genome)
    return brain


def brains_from_genomes(genomes, rng, profile, size):
    """Retourne `size` cerveaux du profil : les parents (élitisme) puis des enfants mutés.
    Une sauvegarde plus grosse que la place disponible est tronquée (les génomes sont classés du meilleur au pire)."""
    genomes = genomes[:config.parents_for(size)]
    # Élitisme : copies des parents, créatures neuves (âge, énergie, position remis à zéro)
    brains = [_brain_from_genome(g, profile) for g in genomes]

    # Enfants : un parent après l'autre, copie + bruit
    for i in range(size - len(genomes)):
        parent_genome = genomes[i % len(genomes)]
        brains.append(_brain_from_genome(mutate(parent_genome, rng, config.MUTATION_STD), profile))
    return brains

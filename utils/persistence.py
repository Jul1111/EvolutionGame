import os
import time

import numpy as np

from brain.profiles import paths, n_params


def save_genomes(profile, genomes, generation):
    """Sauvegarde les génomes des parents (classés) d'un profil et le numéro de génération terminée."""
    file = paths(profile)[0]
    os.makedirs(os.path.dirname(file), exist_ok=True)
    # Écriture dans un fichier temporaire puis remplacement : pas de sauvegarde corrompue en cas de crash
    # Le nom doit finir par .npz, sinon numpy l'ajoute lui-même
    tmp = os.path.join(os.path.dirname(file), "latest_tmp.npz")
    np.savez(tmp, genomes=np.array(genomes), generation=generation)
    os.replace(tmp, file)


def load_genomes(profile):
    """Retourne (genomes, generation) ou None si le profil n'a pas de sauvegarde."""
    file = paths(profile)[0]
    if not os.path.exists(file):
        return None
    data = np.load(file)
    genomes, generation = data["genomes"], int(data["generation"])
    expected = n_params(profile)
    if genomes.shape[1] != expected:
        # The profile changed since the save: set it aside instead of crashing or overwriting it
        stamp = time.strftime("%Y%m%d_%H%M%S")
        moved = file.replace(".npz", f"_incompatible_{stamp}.npz")
        data.close()
        os.replace(file, moved)
        print(f"{profile} : sauvegarde incompatible ({genomes.shape[1]} poids au lieu de {expected}), mise de côté, départ de zéro")
        return None
    return genomes, generation


def archive_genomes(profile):
    """Fresh start: set aside the existing save of the profile (timestamped) instead of deleting it."""
    file = paths(profile)[0]
    if os.path.exists(file):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        os.replace(file, file.replace(".npz", f"_ancien_{stamp}.npz"))

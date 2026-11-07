import os
import time

import numpy as np

import config
from brain.network import NeuralNetwork


def save_genomes(genomes, generation):
    """Sauvegarde les génomes des parents (classés) et le numéro de génération terminée."""
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    # Écriture dans un fichier temporaire puis remplacement : pas de sauvegarde corrompue en cas de crash
    # Le nom doit finir par .npz, sinon numpy l'ajoute lui-même
    tmp = os.path.join(config.SAVE_DIR, "latest_tmp.npz")
    np.savez(tmp, genomes=np.array(genomes), generation=generation)
    os.replace(tmp, config.GENOMES_FILE)


def load_genomes():
    """Retourne (genomes, generation) ou None si aucune sauvegarde n'existe."""
    if not os.path.exists(config.GENOMES_FILE):
        return None
    data = np.load(config.GENOMES_FILE)
    genomes, generation = data["genomes"], int(data["generation"])
    expected = NeuralNetwork(config.NN_INPUTS, config.NN_HIDDEN, config.NN_OUTPUTS).n_weights()
    if genomes.shape[1] != expected:
        # The network changed since the save: set it aside instead of crashing or overwriting it
        stamp = time.strftime("%Y%m%d_%H%M%S")
        moved = config.GENOMES_FILE.replace(".npz", f"_incompatible_{stamp}.npz")
        data.close()
        os.replace(config.GENOMES_FILE, moved)
        print(f"Sauvegarde incompatible ({genomes.shape[1]} poids au lieu de {expected}) : mise de côté, départ de zéro")
        return None
    return genomes, generation


def archive_genomes():
    """Fresh start: set aside the existing save (timestamped) instead of deleting it."""
    if os.path.exists(config.GENOMES_FILE):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        os.replace(config.GENOMES_FILE, config.GENOMES_FILE.replace(".npz", f"_ancien_{stamp}.npz"))

import os

import numpy as np

import config


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
    return data["genomes"], int(data["generation"])

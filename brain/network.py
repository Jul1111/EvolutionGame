import numpy as np

class NeuralNetwork:
    """Réseau feed-forward : entrées → couche cachée (tanh) → sorties (tanh)."""
    def __init__(self, n_inputs, n_hidden, n_outputs):
        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self.n_outputs = n_outputs
        
        self.w1 = np.zeros((n_hidden, n_inputs))  # Poids de la couche d'entrée à la couche cachée
        self.b1 = np.zeros((n_hidden,))           # Biais de la couche
        self.w2 = np.zeros((n_outputs, n_hidden))  # Poids de la couche cachée à la couche de sortie
        self.b2 = np.zeros((n_outputs,))           # Biais de la couche

    def n_weights(self):
        """Retourne le nombre total de poids et biais dans le réseau."""
        return (self.n_hidden * self.n_inputs + self.n_hidden + 
                self.n_outputs * self.n_hidden + self.n_outputs)

    def forward(self, inputs):
        """Fait passer les entrées x à travers le réseau et retourne les sorties."""
        x = np.array(inputs, dtype=float)

        hidden = np.tanh(self.w1 @ x + self.b1)  # Activation de la couche cachée
        output = np.tanh(self.w2 @ hidden + self.b2)  # Activation de la couche de sortie
        
        return output

    def activations(self, inputs):
        """Comme forward, mais renvoie aussi la couche cachée : (hidden, output). Sert à l'affichage, ne modifie rien."""
        x = np.array(inputs, dtype=float)
        hidden = np.tanh(self.w1 @ x + self.b1)
        output = np.tanh(self.w2 @ hidden + self.b2)
        return hidden, output

    def get_genome(self):
        """Retourne le génome du réseau sous forme d'un vecteur 1D."""
        return np.concatenate([self.w1.flatten(), self.b1, self.w2.flatten(), self.b2])

    def set_genome(self, genome):
        """Charge un génome (liste ou vecteur 1D) dans les poids et biais du réseau."""
        genome = np.asarray(genome, dtype=float)
        if len(genome) != self.n_weights():
            raise ValueError(f"Génome de taille {len(genome)}, {self.n_weights()} attendue")

        # Même ordre que get_genome : w1, b1, w2, b2
        n1 = self.w1.size
        n2 = n1 + self.b1.size
        n3 = n2 + self.w2.size

        # .copy() : un morceau est une vue sur genome, le réseau ne doit pas rester lié à lui
        self.w1 = genome[:n1].reshape(self.w1.shape).copy()
        self.b1 = genome[n1:n2].copy()
        self.w2 = genome[n2:n3].reshape(self.w2.shape).copy()
        self.b2 = genome[n3:].copy()

    def randomize(self, rng, std=0.5):
        """Tire tous les poids et biais selon une loi normale (moyenne 0, écart-type std)."""
        self.set_genome([rng.gauss(0, std) for _ in range(self.n_weights())])

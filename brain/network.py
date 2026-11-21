import numpy as np

class NeuralNetwork:
    """Feed-forward network: inputs → hidden layer (tanh) → outputs (tanh)."""
    def __init__(self, n_inputs, n_hidden, n_outputs):
        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self.n_outputs = n_outputs

        # With no hidden neuron (n_hidden = 0) the inputs go straight to the outputs: everything is in w1 and b1
        self.direct = n_hidden == 0
        self.w1 = np.zeros((n_outputs if self.direct else n_hidden, n_inputs))  # Weights of the first layer
        self.b1 = np.zeros((self.w1.shape[0],))                                  # Biases of the first layer
        self.w2 = np.zeros((n_outputs, n_hidden))  # Weights from the hidden layer to the outputs (empty if direct)
        self.b2 = np.zeros((0 if self.direct else n_outputs,))                   # Biases of the outputs

    def n_weights(self):
        """Total number of weights and biases of the network."""
        if self.direct:
            return self.n_outputs * self.n_inputs + self.n_outputs
        return (self.n_hidden * self.n_inputs + self.n_hidden +
                self.n_outputs * self.n_hidden + self.n_outputs)

    def forward(self, inputs):
        """Runs the inputs through the network and returns the outputs."""
        return self.activations(inputs)[1]

    def activations(self, inputs):
        """Like forward, but also returns the hidden layer: (hidden, output). Used by the display, changes
        nothing."""
        x = np.array(inputs, dtype=float)
        if self.direct:
            return np.zeros(0), np.tanh(self.w1 @ x + self.b1)
        hidden = np.tanh(self.w1 @ x + self.b1)
        output = np.tanh(self.w2 @ hidden + self.b2)
        return hidden, output

    def get_genome(self):
        """The genome of the network as a 1D vector."""
        return np.concatenate([self.w1.flatten(), self.b1, self.w2.flatten(), self.b2])

    def set_genome(self, genome):
        """Loads a genome (list or 1D vector) into the weights and biases of the network."""
        genome = np.asarray(genome, dtype=float)
        if len(genome) != self.n_weights():
            raise ValueError(f"Genome of size {len(genome)}, expected {self.n_weights()}")

        # Same order as get_genome: w1, b1, w2, b2
        n1 = self.w1.size
        n2 = n1 + self.b1.size
        n3 = n2 + self.w2.size

        # .copy(): a slice is a view on genome, the network must not stay tied to it
        self.w1 = genome[:n1].reshape(self.w1.shape).copy()
        self.b1 = genome[n1:n2].copy()
        self.w2 = genome[n2:n3].reshape(self.w2.shape).copy()
        self.b2 = genome[n3:].copy()

    def randomize(self, rng, std=0.5):
        """Draws every weight and bias from a normal law (mean 0, standard deviation std)."""
        self.set_genome([rng.gauss(0, std) for _ in range(self.n_weights())])

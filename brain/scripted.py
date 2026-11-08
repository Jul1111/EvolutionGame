"""Hand-written controller, used as a reference point (profile `scripte`).

It answers one question: what does a simple, sensible policy score in this world? If evolved networks stay far
below it, the problem is the evolution (selection, mutation); if they reach it, the world or the sensors are the
limit. It is a floor of what is reachable, not the optimum.

Same interface as NeuralNetwork, with no weights: its genome is empty, so mutation and saving do nothing.
Expected inputs (profile `scripte`): food distance, food angle, can eat, poison distance, poison angle,
obstacle distance, obstacle angle.
"""
import numpy as np

from brain.network import NeuralNetwork


class ScriptedBrain(NeuralNetwork):
    def __init__(self, n_inputs, n_outputs):
        super().__init__(n_inputs, 0, n_outputs)

    def n_weights(self):
        return 0

    def get_genome(self):
        return np.zeros(0)

    def set_genome(self, genome):
        if len(genome):
            raise ValueError("Le cerveau scripté n'a pas de poids")

    def randomize(self, rng, std=0.5):
        pass

    def activations(self, inputs):
        food_d, food_a, can_eat, poison_d, poison_a, obst_d, obst_a = inputs[:7]
        # Speed command in [-1, 1] → target (command + 1) / 2 × max speed: -0.5 = 1.0, -0.6 = 0.8.
        # Slow on purpose: at speed 2 the energy spent (0.10 per tick) is more than the food found (08/11 test)
        turn, speed = 0.3, -0.5                       # Nothing to do: gentle curve at speed 1 (explores)
        if can_eat and food_d < 1.0:
            turn = float(np.clip(food_a * 8.0, -1, 1))  # Head for the food
            speed = -0.6 if food_d < 0.25 else -0.4     # Slow down when close, or it orbits
        if poison_d < 0.4 and abs(poison_a) < 0.35:
            turn = -1.0 if poison_a >= 0 else 1.0       # Poison ahead: turn away
        if obst_d < 0.15 and abs(obst_a) < 0.5:
            turn = -1.0 if obst_a >= 0 else 1.0         # Obstacle ahead: turn away
        return np.zeros(0), np.array([turn, speed])

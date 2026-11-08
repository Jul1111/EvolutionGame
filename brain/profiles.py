"""Network profiles (species): which sensors feed the network, what it controls, how many memory cells it has and how
wide its hidden layer is. Several profiles live in the same world at once (config.ACTIVE_PROFILES); every creature
carries the name of its profile, and each profile keeps its own population save and its own CSV.
To try another network, add an entry to PROFILES (sensors come from SENSORS)."""
import math
import os

import config
from brain.network import NeuralNetwork
from core.physics import normalize_angle



def _food(world, c, ctx):
    return world._direction(c, ctx["food"])


def _poison(world, c, ctx):
    if "poison" not in ctx:
        ctx["poison"] = world.nearest(c, world.poisons)[0]
    return world._direction(c, ctx["poison"])


def _obstacle(world, c, ctx):
    if "obstacle" not in ctx:
        ctx["obstacle"] = world.nearest(c, world.obstacles)[0]
    return world._direction(c, ctx["obstacle"])


def _energy(world, c, ctx):
    return [max(0.0, min(c.energy / config.ENERGY_INPUT_MAX, 1.0))]


def _speed(world, c, ctx):
    return [c.speed / config.CREATURE_MAX_SPEED]


def _can_eat(world, c, ctx):
    # 1.0 if a meal would fit (same rule as the food phase), else 0.0
    return [1.0 if c.energy + config.FOOD_ENERGY <= config.ENERGY_MAX else 0.0]


def _compass(world, c, ctx):
    return [math.cos(c.angle), math.sin(c.angle)]   # Heading in the world (the creature has no other way to know it)


def _touch(world, c, ctx):
    return [1.0 if c.touching else 0.0]   # Pushed against an obstacle at the last tick


# key → (labels, function(world, creature, ctx) → list of values). ctx caches what several sensors share.
SENSORS = {
    "food": (["Distance", "Angle"], _food),
    "energy": (["Énergie"], _energy),
    "speed": (["Vitesse"], _speed),
    "can_eat": (["Peut manger"], _can_eat),
    "poison": (["Dist. poison", "Angle poison"], _poison),
    "obstacle": (["Dist. obstacle", "Angle obstacle"], _obstacle),
    "compass": (["Cap cos", "Cap sin"], _compass),
    "touch": (["Contact"], _touch),
}

PROFILES = {
    # Simple networks. hidden = 0: inputs wired straight to the outputs. speed_output False: constant speed
    # (fixed_speed is an output value in [-1, 1], so 0.0 means half of the maximum speed).
    "chasseur": {"title": "Chasseur", "sensors": ["food"], "hidden": 0, "speed_output": True, "memory": 0,
                 "color": (255, 196, 77)},
    "chasseur_rassasie": {"title": "Chasseur rassasié", "sensors": ["food", "can_eat"], "hidden": 0,
                          "speed_output": True, "memory": 0, "color": (86, 180, 255)},
    "prudent": {"title": "Prudent (poison)", "sensors": ["food", "poison"], "hidden": 3, "speed_output": True,
                "memory": 0, "color": (255, 122, 168)},
    "vitesse_fixe": {"title": "Vitesse fixe", "sensors": ["food"], "hidden": 0, "speed_output": False,
                     "fixed_speed": 0.0, "memory": 0, "color": (150, 160, 255)},
}


def spec(name):
    return PROFILES[name]


def input_labels(name):
    p = PROFILES[name]
    return ([label for key in p["sensors"] for label in SENSORS[key][0]]
            + [f"Mémoire {i + 1}" for i in range(p["memory"])])


def output_labels(name):
    p = PROFILES[name]
    return (["Virage"] + (["Vit. cible"] if p["speed_output"] else [])
            + [f"Mémoire {i + 1}" for i in range(p["memory"])])


def new_brain(name):
    """Untrained network of the profile (weights at zero)."""
    p = PROFILES[name]
    return NeuralNetwork(len(input_labels(name)), p["hidden"], len(output_labels(name)))


def n_params(name):
    return new_brain(name).n_weights()


def paths(name):
    """(population file, CSV file) of a profile: one folder per profile in saves/profiles/."""
    folder = os.path.join(config.SAVE_DIR, "profiles", name)
    return os.path.join(folder, "latest.npz"), os.path.join(folder, "stats.csv")


def config_values(name):
    """What describes the network of a profile, for the CSV: {CONSTANT NAME: value}."""
    p = PROFILES[name]
    return {"NN_PROFILE": name, "NN_INPUTS": len(input_labels(name)), "NN_HIDDEN": p["hidden"],
            "NN_OUTPUTS": len(output_labels(name)), "SENSOR_KEYS": list(p["sensors"]), "MEMORY_CELLS": p["memory"],
            "SPEED_OUTPUT": p["speed_output"], "INPUT_LABELS": input_labels(name),
            "OUTPUT_LABELS": output_labels(name)}

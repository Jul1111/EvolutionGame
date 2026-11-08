"""Network profiles (species): which sensors feed the network, what it controls, how many memory cells it has and how
wide its hidden layer is. Several profiles live in the same world at once (config.ACTIVE_PROFILES); every creature
carries the name of its profile, and each profile keeps its own population save and its own CSV.

Adding a profile = one entry in PROFILES. Sensors come from core/sensors.py.
Keys: title, sensors, hidden (0 = inputs wired straight to the outputs), speed_output (False: constant speed,
fixed_speed is an output value in [-1, 1], 0.0 = half the maximum speed), memory (extra outputs fed back as
inputs), color, brain ("network" by default, "scripted" = hand-written controller, see brain/scripted.py).
"""
from brain.network import NeuralNetwork
from brain.scripted import ScriptedBrain
from core.sensors import SENSORS

PROFILES = {
    # The network of the runs that worked (100 generations, 08/11): 9 inputs, 6 hidden, 74 weights
    "complet": {"title": "Complet", "sensors": ["food", "energy", "speed", "can_eat", "poison", "obstacle"],
                "hidden": 6, "speed_output": True, "memory": 0, "color": (120, 224, 176)},
    "chasseur": {"title": "Chasseur", "sensors": ["food"], "hidden": 0, "speed_output": True, "memory": 0,
                 "color": (255, 196, 77)},
    "chasseur_rassasie": {"title": "Chasseur rassasié", "sensors": ["food", "can_eat"], "hidden": 0,
                          "speed_output": True, "memory": 0, "color": (86, 180, 255)},
    "prudent": {"title": "Prudent (poison)", "sensors": ["food", "poison"], "hidden": 3, "speed_output": True,
                "memory": 0, "color": (255, 122, 168)},
    "vitesse_fixe": {"title": "Vitesse fixe", "sensors": ["food"], "hidden": 0, "speed_output": False,
                     "fixed_speed": 0.0, "memory": 0, "color": (150, 160, 255)},
    # Reference point, not evolved: see brain/scripted.py
    "scripte": {"title": "Scripté (référence)", "sensors": ["food", "can_eat", "poison", "obstacle"], "hidden": 0,
                "speed_output": True, "memory": 0, "color": (200, 200, 200), "brain": "scripted"},
}


def spec(name):
    return PROFILES[name]


def input_labels(name):
    p = PROFILES[name]
    return ([label for key in p["sensors"] for label in SENSORS[key].labels]
            + [f"Mémoire {i + 1}" for i in range(p["memory"])])


def output_labels(name):
    p = PROFILES[name]
    return (["Virage"] + (["Vit. cible"] if p["speed_output"] else [])
            + [f"Mémoire {i + 1}" for i in range(p["memory"])])


def needed_items(names):
    """Item kinds (food, poison, obstacle...) whose nearest one must be computed each tick for these profiles.
    Food is always needed: it feeds the exploration metrics."""
    kinds = {"food"}
    for name in names:
        for key in PROFILES[name]["sensors"]:
            kinds |= SENSORS[key].needs
    return kinds


def new_brain(name):
    """Untrained brain of the profile (weights at zero)."""
    p = PROFILES[name]
    if p.get("brain") == "scripted":
        return ScriptedBrain(len(input_labels(name)), len(output_labels(name)))
    return NeuralNetwork(len(input_labels(name)), p["hidden"], len(output_labels(name)))


def n_params(name):
    return new_brain(name).n_weights()

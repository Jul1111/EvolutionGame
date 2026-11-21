"""The network of the selected creature as rows (side bar) and as nodes and links (graph views)."""
import pygame

from brain.profiles import input_labels, output_labels
from rendering.ui.draw import MINT, AMBER, CORAL, _lerp

# How each network input is displayed, by label: value → (text, signed bar?).
# A label that is not listed here is shown as a plain number with a plain bar.
INPUT_FORMAT = {
    "Distance": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle": lambda v: (f"{v:+.2f}", True),
    "Peut manger": lambda v: ("oui" if v >= 0.5 else "non", False),
    "Dist. poison": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle poison": lambda v: (f"{v:+.2f}", True),
    "Dist. obstacle": lambda v: ("rien en vue" if v >= 1.0 else f"{v:.2f}", False),
    "Angle obstacle": lambda v: (f"{v:+.2f}", True),
    "Contact": lambda v: ("oui" if v >= 0.5 else "non", False),
    "Cap cos": lambda v: (f"{v:+.2f}", True),
    "Cap sin": lambda v: (f"{v:+.2f}", True),
    **{f"Mémoire {i}": (lambda v: (f"{v:+.2f}", True)) for i in range(1, 9)},
}


def network_rows(inputs, outputs, profile):
    """Rows of the network panel: (label, text, value, signed bar?, colour), with the labels of the creature's
    profile."""
    rows = []
    for label, value in zip(input_labels(profile), inputs):
        value = float(value)
        text, signed = INPUT_FORMAT.get(label, lambda v: (f"{v:.2f}", False))(value)
        rows.append((label, text, value, signed, MINT))
    for label, value in zip(output_labels(profile), outputs):
        value = float(value)
        rows.append((label, f"{value:+.2f}", value, True, AMBER))
    return rows


def _node(surf, x, y, r, value):
    """Neuron: fill brightness = |activation|, mint if positive, coral if negative."""
    t = max(0.0, min(1.0, abs(value)))
    base = MINT if value >= 0 else CORAL
    pygame.draw.circle(surf, _lerp((38, 46, 54), base, t), (x, y), r)
    pygame.draw.circle(surf, (255, 255, 255, 80), (x, y), r, 1)


def _edge(surf, a, b, weight, source, wmax):
    """Link: colour = sign of the signal (weight x source activation), strength = size of that signal.
    A link carrying no signal stays faintly visible, according to the size of its weight."""
    signal = weight * source
    sign = signal if abs(signal) > 1e-3 else weight
    t = min(1.0, abs(signal))
    alpha = int(min(255, 22 + 190 * t + 40 * abs(weight) / wmax))
    color = (*(MINT if sign >= 0 else CORAL), alpha)
    pygame.draw.line(surf, color, a, b, 1 if t < 0.4 else 2)

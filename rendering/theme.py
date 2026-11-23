"""Colours and sizes of the interface. Not simulation settings: nothing here changes how the creatures live, so they
are not recorded in the run.json of an experiment."""

# World
DEAD_COLOR = (90, 90, 90)
FOOD_COLOR = (90, 200, 110)
FOOD_B_COLOR = (240, 210, 80)     # Second kind of food (FOOD_TYPES = 2): yellow, far from the green
PREDATOR_COLOR = (235, 60, 60)    # Crown of spikes of the predators (rendering/world/scene.py)
POISON_COLOR = (176, 96, 214)
OBSTACLE_COLOR = (92, 102, 112)

# Background and creatures (organic style)
BG_CENTER_COLOR = (30, 40, 46)       # Centre of the "petri dish" background
BG_EDGE_COLOR = (9, 11, 15)          # Darker vignette on the edges
ENERGY_LOW_COLOR = (222, 96, 78)     # Creature colour when energy is near 0
ENERGY_MID_COLOR = (240, 196, 92)
ENERGY_HIGH_COLOR = (120, 224, 176)  # Creature colour when energy is at ENERGY_INPUT_MAX
DEBUG_VISION_COLOR = (70, 120, 130)
DEBUG_LINK_COLOR = (150, 235, 200)
HUD_PANEL_COLOR = (25, 31, 37, 255)
SIDEBAR_BG_COLOR = (15, 18, 22)
PANEL_WIDTH = 320                    # Side bar on the right of the world view
HUD_LABEL_COLOR = (150, 165, 170)
HUD_VALUE_COLOR = (235, 240, 240)

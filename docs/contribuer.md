# Contribuer

## Ajouter une fonctionnalité

| Je veux ajouter... | Où |
|---|---|
| un capteur | une entrée dans `SENSORS` (`core/sensors.py`), puis le nommer dans un profil |
| une espèce / un réseau | une entrée dans `PROFILES` (`brain/profiles.py`) |
| un type d'objet perçu | une liste dans `World.items` (`core/world.py`) + un capteur `nearest_of("<type>")` |
| une règle de vie (naissance, mort) | `ContinuousSimulation` (`evolution/continuous.py`) |
| une mesure dans le temps | `ContinuousSimulation.sample` + `SAMPLE_HEADER`, puis une courbe dans `SERIES` (`rendering/hud.py`) |
| un réglage du menu | `PARAMS` de `main.py`, une ligne du menu Paramètres (`rendering/menu.py`), son aide (`PARAM_INFO`, `rendering/overlay.py`) |

Règle : un mécanisme à la fois, puis une expérience sur 4 graines au moins avant le suivant.


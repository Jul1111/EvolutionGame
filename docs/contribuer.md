# Contribuer

## Ajouter une fonctionnalité

| Je veux ajouter... | Où |
|---|---|
| un capteur | une entrée dans `SENSORS` (`core/sensors.py`), puis le nommer dans un profil |
| une espèce / un réseau | une entrée dans `PROFILES` (`brain/profiles.py`) |
| un type d'objet perçu | une liste dans `World.items` (`core/world.py`) + un capteur `nearest_of("<type>")` |
| une règle de vie (naissance, mort) | `ContinuousSimulation` (`evolution/continuous.py`) |
| une mesure dans le temps | `ContinuousSimulation.sample` + `SAMPLE_HEADER`, puis une courbe dans `SERIES` (`rendering/ui/hud.py`) |
| un réglage du menu | `PARAMS` de `app.py`, une ligne du menu Paramètres (`rendering/ui/menu.py`), son aide (`PARAM_INFO`, `rendering/ui/overlay/texts.py`) |

Règle : un mécanisme à la fois, puis une expérience sur 4 graines au moins avant le suivant.


## Réglages (`config`)

`World` et `ContinuousSimulation` lisent leurs réglages dans `self.cfg` (aussi `Creature`, les capteurs et le calcul par lot, via `world.cfg`), jamais dans le module `config`. Par défaut `cfg` est le module vivant, donc le jeu et les expériences n'ont rien changé. Pour simuler avec d'autres réglages, sans toucher au module : `ContinuousSimulation(rng, cfg=config.Settings(WORLD_SCALE=2, FOOD_COUNT=20))`. Dans le nouveau code de simulation, écrire `self.cfg.X` et non `config.X`.

Encore lus directement dans le module `config` : `rendering/`, `app.py`, `utils/`, `experiments/`, et les chemins de sauvegarde de `evolution/continuous.py`.

# Contribuer

## Ajouter une fonctionnalité

| Je veux ajouter... | Où |
|---|---|
| un capteur | une entrée dans `SENSORS` (`core/sensors.py`), puis le nommer dans un profil |
| une espèce / un réseau | une entrée dans `PROFILES` (`brain/profiles.py`) |
| un type d'objet perçu | une liste dans `World.items` (`core/world.py`) + un capteur `nearest_of("<type>")` |
| une règle de vie (naissance, mort) | `ContinuousSimulation` (`evolution/continuous.py`) |
| une mesure dans le temps | `ContinuousSimulation.sample` + `SAMPLE_HEADER`, puis une courbe dans `SERIES` (`rendering/ui/series.py`) |
| un réglage du menu | `PARAMS` de `app/settings.py`, une ligne du menu Paramètres (`rendering/ui/menu.py`), son aide (`PARAM_INFO`, `rendering/ui/overlay/texts.py`) |

Règle : un mécanisme à la fois, puis une expérience sur 4 graines au moins avant le suivant.


## Réglages (`config`)

Tout ce qui lit un réglage le reçoit en paramètre `cfg` : `World`, `ContinuousSimulation` (et, via `world.cfg`, `Creature`, les capteurs, le calcul par lot), `App`, `Scene`, `Hud`, `MiniMap`, `Display`, `PresetBrowser`, `load_settings` / `save_settings` et les chemins de sauvegarde. Par défaut `cfg` est le module `config` : le jeu et les scripts se comportent comme avant. Pour d'autres réglages, sans toucher au module :

```python
cfg = config.Settings(WORLD_SCALE=2, FOOD_COUNT=20)   # Copie, avec surcharges
sim = ContinuousSimulation(rng, cfg=cfg)
app = App(cfg)
```

`experiments/run.py` et `experiments/jardin.py` font ainsi : chaque graine a ses réglages, rien n'est partagé entre deux runs d'un même processus. Dans le code de simulation ou d'interface, écrire `self.cfg.X` (ou `world.cfg.X`), jamais `config.X`.

Les couleurs et la largeur du panneau latéral ne sont pas des réglages : elles sont dans `rendering/theme.py`. `layout.py` lit encore `SCREEN_WIDTH` et `SCREEN_HEIGHT` dans `config` : c'est l'unité fixe de la maquette de l'interface.

## Conventions

- **Langue.** Le code est en anglais : noms, commentaires, docstrings, messages d'erreur. Le français est pour ce que le joueur ou le lecteur voit : textes de l'interface (`rendering/ui/overlay/texts.py`, menus, bulles d'aide), documentation (`README.md`, `docs/`) et messages de commit.
- **Style.** `ruff check .` doit passer (lignes de 120 colonnes au plus). La CI le lance avant les tests. Pas de reformatage automatique du code existant.
- **Tests.** `python -m pytest` (environ 20 s) ; `--cov` ajoute la couverture, que la CI exige à 80 % minimum. Le rendu est testé sans écran (`SDL_VIDEODRIVER=dummy`, déjà réglé dans `tests/conftest.py`) : `tests/test_rendering.py` dessine tous les panneaux, vues et espèces. Un nouveau panneau ou une nouvelle vue s'y ajoute en quelques lignes.
- **Types.** `mypy .` (réglé dans `pyproject.toml`, passé par la CI).
- **Structure de `app/`.** `App` (`app/__init__.py`) assemble des composants qui reçoivent chacun ce dont ils ont besoin (`RunState` et `Selection` dans `app/state.py`, puis `MenuSettings`, `Session`, `Commands`, `Events`, `Frame`) : plus de mixins, ce qu'un composant lit ou écrit se voit dans son constructeur. Une nouvelle commande va dans `Commands._build`.
- **Structure de `rendering/ui/overlay/`.** Même principe : `Overlay` assemble des panneaux (`Toolbar`, `Legend`, `Help`, `NetworkPanel`, `ParamsPanel`, `Tips`) qui ont chacun leur état et reçoivent un `UiContext` (échelle, polices, zone libre, souris). Un nouveau panneau est une classe avec `draw()`, branchée dans `Overlay.draw()` ; s'il prend des clics, `Overlay.click()` les lui route.
- **Commits.** Un commit par modification, pour que l'historique se lise comme le journal du projet.

# EvolutionGame

Simulation en Python et pygame de l'évolution de créatures pilotées par un réseau de neurones.

But : faire tourner, un par un, les mécanismes qui ont façonné les êtres vivants (et l'humain), et voir ce qu'ils produisent. Une étape = un mécanisme = une question, vérifiée sur plusieurs graines.

Les créatures n'apprennent rien pendant leur vie. Il n'y a pas de générations ni de parents choisis : une créature qui mange assez fait un petit qui hérite de son réseau, avec une mutation. C'est de la sélection naturelle.

## Lancer le projet

Il faut Python 3.10 ou plus.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt   # numpy, pygame-ce, pytest
python main.py                   # le jeu
python -m pytest                 # les tests (moins de 10 s)
python -m experiments.run --name essai --seeds 1 2 3 4 --ticks 60000   # une expérience sans affichage
```

Au lancement, le terminal liste les réglages du menu qui remplacent `config.py` (`saves/settings.json`) et, s'il y en a une, la population reprise.

## Commandes

| Touche | Action |
|---|---|
| ↑ / ↓ | Vitesse de simulation (×1 à ×100) |
| Espace / → | Pause / avancer d'un tick (en pause) |
| Clic | Sélectionner une créature, ou utiliser les menus |
| Molette, glisser, + - 0 | Zoom (jusqu'à 4 fois plus loin que la carte entière : le tore apparaît répété, assombri, autour de la carte encadrée), déplacer la vue, toute la carte |
| V | Caméra sur la créature sélectionnée |
| B | Sélectionner la créature qui a eu le plus de petits |
| T | Suivre la lignée : à la mort de la sélection, passer à son plus jeune descendant vivant |
| S | Sauvegarder la population (`saves/populations/<date>_manuelle.npz`) |
| D, C, L | Debug (cône de vision et cibles), couleur des créatures, légende |
| G, N | Courbes, graphe du réseau (masqué, petit, grand) |
| P, H ou ?, F | Paramètres, aide, plein écran |
| Échap | Fermer, puis quitter le plein écran, puis quitter |

## Interface

- **Panneau Population** : vivantes sur le plafond de calcul, temps simulé, naissances et morts depuis le départ, génération de lignée moyenne et maximale. Statut «Extinction» quand tout le monde est mort.
- **Panneau Créature** : énergie, vitesse, âge, repas et poisons, temps aveugle, génération de lignée et nombre de petits.
- **Réseau** : entrées et sorties de la créature sélectionnée, en barres ou en graphe.
- **Courbes dans le temps** (menu Courbes) : une valeur toutes les 10 s simulées, lue dans `saves/timeline.csv`. Population, naissances, morts (faim, vieillesse), repas et poisons par 1000 ticks de vie, vitesse, énergie, génération de lignée, âge à la mort, nourriture disponible, naissances bloquées par le plafond.
- **Paramètres** (touche P) : mutation, seuil de reproduction, âge maximal, champ de vision, nourriture (nombre, énergie, délai, épuisement, positions), poison (nombre, dégâts), obstacles, taille du monde (1×1, 2×2 ou 3×3 écrans). Tout s'applique tout de suite, sauf les obstacles et la taille du monde (au prochain départ de zéro, marqués en orange). Nourriture, obstacles, fondateurs et plafond sont donnés par écran : un monde 2×2 en a 4 fois plus, et tourne environ 4 fois plus lentement. Les choix sont gardés dans `saves/settings.json`, qui ne contient que les écarts avec `config.py`.
- **Menu Réseau** : espèces des fondateurs, appliquées au prochain départ de zéro.
- **Menu Sauvegarde** : sauvegarder la population, charger la dernière sauvegardée, repartir de zéro (confirmation demandée).
- **Extinction** : la simulation se met en pause avec un message. Repartir de zéro ou charger une population.
- À la fermeture, la population est gardée (`saves/autosave.npz`) et reprise au lancement suivant (`LOAD_ON_START`). Après une extinction, il n'y a rien à garder.

## Comment ça marche

**Le monde.** Un tore de 1280 × 720 : ce qui sort d'un côté rentre de l'autre. 40 sources de nourriture, 5 poisons et 6 obstacles (valeurs par écran, `WORLD_SCALE` multiplie la surface).

**La nourriture.** Une nourriture mangée disparaît 60 ticks puis revient au même endroit. Après 3 repas, la source se déplace au hasard. Quand plusieurs créatures la touchent, la plus proche gagne. Une créature ne mange que si le repas rentre en entier sous le maximum d'énergie (200).

**Le poison.** La créature la plus proche qui le touche perd 40 d'énergie. Il réapparaît ensuite ailleurs.

**Les obstacles.** Disques, carrés ou triangles pleins (dessinés en anémones). On ne peut pas y entrer : la créature glisse le long, et dépense de l'énergie en poussant.

**L'énergie et le mouvement.** Coût par tick : 0,04 + 0,03 × vitesse. Vitesse de 0 à 4, qui change progressivement. Plus on va vite, moins on tourne.

**Le réseau** (espèce `complet`). 9 entrées → 6 neurones cachés → 2 sorties (virage, vitesse demandée), 74 poids. Entrées : distance et angle de la nourriture visible la plus proche, énergie, vitesse, «peut manger», distance et angle du poison, distance au bord et angle de l'obstacle. La vision est un cône de 120° et de portée 200. Pas de mémoire.

**La vie et la mort** (`evolution/continuous.py`).
1. Départ : 200 créatures aux réseaux tirés au hasard.
2. Une créature d'au moins 10 s qui a 120 d'énergie fait un petit (au plus un toutes les 5 s) : elle perd 60, le petit naît à côté avec 50 et hérite de son réseau plus un bruit gaussien (écart-type 0,1).
3. Mort de faim (énergie 0) ou de vieillesse (100 s).
4. Plafond de calcul : 400 créatures. Les naissances qu'il bloque sont comptées : si ce n'est pas 0, la population n'est plus réglée par la nourriture.
5. Une extinction arrête tout.

## Les espèces (profils de réseau)

Un profil dit quels capteurs alimentent le réseau, la taille de la couche cachée, si la vitesse est une sortie, et le nombre de cellules de mémoire. Plusieurs espèces peuvent partager le monde (menu Réseau).

| Profil | Entrées | Sorties | Poids |
|---|---|---|---|
| `complet` (défaut) | nourriture, énergie, vitesse, peut manger, poison, obstacle ; 6 cachés | virage, vitesse | 74 |
| `chasseur` | nourriture | virage, vitesse | 6 |
| `chasseur_rassasie` | nourriture + peut manger | virage, vitesse | 8 |
| `prudent` | nourriture + poison, 3 cachés | virage, vitesse | 23 |
| `vitesse_fixe` | nourriture | virage (vitesse fixe) | 3 |
| `scripte` | règles écrites à la main (`brain/scripted.py`), n'évolue pas : point de référence | virage, vitesse | 0 |

## Configuration

`config.py` est la seule référence. Le menu peut remplacer certaines valeurs (`saves/settings.json`, écarts seulement). Les expériences sans affichage ne lisent jamais `settings.json`. Les valeurs sont des valeurs de départ, réglées par des expériences notées dans les commentaires.

## Structure du projet

```
main.py                 Boucle pygame, événements, menus, sauvegardes (aucune règle de simulation)
config.py               Toutes les constantes (seule référence)
core/
  world.py              Monde : objets, déplacements, contacts (nourriture, poison), collisions
  sensors.py            Capteurs : un capteur = une entrée de SENSORS
  creature.py           Créature : mouvement, énergie, lignée, compteurs
  food.py, obstacle.py  Nourriture/poison, obstacles (géométrie)
  physics.py            Distances et angles sur le tore
brain/
  network.py            Réseau de neurones (génome = vecteur à plat)
  profiles.py           Espèces : capteurs, couche cachée, sorties
  scripted.py           Contrôleur écrit à la main (référence)
evolution/
  continuous.py         Naissances, morts, mesures (timeline.csv), sauvegarde d'une population
  mutation.py           Mutation gaussienne
experiments/
  run.py                Plusieurs graines en parallèle, résultats conservés
  summary.py            Résumé et comparaison d'expériences
  jardin.py             Jardin commun : mêmes génomes, conditions différentes
  gradient.py           Gradient de sélection : quel trait laisse le plus de petits
  results/              Résultats (CSV dans git, génomes ignorés)
rendering/              Tout l'affichage
utils/                  Réglages du menu, format du temps
tests/                  Tests (python -m pytest)
saves/                  Partie en cours : timeline.csv, autosave.npz, populations/ (ignoré par git)
```

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

## Expériences

```bash
python -m experiments.run --name <nom> --seeds 1 2 3 4 --ticks 120000 [--set FOOD_COUNT=30 MUTATION_STD=0.2]
python -m experiments.run --name suite --from-population saves/populations/<fichier>.npz
python -m experiments.summary experiments/results/<run A> experiments/results/<run B>
python -m experiments.jardin <population.npz> aleatoire --densities 30 280
python -m experiments.gradient experiments/results/<run>/seed_*/population_finale.npz
```

Chaque run écrit `experiments/results/<date>_<nom>/` : `run.json` (commande, commit, toutes les constantes), un `timeline.csv` par graine, `summary.csv` (moyenne et écart-type entre graines), et la population finale. Compter environ 7 min par graine pour 120 000 ticks sur 2 cœurs : lancer les longs runs depuis un terminal.

Deux expériences dont les intervalles (± écart-type) se recouvrent ne sont pas départagées : ajouter des graines avant de conclure.

## Résultats

### Évolution continue (08/11/2026)

- **Calibrage** : depuis des réseaux au hasard, seuil de reproduction 150 → extinction. Seuil 120 : 2 extinctions sur 8 graines avec 30 nourritures, 0 sur 8 avec 40.
- **Équilibre** (4 graines × 120 000 ticks) : 0 extinction. Goulot au départ (200 → 20-50), puis population stable vers 283 ± 18 à partir de 60 000-80 000 ticks, sans que le plafond serve. À l'équilibre, ~2 repas par 1000 ticks de vie, soit à peu près la dépense d'une créature lente : la nourriture règle la population.
- **Chute de la vitesse** (de 2-3 à ~0,4 à l'équilibre) :
  - Jardin commun (mêmes génomes évolués, sans naissances) : vitesse 1,1-1,5 à 30 créatures, 0,4-0,6 à 280. Les réseaux au hasard ne réagissent presque pas (1,54 contre 1,42). La chute est donc surtout un **comportement appris par l'évolution qui dépend de la densité** (plasticité), pas un ralentissement figé dans les gènes.
  - Gradient de sélection à l'équilibre (4 populations, ~1 500 morts chacune) : pas de lien simple entre lenteur et nombre de petits (rho moyen +0,07 ± 0,11). Les plus lents (vitesse ~0,1) et les plus rapides (~0,7-1) ont le moins de petits, les intermédiaires (0,2-0,5) le plus : forme de **sélection stabilisante**. Corrélation seulement : les plus lents sont peut-être lents parce qu'affaiblis.
  - Limites : 2 tirages par condition du jardin, une seule suite par population pour le gradient.

### Mode générations (supprimé le 08/11, historique)

Le monde durci (×2, 5 nourritures, 20 poisons à 80, 25 obstacles) avec une sélection sur l'âge d'abord menait au piège d'immobilité sur 4 graines sur 4. Dans le monde réparé (10 nourritures), l'évolution progressait sur 4 graines sur 4. Résultats dans `experiments/results/20261108_20*` (format de l'époque, lisible par `experiments.summary`).

## Limites connues

- Le réseau n'a pas de mémoire : quand rien n'est en vue, ses entrées sont constantes.
- Le corps n'évolue pas encore (prochaine étape : gène de taille).
- La simulation est lente au-delà de quelques centaines de créatures (réseaux calculés un par un).

## Pistes

Dans l'ordre : gène de taille avec son coût (et un témoin de dérive), reproduction à deux parents, environnement qui change, interactions (prédateurs, partage), signaux, apprentissage et transmission.

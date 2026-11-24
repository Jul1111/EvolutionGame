# EvolutionGame

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![pygame-ce](https://img.shields.io/badge/pygame--ce-2.5%2B-green)
![tests](https://img.shields.io/badge/tests-pytest-informational)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

Simulation de sélection naturelle en Python : des créatures pilotées par un petit réseau de neurones mangent, se reproduisent et meurent sur un monde torique. Rien n'est appris pendant la vie. Seule la reproduction avec mutation fait évoluer les comportements.

L'objectif : activer un mécanisme évolutif à la fois, et mesurer ce qu'il produit sur plusieurs graines.

## Fonctionnalités

- **Évolution continue** : pas de générations. Une créature assez nourrie fait un petit qui hérite de son réseau, muté.
- **Réseaux configurables** : plusieurs espèces (profils de capteurs et de couches) peuvent partager le monde.
- **Prédateurs** (facultatif) : une espèce qui ne mange que les autres créatures, avec ses capteurs et ses courbes.
- **Gène de taille** : coût métabolique selon la loi de Kleiber, modes `actif`, `neutre` ou `fixe`.
- **Interface pygame** : zoom, suivi de lignée, courbes, graphe du réseau, sauvegarde et reprise.
- **Expériences sans affichage** : runs multi-graines en parallèle, résultats reproductibles (commit et constantes enregistrés).

## Installation

```bash
git clone https://github.com/Jul1111/EvolutionGame.git
cd EvolutionGame
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Utilisation

```bash
python main.py          # lancer la simulation
python -m pytest        # tests (~ 20 s)
python -m pytest --cov  # + couverture (échoue sous 80 %)
mypy .                  # types (mode standard)
```

Lancer une expérience sans affichage :

```bash
python -m experiments.run --name essai --seeds 1 2 3 4 --ticks 120000
python -m experiments.summary experiments/results/<run>
python -m experiments.run --name cout --varie ENERGY_MOVE_COST=0.015,0.06   # un run par valeur, barre globale
python -m experiments.lot "--name a ..." "--name b ..."   # runs différents à la suite, barre globale
python -m experiments.progress --suivre   # barre d'avancement des lots et runs en cours
python -m experiments.pause            # pause des expériences en cours (reprise : python -m experiments.pause reprise)
```

Les résultats sont écrits dans `experiments/results/<date>_<nom>/`. Méthode, autres outils d'analyse et résultats obtenus : [docs/experiences.md](docs/experiences.md).

## Commandes

| Touche | Action |
|---|---|
| ↑ / ↓ | Vitesse de simulation (×1 à ×100) |
| Espace / → | Pause / tick suivant |
| Molette, glisser | Zoom, déplacement |
| V / B / T | Suivre la sélection / meilleur reproducteur / lignée |
| G / N | Courbes (panneau, puis grand) / graphe du réseau |
| Tab / M / E | Panneaux / mini-carte / naissances et morts |
| C | Couleur : espèce, énergie, vitesse, nourriture, taille, lignée |
| S | Sauvegarder la population |
| P / H | Paramètres / aide |

Liste complète et détail des menus : [docs/interface.md](docs/interface.md).

## Fonctionnement

| Élément | Règle |
|---|---|
| Monde | Tore 1280 × 720 (× `WORLD_SCALE`), nourriture, poisons, obstacles |
| Énergie | Coût par tick : 0,04 + 0,03 × vitesse |
| Cerveau | 9 entrées → 6 cachés → 2 sorties (virage, vitesse), vision en cône 120° |
| Reproduction | À 120 d'énergie : un petit à 50, mutation gaussienne (σ = 0,1) |
| Mort | Faim ou vieillesse (100 s) |

Toutes les constantes sont dans `config.py`. Règles détaillées, gène de taille et espèces : [docs/fonctionnement.md](docs/fonctionnement.md).

## Ce qu'on a appris

Résultats sur 8 à 16 graines par condition ; résumé par thème puis détails et limites dans [docs/experiences.md](docs/experiences.md) :

- **Le départ est un goulot** : sur 200 fondateurs au hasard, il en reste quelques dizaines. Avec 40 nourritures par écran, une graine sur deux s'éteignait ; avec 60 (`FOOD_COUNT`), aucune sur 24.
- **La nourriture règle la population** : environ 200 créatures par écran à l'équilibre. Le plafond de calcul (`POP_MAX`, 400 par écran) ne sert plus.
- **La vitesse est un comportement appris qui suit la nourriture** : à génomes égaux, une créature va deux fois plus vite avec 60 nourritures par écran qu'avec 15. Le nombre de voisins compte peu. Les lignées diffèrent beaucoup entre elles, et la sélection favorise les plus rapides.
- **Les duels d'espèces finissent presque toujours par l'élimination d'une des deux**, et aucune aide à explorer (faim, bruit, mémoire) ne bat l'espèce de base. Le vainqueur est écrit dès les fondateurs (même issue dans 37 rejeux sur 40) et dépend surtout de la lignée adverse ; la mémoire est même un handicap (44 duels sur 45 perdus en 2×2). Gagne la lignée qui fait vivre le plus de créatures avec la même nourriture (lente, économe) : les lignées rapides perdent presque tous leurs duels.
- **Coexistence par niches** : avec deux sortes de nourriture et un gène de régime (`FOOD_TYPES = 2`), deux espèces peuvent coexister durablement, chacune spécialisée sur une nourriture (45 % des graines avec des fondateurs spécialistes, sur 48 ; aucune avec une seule nourriture).
- **Une espèce peut se scinder** : avec une mutation du régime assez forte (0,15), une seule espèce se partage en autant de groupes de spécialistes qu'il y a de sortes de nourriture (2, 3, et 3 ou 4 avec 4 sortes), et en refait un quand il disparaît.
- **Une niche rare façonne le comportement** : si une nourriture est rare et riche et l'autre abondante et pauvre (même énergie au total), les spécialistes de la rare sont moins nombreux, plus lents, mangent moins souvent et choisissent leur nourriture par sa valeur plutôt que par sa distance.
- **Les prédateurs tiennent mal, mais façonnent les proies** : des créatures qui mangent les autres (`PREDATION`) s'éteignent presque toujours en 1×1 et dans 3 graines sur 4 en 2×2 ; un monde 3×3 n'aide pas, tout se joue juste après leur arrivée. Des prédateurs déjà évolués passent ce cap, mais mangent presque toutes les proies puis meurent de faim : leur efficacité déstabilise le système. Là où elles durent : cycles proies-prédateurs, proies qui fuient et vont deux fois plus vite, prédateurs qui accélèrent sur une proie en vue.
- **La complexité vient du temps, pas de la taille du cerveau** : sur un million de ticks, la non-linéarité des réseaux triple puis plafonne ; des réseaux 2 à 3 fois plus gros ne sont pas plus complexes.
- **Les réglages ne s'additionnent pas** : chacun pris seul reste vivable, mais combiner peu de nourriture, repousse lente et poison éteint tout. Quatre préréglages validés (Facile, Équitable, Dur, Compliqué, dossier `presets/`) sont proposés en tête du panneau Paramètres.

## Structure

```
main.py        Point d'entrée
app/           Boucle pygame, commandes, réglages (App assemble des composants : Session, Commands, Events, Frame...)
config.py      Constantes (seule référence)
core/          Monde, créatures, capteurs, physique
brain/         Réseau de neurones et profils d'espèces
evolution/     Naissances, morts, mutation
experiments/   Runs multi-graines et analyses
docs/          Documentation détaillée
rendering/     Affichage : world/ (scène, sprites), ui/ (HUD, menus), backend/ (processeur, carte graphique)
tests/         Tests pytest
```

## Feuille de route

- [x] Évolution continue par sélection naturelle
- [x] Gène de taille
- [x] Mesure de l'exploration, espèces faim / bruit / mémoire, duels d'espèces
- [x] Duels : quelle aide à explorer l'emporte ? Aucune : faim, bruit et mémoire ne battent pas `complet` (rejeux et duels croisés : faim et bruit neutres, mémoire handicapante), le vainqueur dépend surtout des lignées
- [ ] Étude du gène de taille (actif contre neutre)
- [ ] Reproduction à deux parents
- [ ] Environnement changeant
- [x] Prédation : espèce prédatrice, capteurs proie et prédateur, cycles, fuite et poursuite (coexistence durable encore rare)
- [ ] Signaux, apprentissage et transmission

## Contribuer

Un mécanisme à la fois, validé sur 4 graines minimum. Voir [docs/contribuer.md](docs/contribuer.md).

## Limites connues

- Mémoire seulement pour l'espèce `complet_memoire` (2 cellules), pas encore étudiée.
- Performances : un tick coûte ~1,1 ms en 1×1 (400 créatures) et ~2,2 ms en 2×2 (~1 350), grâce à une grille spatiale et à numba (facultatif : sans lui, mêmes résultats en numpy, environ deux fois plus lent). Détails : section « Optimisation du calcul » de [docs/experiences.md](docs/experiences.md).

## Licence

MIT. Voir [LICENSE](LICENSE).

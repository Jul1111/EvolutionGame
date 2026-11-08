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
python -m pytest        # tests (< 10 s)
```

Lancer une expérience sans affichage :

```bash
python -m experiments.run --name essai --seeds 1 2 3 4 --ticks 120000
python -m experiments.summary experiments/results/<run>
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

## Structure

```
main.py        Boucle pygame et interface
config.py      Constantes (seule référence)
core/          Monde, créatures, capteurs, physique
brain/         Réseau de neurones et profils d'espèces
evolution/     Naissances, morts, mutation
experiments/   Runs multi-graines et analyses
docs/          Documentation détaillée
rendering/     Affichage et menus
tests/         Tests pytest
```

## Feuille de route

- [x] Évolution continue par sélection naturelle
- [x] Gène de taille
- [x] Mesure de l'exploration, espèces faim / bruit / mémoire, duels d'espèces
- [ ] Duels : quelle aide à explorer l'emporte ?
- [ ] Étude du gène de taille (actif contre neutre)
- [ ] Reproduction à deux parents
- [ ] Environnement changeant
- [ ] Prédation et interactions
- [ ] Signaux, apprentissage et transmission

## Contribuer

Un mécanisme à la fois, validé sur 4 graines minimum. Voir [docs/contribuer.md](docs/contribuer.md).

## Limites connues

- Mémoire seulement pour l'espèce `complet_memoire` (2 cellules), pas encore étudiée.
- Performances limitées au-delà de quelques centaines de créatures.

## Licence

MIT. Voir [LICENSE](LICENSE).

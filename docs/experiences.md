# Expériences et résultats

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


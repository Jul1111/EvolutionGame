# Expériences et résultats

## Expériences

```bash
python -m experiments.run --name <nom> --seeds 1 2 3 4 --ticks 120000 [--set FOOD_COUNT=30 MUTATION_STD=0.2]
python -m experiments.run --name suite --from-population saves/populations/<fichier>.npz
python -m experiments.summary experiments/results/<run A> experiments/results/<run B>
python -m experiments.jardin <population.npz> aleatoire --densities 30 280
python -m experiments.gradient experiments/results/<run>/seed_*/population_finale.npz
```

Chaque run écrit `experiments/results/<date>_<nom>/` : `run.json` (commande, commit, toutes les constantes), un `timeline.csv` par graine, `summary.csv` (moyenne et écart-type entre graines), et la population finale. Les `run.json` et les CSV sont versionnés dans git (de quoi retrouver les chiffres cités ici) ; les populations finales `.npz` ne le sont pas, à garder à part si une expérience doit être rejouée à partir d'elles. Compter environ 7 min par graine pour 120 000 ticks sur 2 cœurs : lancer les longs runs depuis un terminal.

Deux expériences dont les intervalles (± écart-type) se recouvrent ne sont pas départagées : ajouter des graines avant de conclure.

## Résultats

### Évolution continue (08/11/2026)

- **Calibrage** : depuis des réseaux au hasard, seuil de reproduction 150 → extinction. Seuil 120 : 2 extinctions sur 8 graines avec 30 nourritures, 0 sur 8 avec 40.
- **Équilibre** (4 graines × 120 000 ticks) : 0 extinction. Goulot au départ (200 → 20-50), puis population stable vers 283 ± 18 à partir de 60 000-80 000 ticks, sans que le plafond serve. À l'équilibre, ~2 repas par 1000 ticks de vie, soit à peu près la dépense d'une créature lente : la nourriture règle la population.
- **Chute de la vitesse** (de 2-3 à ~0,4 à l'équilibre) :
  - Jardin commun (mêmes génomes évolués, sans naissances) : vitesse 1,1-1,5 à 30 créatures, 0,4-0,6 à 280. Les réseaux au hasard ne réagissent presque pas (1,54 contre 1,42). La chute est donc surtout un **comportement appris par l'évolution qui dépend de la densité** (plasticité), pas un ralentissement figé dans les gènes.
  - Gradient de sélection à l'équilibre (4 populations, ~1 500 morts chacune) : pas de lien simple entre lenteur et nombre de petits (rho moyen +0,07 ± 0,11). Les plus lents (vitesse ~0,1) et les plus rapides (~0,7-1) ont le moins de petits, les intermédiaires (0,2-0,5) le plus : forme de **sélection stabilisante**. Corrélation seulement : les plus lents sont peut-être lents parce qu'affaiblis.
  - Limites : 2 tirages par condition du jardin, une seule suite par population pour le gradient.

### Équilibre avec la nourriture qui suit la population (22/11/2026)

Même protocole que l'équilibre du 08/11 (4 graines × 120 000 ticks, réglages de `config.py`), avec le code actuel : `experiments/results/20261122_013320_equilibre_refonte`.

- **2 extinctions sur 4** (graines 1 et 2, aux ticks 8 064 et 7 186), contre 0 sur 4 le 08/11. Dans la timeline, les naissances restent à 0-1 par relevé pendant des milliers de ticks après le départ : le goulot du début ne se referme pas. Les graines 3 et 4 passent le goulot.
- **Graines survivantes (2)** : population 181 ± 8 (283 ± 18 le 08/11), vitesse moyenne 1,15 ± 0,25 (0,41 ± 0,15), âge moyen à la mort 2 023 ticks (2 949). Le 08/11 la vitesse tombait à ~0,4 à l'équilibre ; ici elle reste plus haute et la population plus basse.
- **Ce n'est pas dû au rangement du code** : le même run sur le dernier commit d'avant les refactorings (`b2ba45a`, « Nourriture qui suit la population ») donne exactement les mêmes chiffres, mêmes ticks d'extinction compris. L'écart avec le 08/11 vient donc de ce changement de règle de nourriture (et du calcul par lot du 09/11), pas du refactoring.
- **Limites** : 2 graines survivantes seulement, donc aucune conclusion sur la vitesse ou la population d'équilibre ; une seule configuration testée. À faire : refaire le calibrage du goulot (nourriture au départ, seuil de reproduction) avec 8 graines ou plus avant de toucher aux réglages.

### Mode générations (supprimé le 08/11, historique)

Le monde durci (×2, 5 nourritures, 20 poisons à 80, 25 obstacles) avec une sélection sur l'âge d'abord menait au piège d'immobilité sur 4 graines sur 4. Dans le monde réparé (10 nourritures), l'évolution progressait sur 4 graines sur 4. Résultats dans `experiments/results/20261108_20*` (format de l'époque, lisible par `experiments.summary`).


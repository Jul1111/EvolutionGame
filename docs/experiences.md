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

### Calibrage du goulot de départ (22/11/2026)

Question : quel réglage fait passer le goulot du départ (200 fondateurs au hasard → quelques dizaines) sans dérégler l'équilibre ? Mêmes graines 1 à 8 pour toutes les variantes (comparaison appariée), un réglage changé à la fois. Résultats : `experiments/results/20261122_01*_calib_*`.

**Balayage, 8 graines × 30 000 ticks** (les extinctions arrivent toutes avant 25 000 ticks) :

| Variante | Extinctions |
|---|---|
| actuelle (`FOOD_COUNT=40`, `FOOD_ENERGY=30`, seuil 120) | 4/8 |
| `FOOD_COUNT=60` | 0/8 |
| `FOOD_ENERGY=45` | 0/8 |
| `FOOD_COUNT=60`, `FOOD_COUNT_MIN=25` | 0/8 |
| `INITIAL_POPULATION=300` | 1/8 |
| `REPRO_THRESHOLD=100` | 1/8 |
| `REPRO_THRESHOLD=110` | 2/8 |
| `MATURITY_AGE=300` | 2/8 |
| `FOOD_RESPAWN_DELAY=30` | 3/8 |

Seule la quantité de nourriture fait une différence nette. Les autres (1 à 3 sur 8 contre 4 sur 8) ne se distinguent pas de la référence à 8 graines.

**Équilibre, 8 graines × 120 000 ticks** (moyenne des 10 derniers relevés des graines survivantes, ± écart-type entre graines) :

| Variante | Extinctions | Population | Vitesse | Repas / 1000 ticks | Âge à la mort |
|---|---|---|---|---|---|
| actuelle | 4/8 | 180 ± 6 | 1,19 ± 0,15 | 1,67 | 1 962 |
| `FOOD_COUNT=60` | 0/8 | 204 ± 27 | 1,49 ± 1,03 | 1,81 | 1 890 |
| `FOOD_ENERGY=45` | 0/8 | 231 ± 12 | 1,01 ± 0,24 | 1,10 | 1 842 |

- `FOOD_COUNT=60` ne change que la nourriture des petites populations (le départ, l'après-effondrement) : le plancher reste à 15 par écran. L'équilibre bouge peu (+13 % de population). Une graine (la 2) part sur une autre stratégie : 142 créatures à vitesse ~3,9, contre ~1 pour les autres, d'où le grand écart-type de la vitesse.
- `FOOD_ENERGY=45` change toute la partie (chaque repas vaut 50 % de plus) : population plus haute (+28 %) et homogène, moins de repas nécessaires.
- Le plafond (400) ne bloque aucune naissance dans les trois cas.
- **Limites** : 8 graines, une seule valeur testée par levier, pas de combinaison. 0/8 n'exclut pas un taux d'extinction de quelques pour cent.
- **Retenu** : `FOOD_COUNT = 60` dans `config.py` (le changement le plus ciblé : il ne touche pas le plancher).

### Goulot dans une partie réelle : monde 2×2, duel d'espèces (22/11/2026)

Vérification du calibrage hors du cadre où il a été fait : réglages d'une partie jouée (`WORLD_SCALE=2`, `VISION_FOV_DEGREES=60`, espèces `complet` et `complet_faim`), 8 graines × 120 000 ticks. Résultats : `experiments/results/20261122_02*_mes_reglages_*`.

| `FOOD_COUNT` | Extinctions | Population | Naissances bloquées par le plafond | `complet_faim` éteinte |
|---|---|---|---|---|
| 40 | 4/8 (ticks 9 300 à 18 900) | 400 | ~33 000 par graine | 8/8 |
| 60 | 0/8 | 400 | ~40 000 par graine | 5/8 |

- Le goulot se comporte comme dans le monde 1×1 : 4 sur 8 à 40, 0 sur 8 à 60. Le calibrage tient dans ce cadre.
- **À l'équilibre, le plafond `POP_MAX` (400) limite la population, pas la nourriture** : toutes les graines survivantes sont à 400, et des dizaines de milliers de naissances sont refusées. Dans un monde 2×2, la nourriture est 4 fois plus abondante mais le plafond ne change pas.
- **Duel** : dans chaque graine, une espèce finit par occuper tout le monde. Avec `FOOD_COUNT=60`, `complet` gagne 5 graines sur 8 et `complet_faim` 3 sur 8 : pas de vainqueur net à 8 graines.
- **Limites** : un seul cadre de partie ; le plafond fausse toute mesure de l'équilibre (population, vitesse) dans ce monde.

### Plafond proportionnel à la surface du monde (22/11/2026)

Même partie (2×2, 60°, `complet` + `complet_faim`, `FOOD_COUNT=60`) avec `POP_MAX=1600`, soit 400 × 4 écrans : ce que donnerait un plafond qui grandit avec le monde. 8 graines × 120 000 ticks. Résultats : `experiments/results/20261122_121405_mes_reglages_plafond1600`.

| Plafond | Extinctions | Population (10 derniers relevés) | Maximum atteint | Naissances refusées | Temps par graine |
|---|---|---|---|---|---|
| 400 | 0/8 | 400 | 400 | ~40 000 | ~720 s |
| 1 600 | 0/8 | 444 ± 29 | 438 à 505 | 0 | ~720 s |

- **La nourriture reprend la main** : sans plafond qui bloque, la population se fixe vers 440, bien en dessous de 1 600. Le plafond à 400 ne retenait que de peu une population qui en voulait ~10 % de plus.
- **Pourquoi pas ~4 × 200** : `FOOD_PRESSURE_POP` (300) compte les créatures du monde entier, sans tenir compte de sa taille. Dès 300 créatures nées, un monde 2×2 descend au plancher (15 par écran), comme un monde 1×1. La population d'un grand monde est donc tenue par cette règle, pas par la surface.
- **Coût** : aucun dans ce cadre, le temps de calcul ne bouge pas (la population ne monte que de 10 %).
- Le duel donne la même répartition qu'avec le plafond à 400 (`complet` 5 graines sur 8).
- **Limites** : un seul monde (2×2) ; en 3×3, le plafond proportionnel vaudrait 3 600, jamais testé.

### Plafond et pression de nourriture par écran (22/11/2026)

Après le passage de `POP_MAX` et `FOOD_PRESSURE_POP` en valeurs par écran (`POP_CAP`, `FOOD_PRESSURE`), même partie (2×2, 60°, `complet` + `complet_faim`), 8 graines × 120 000 ticks. Résultats : `experiments/results/20261122_123117_mes_reglages_tout_par_ecran`.

| Règle | Extinctions | Population | Naissances refusées | Temps par graine | Coût d'un tick (1 processus) |
|---|---|---|---|---|---|
| plafond 400, pression 300 (avant) | 0/8 | 400 | ~40 000 | ~720 s | ~6 ms |
| plafond 1 600, pression 300 | 0/8 | 444 ± 29 | 0 | ~720 s | ~6 ms |
| plafond 1 600, pression 1 200 (actuel) | 0/8 | 895 ± 13 | 0 | ~1 950 s | ~17,5 ms |

- **Densité indépendante de la taille du monde** : 895 créatures sur 4 écrans, soit ~224 par écran, comme un monde 1×1 (204 ± 27). Le plafond n'est jamais atteint.
- **Duel** : `complet` l'emporte dans 7 graines sur 8 (5 sur 8 avec l'ancienne règle) ; `complet_faim` s'éteint dans 7.
- **Coût** : un tick coûte ~17,5 ms à 900 créatures (~24 ms à 1 600), contre ~6 ms à 400. C'est plus qu'une image à 60 i/s : dans le jeu, un monde 2×2 à l'équilibre tourne sous 60 images par seconde même en vitesse ×1, et les vitesses supérieures ne vont pas plus vite.
- **Limites** : coût mesuré sur une seule machine (8 cœurs, un processus par graine) ; 3×3 non testé (densité attendue ~2 000 créatures).
- **Retenu** : la pression de nourriture redevient un nombre pour le monde entier (`FOOD_PRESSURE_POP = 300`), le plafond reste par écran : un 2×2 se fixe vers 440 créatures, à ~6 ms par tick.

### Mode générations (supprimé le 08/11, historique)

Le monde durci (×2, 5 nourritures, 20 poisons à 80, 25 obstacles) avec une sélection sur l'âge d'abord menait au piège d'immobilité sur 4 graines sur 4. Dans le monde réparé (10 nourritures), l'évolution progressait sur 4 graines sur 4. Résultats dans `experiments/results/20261108_20*` (format de l'époque, lisible par `experiments.summary`).


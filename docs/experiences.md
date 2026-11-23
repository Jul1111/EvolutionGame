# Expériences et résultats

## Expériences

```bash
python -m experiments.run --name <nom> --seeds 1 2 3 4 --ticks 120000 [--set FOOD_COUNT=30 MUTATION_STD=0.2]
python -m experiments.run --name suite --from-population saves/populations/<fichier>.npz
python -m experiments.summary experiments/results/<run A> experiments/results/<run B>
python -m experiments.jardin <population.npz> aleatoire --densities 30 280
python -m experiments.gradient experiments/results/<run>/seed_*/population_finale.npz
python -m experiments.run ... --replica 1         # mêmes fondateurs, autre hasard du monde
python -m experiments.run ... --shift 1 --from-population <A>/seed_{seed}/... <B>/seed_{pair}/...   # duels croisés
python -m experiments.pause [reprise|etat]        # mettre en pause / reprendre les expériences en cours
python -m experiments.progress [--suivre]         # barre d'avancement des lots et runs en cours
python -m experiments.run --name cout --varie ENERGY_MOVE_COST=0.015,0.03,0.06   # 3 runs à la suite
python -m experiments.lot "--name a ..." "--name b ... {run:a}/seed_{seed}/population_finale.npz"   # runs différents
```

**Plusieurs runs d'une seule commande**, sans fichier : `--varie NOM=V1,V2,...` fait un run par valeur (`cout_0.015`, `cout_0.03`...), `--replica 1 2` et `--shift 0 1 2` un run par valeur (`_r1`, `_s0`...) ; plusieurs à la fois : toutes les combinaisons. Pour des runs qui diffèrent autrement (autres espèces, un run qui part des populations d'un autre) : `experiments.lot` avec un run entre guillemets par argument, ou un fichier texte d'une ligne par run (`experiments/lots/exemple.txt`). Dans les deux cas : barre globale puis une barre par run.

**Lots** : des runs entre guillemets, ou un fichier texte d'une ligne par run (les arguments de `experiments.run`, `#` pour un commentaire, `\` en fin de ligne pour continuer). `{run:NOM}` est remplacé par le dossier de résultats du run `NOM` du même lot, pour partir des populations d'un run précédent. Tout le lot est vérifié avant le premier run (une faute de frappe ne tombe pas après des heures). Le plan va dans `experiments/results/lots/<date>_<fichier>.json`, la sortie des runs dans le `.log` à côté. Un run en échec arrête le lot. Affichage :

```
Lot exemple  [########------------]  38 %   1/3 runs  9 min 12, reste ~15 min 01
  seul_complet       [####################] 100 %   4/4 graines  6 min 40
  seul_complet_faim  [#######-------------]  33 %   0/4 graines  2 min 32, reste ~5 min 04
  duel_evolues       [--------------------]   0 %  en attente
```

La barre globale pèse chaque run par son coût estimé (graines × ticks × surface du monde) : un run en 2×2 compte 4 fois un run en 1×1.

**Avancement** : `experiments.run` affiche une barre pendant qu'il tourne (`[###############-----]  75 %  12/16 graines  6 min 10, reste ~2 min 03`), redessinée sur place dans un terminal, une ligne tous les 10 % dans un fichier de log. Pour un run lancé ailleurs (en fond, autre terminal) : `python -m experiments.progress` montre les lots en cours (barre globale, puis une barre par run) et les runs lancés seuls, `--suivre` la redessine toutes les 5 s en haut de l'écran (lignes coupées à la largeur du terminal). Elle est lue sur le disque (dernière ligne de `timeline.csv` de chaque graine) : précise à `SAMPLE_TICKS` près, et le temps restant compte aussi les pauses.

**Pause** : `python -m experiments.pause` arrête net toutes les expériences en cours et leurs processus de graines (plus aucun calcul), `python -m experiments.pause reprise` les relance exactement où elles étaient (mêmes résultats que sans pause), `etat` les liste. Une pause ne survit pas à l'extinction ou au redémarrage de l'ordinateur : le run en cours est alors perdu (les graines déjà finies restent sur le disque).

Chaque run écrit `experiments/results/<date>_<nom>/` : `run.json` (commande, commit, toutes les constantes), un `timeline.csv` par graine, `summary.csv` (moyenne et écart-type entre graines), et la population finale. Les `run.json` et les CSV sont versionnés dans git (de quoi retrouver les chiffres cités ici) ; les populations finales `.npz` ne le sont pas, à garder à part si une expérience doit être rejouée à partir d'elles. Durée d'une graine de 120 000 ticks (8 graines en parallèle sur 8 cœurs), avant l'optimisation du 23/11 : ~2 min en 1×1, ~12 min en 2×2 ; ~7 min en 1×1 sur 2 cœurs. Depuis, environ 4 fois moins en 2×2 (section « Coût du calcul »). Lancer les longs runs depuis un terminal.

`experiments.jardin` et `experiments.gradient` reprennent une population dans le monde de son run : toutes les valeurs de son `run.json` (le jardin ne change que la densité, sans naissances ni vieillesse). Une population sans `run.json` (sauvegardée depuis le jeu) prend `config.py`. Le script affiche la source des réglages utilisée. Avant le 22/11, ils prenaient toujours `config.py`.

Deux expériences dont les intervalles (± écart-type) se recouvrent ne sont pas départagées : ajouter des graines avant de conclure.

## Résultats

### État actuel (22/11/2026)

Réglages de `config.py` : `FOOD_COUNT = 60` (nourriture des petites populations), `FOOD_COUNT_MIN = 15`, `FOOD_PRESSURE_POP = 300` créatures nées pour le monde entier, `POP_MAX = 400` par écran (`POP_CAP`). Détails et protocoles dans les sections datées ci-dessous.

| Cadre | Extinctions | Population à l'équilibre | Vitesse moyenne | Coût d'un tick |
|---|---|---|---|---|
| 1×1, une espèce (`complet`) | 0/8 | 204 ± 27 | 1,49 ± 1,03 (une graine à ~3,9, les autres ~1) | ~1,4 ms |
| 2×2, 60°, `complet` + `complet_faim` | 0/16 | 440 ± 27 | 0,77 ± 0,08 | ~7,4 ms |

- Coût d'un tick : chiffres d'avant l'optimisation du 23/11 ; depuis, environ 4 fois moins en 2×2 (section « Optimisation du calcul »).
- Le goulot de départ est passé dans 24 graines sur 24 (8 en 1×1, 16 en 2×2), contre 8 sur 16 avec `FOOD_COUNT = 40`.
- Le plafond ne bloque plus de naissances ; c'est la nourriture qui règle la population.
- Duels de populations évoluées (1×1) : une fois les fondateurs choisis, l'issue ne dépend presque pas du hasard du monde (même vainqueur dans 37 rejeux sur 40). En duels croisés (chaque lignée contre 4 adversaires), la qualité de la lignée adverse prédit 81 à 91 % des issues. Faim et bruit : aucun effet d'espèce. Mémoire : vrai handicap (13 lignées mémoire sur 16 perdent en majorité contre des `complet` variés, p = 0,02), bien que les réseaux s'en servent (la couper coûte 3 % de population et fait perdre les duels plus vite). Ce qui gagne : la population qu'une lignée tient seule (79 % des duels) ; les lignées rapides perdent presque tout. **Confirmé en 2×2 à 60° (réglages de la partie)** : `complet` gagne 44 duels tranchés sur 45 contre la mémoire, les 16 lignées mémoire perdent en majorité.
- **Carte des réglages** (section « Carte des réglages et préréglages ») : la nourriture décide de la survie, la vision et la mutation de la complexité des réseaux ; aucun réglage ne fait coexister deux espèces durablement, l'abondance retarde seulement l'élimination. Combinés, les réglages durs s'additionnent jusqu'à l'extinction : quatre préréglages validés (Facile, Équitable, Dur, Compliqué) sont dans `presets/`.
- Duel en 2×2 (16 graines) : `complet` l'emporte 10 fois, `complet_faim` 6 fois. Écart compatible avec le hasard (p = 0,45) : le capteur de faim ne donne ni avantage ni handicap mesurable. Il n'est pas cassé, mais il vaut presque toujours ~0 : son échelle (600 ticks) est 50 fois plus longue que les moments typiques sans nourriture en vue. Avec une échelle de 60 ticks, l'entrée varie et le réseau s'en sert un peu (couper le capteur coûte ~2,5 % de population), mais le duel reste à 9 contre 6 (et une graine où les deux coexistent) : l'avantage est trop petit face au hasard du départ. Une espèce élimine toujours l'autre, entre 6 000 et 70 000 ticks.
- **Vitesse** (revérifiée le 22/11, section « La vitesse avec les règles actuelles ») : la conclusion du 08/11 ne tient plus. C'est la quantité de nourriture qui règle la vitesse (×2 de 15 à 60 nourritures par écran, à densité égale), la densité ne la baisse que de 6 à 18 %. Les lignées diffèrent beaucoup entre elles (0,5 à 4), et la sélection favorise les plus rapides (rho +0,27 ± 0,19, positif dans les 8 populations) au lieu des intermédiaires.

### Évolution continue, ancienne règle de nourriture (08/11/2026, historique)

Ces chiffres datent d'avant « la nourriture qui suit la population » (21/11), le calcul par lot (09/11), `FOOD_COUNT = 60` et le plafond par écran (22/11) : ils décrivent un autre réglage du monde. Avec la règle actuelle, la population d'équilibre en 1×1 est ~204 (pas 283) et la vitesse reste ~1 (pas ~0,4).

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
| 40 | 4/8 (ticks 9 300 à 18 900) | 400 | ~33 000 par graine | 4 sur les 4 survivantes |
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
| plafond 1 600, pression 300 (retenu) | 0/8 | 444 ± 29 | 0 | ~720 s | ~6 ms |
| plafond 1 600, pression 1 200 (essayé, annulé) | 0/8 | 895 ± 13 | 0 | ~1 950 s | ~17,5 ms |

- **Densité indépendante de la taille du monde** : 895 créatures sur 4 écrans, soit ~224 par écran, comme un monde 1×1 (204 ± 27). Le plafond n'est jamais atteint.
- **Duel** : `complet` l'emporte dans 7 graines sur 8 (5 sur 8 avec l'ancienne règle) ; `complet_faim` s'éteint dans 7.
- **Coût** : un tick coûte ~17,5 ms à 900 créatures (~24 ms à 1 600), contre ~6 ms à 400. C'est plus qu'une image à 60 i/s : dans le jeu, un monde 2×2 à l'équilibre tourne sous 60 images par seconde même en vitesse ×1, et les vitesses supérieures ne vont pas plus vite.
- **Limites** : coût mesuré sur une seule machine (8 cœurs, un processus par graine) ; 3×3 non testé (densité attendue ~2 000 créatures).
- **Retenu** : la pression de nourriture redevient un nombre pour le monde entier (`FOOD_PRESSURE_POP = 300`), le plafond reste par écran : un 2×2 se fixe vers 440 créatures, à ~6 ms par tick.

### La vitesse avec les règles actuelles (22/11/2026)

Même protocole que le 08/11 (jardin commun, puis gradient de sélection), sur les 8 populations finales de `calib_long_nourr60` (1×1, une espèce, `FOOD_COUNT=60`, 120 000 ticks). Jardin et gradient les reprennent dans le monde de leur run (`run.json`). Sorties brutes : `experiments/results/20261122_014718_calib_long_nourr60/vitesse_jardin_gradient.txt`.

**Jardin commun** (mêmes génomes, sans naissances ni vieillesse, nourriture fixe à 60 par écran : les créatures chargées ne comptent pas dans la pression ; 3 tirages par condition, 3 000 ticks, mesure après 600) :

| Population | Vitesse à 30 | à 200 | à 280 | Écart 30 → 280 | Vitesse dans son run à l'équilibre |
|---|---|---|---|---|---|
| 1 | 2,37 | 2,00 | 1,79 | −24 % | 1,12 |
| 2 | 3,98 | 3,98 | 3,99 | 0 (vitesse max : 4) | 3,94 |
| 3 | 1,20 | 1,25 | 1,24 | 0 | 1,00 |
| 4 | 2,03 | 1,79 | 1,66 | −18 % | 1,07 |
| 5 | 2,68 | 2,41 | 2,24 | −16 % | 1,26 |
| 6 | 3,13 | 2,94 | 2,70 | −14 % | 1,69 |
| 7 | 0,54 | 0,55 | 0,54 | 0 | 0,71 |
| 8 | 2,20 | 2,06 | 1,88 | −15 % | 1,14 |
| au hasard | 1,52 | 1,60 | 1,62 | +7 % | |

- **Peu de plasticité liée à la densité** : 5 populations sur 8 ralentissent de 14 à 24 % quand la densité passe de 30 à 280, les 3 autres pas du tout. Le 08/11 c'était −60 % environ (1,1-1,5 → 0,4-0,6). Les génomes au hasard ne réagissent pas, comme alors.
- **Les lignées diffèrent beaucoup** : de 0,5 à 4 à densité égale. La vitesse dépend surtout de la lignée qui a gagné dans la graine, plus que des conditions.
- **Piste** : à densité égale (~200), les populations vont nettement plus vite dans le jardin (nourriture à 60) que dans leur run à l'équilibre (nourriture vers 28 par écran à ~210 créatures nées), par exemple 2,00 contre 1,12. Testée et confirmée ci-dessous (« Jardin à nourriture variable »).

**Jardin à nourriture variable** (mêmes populations, `--set FOOD_COUNT` à 15, 30 ou 60 par écran, densité 30 ou 200, 3 tirages ; sorties brutes : `experiments/results/20261122_014718_calib_long_nourr60/jardin_nourriture.txt`). Moyenne des populations 1, 3 à 8 (la 2 est collée à la vitesse maximale 4 dans toutes les conditions) :

| Nourriture par écran | Vitesse à 30 créatures | à 200 | Effet de la densité (30 → 200) | Repas / 1000 ticks à 200 |
|---|---|---|---|---|
| 15 | 1,09 | 0,86 | −16 % | 0,87 |
| 30 | 1,56 | 1,25 | −18 % | 1,43 |
| 60 | 2,02 | 1,86 | −6 % | 1,91 |
| génomes au hasard, 15 → 60 (à 200) | | 1,14 → 1,60 | | 0,34 → 1,37 |

- **La quantité de nourriture règle la vitesse** : de 15 à 60 nourritures par écran, à densité 200, la vitesse est multipliée par 1,8 à 2,4 selon la population (moyenne 0,86 → 1,86). La densité, à nourriture égale, ne la baisse que de 6 à 18 % en moyenne.
- **C'est appris** : les génomes au hasard ne gagnent que +40 % de vitesse dans les mêmes conditions (leurs entrées changent quand plus de nourriture est en vue), les génomes évolués +115 %.
- **Cohérent avec les runs** : à l'équilibre d'un run, la nourriture est vers 28 par écran ; le jardin à 30 nourritures donne 1,25, proche des vitesses mesurées dans les runs (0,7 à 1,7, ~1,1 en médiane). Ce qui ralentit les créatures d'une grosse population, c'est surtout la nourriture qui se raréfie, pas le nombre de voisins.
- Ce que le 08/11 attribuait à la densité était sans doute en partie un effet de nourriture par créature (nourriture fixe, plus de créatures pour se la partager).
- **Limites** : 3 tirages, 3 000 ticks par condition ; trois niveaux de nourriture ; une seule configuration (1×1).

**Gradient de sélection** (chaque population continuée 20 000 ticks, morts d'adultes après 5 000, ~1 100 à 1 550 morts chacune) :

- **rho moyen +0,27 ± 0,19**, positif dans les 8 populations (de +0,03 à +0,67) : les plus rapides laissent plus de petits. Petits par quart de vitesse, du plus lent au plus rapide, en moyenne : ~0,56 / 1,08 / 1,46 / 2,01 ; la hausse est régulière dans 7 populations sur 8.
- Le 08/11 : rho +0,07 ± 0,11, avec les intermédiaires favorisés (**sélection stabilisante**). Aujourd'hui la sélection est **dirigée vers la vitesse**.
- Corrélation seulement : une créature rapide est peut-être rapide parce qu'elle est en bonne santé (bien nourrie), pas l'inverse.

**Conclusion** : avec les règles actuelles, la vitesse est un comportement appris qui suit **la quantité de nourriture** (×2 de 15 à 60 nourritures par écran), bien plus que la densité ; elle varie aussi beaucoup entre lignées, et la sélection pousse vers les plus rapides. Le 08/11 décrivait un autre monde (nourriture fixe, sans `FOOD_COUNT` élevé pour les petites populations).

**Limites** : une seule configuration (1×1, une espèce) ; 3 tirages par condition du jardin ; une seule suite par population pour le gradient ; nourriture du jardin fixée à son maximum.

### Duel `complet` contre `complet_faim` sur 16 graines (22/11/2026)

Partie 2×2, 60°, règles actuelles, 120 000 ticks, 100 fondateurs de chaque espèce. Graines 1 à 8 : `experiments/results/20261122_121405_mes_reglages_plafond1600` (lancé avec `POP_MAX=1600` pour le monde entier, l'équivalent exact du plafond actuel de 400 par écran en 2×2 ; l'optimisation de la vision ne change aucun bit). Graines 9 à 16 : `experiments/results/20261122_135654_duel_graines_9_16`.

| Graines | `complet` gagne | `complet_faim` gagne | Perdante éteinte au tick |
|---|---|---|---|
| 1 à 8 | 5 | 3 | 6 000 à 70 200 |
| 9 à 16 | 5 | 3 | 12 600 à 42 600 |
| **Total** | **10** | **6** | médiane ~17 000 |

- **Pas de vainqueur** : 10 sur 16 pour `complet`, soit 62 % (intervalle de confiance à 95 % : 39 à 82 %). Sous l'hypothèse d'espèces aussi bonnes l'une que l'autre, un écart au moins aussi grand arrive 45 fois sur 100. Le capteur de faim n'apporte rien de mesurable dans ce monde, ni en bien ni en mal.
- **Toujours un seul survivant** : dans les 16 graines, une espèce disparaît, le plus souvent avant 30 000 ticks. Le vainqueur semble se décider tôt, à la sortie du goulot, plutôt que par un avantage durable.
- Les 8 nouvelles graines reproduisent exactement la répartition des 8 premières (5 contre 3) ; population 439 ± 25, comme avant.
- **Limites** : un seul monde (2×2, 60°) ; avec un écart réel de quelques points, il faudrait une centaine de graines pour le voir.

**Le capteur de faim marche-t-il ?** Mesuré sur les 6 populations `complet_faim` gagnantes (sorties brutes et script : `experiments/results/20261122_135654_duel_graines_9_16/capteur_faim.txt`) :

| Mesure | Résultat |
|---|---|
| Valeur de l'entrée « Faim » pendant une partie | 0,02 en moyenne ; au-dessus de 0,05 seulement 8 à 11 % du temps ; jamais à 1 |
| Écart des sorties entre faim forcée à 0 et à 1 | virage 0,15 à 0,47, vitesse 0,26 à 0,35 : autant ou plus que pour l'énergie (0,09 à 0,20 ; 0,14 à 0,42) |
| Capteur coupé (forcé à 0), même graine, 20 000 ticks | population et vitesse à ±5 % près, écarts dans les deux sens selon la population |

- Le capteur n'est pas cassé, et le réseau réagirait à lui (ses poids ne sont pas nuls).
- Mais l'entrée reste collée près de 0, à cause de son échelle. La nourriture est pourtant hors de vue 81 % du temps (`blind_frac`) ; seulement, ces moments sont courts (~12 ticks en moyenne : la créature tourne et en aperçoit vite une), alors que l'entrée met `HUNGER_SCALE` = 600 ticks à monter jusqu'à 1. Elle dépasse donc rarement quelques centièmes.
- D'où, sans doute, le duel nul : avec cette échelle, le capteur ne distingue pas « rien vu depuis 5 ticks » de « rien vu depuis 50 ». Test avec une échelle de 60 ticks : section suivante.
- (Corrigé le 22/11 : une première version disait qu'une nourriture est « presque toujours en vue », ce que `blind_frac` dément.)
- Limite : la population monte au-dessus de l'équilibre (500 à 590) pendant ces 20 000 ticks, car les créatures rechargées ne comptent pas dans la pression de nourriture ; c'est le même biais dans les deux bras.

### Duel avec un capteur de faim à la bonne échelle (22/11/2026)

Même duel (2×2, 60°, 16 graines, 120 000 ticks), avec `HUNGER_SCALE=60` au lieu de 600 : l'entrée « Faim » atteint 1 après 1 s sans nourriture en vue au lieu de 10 s, à l'échelle des moments réels sans rien voir (4 ticks en médiane, 31 au 90e centile). Résultats : `experiments/results/20261122_142633_duel_faim_echelle60` (avec `capteur_faim.txt`).

| Échelle | `complet` gagne | `complet_faim` gagne | Les deux encore là | Entrée « Faim » moyenne | Population quand on coupe le capteur |
|---|---|---|---|---|---|
| 600 ticks (défaut) | 10 | 6 | 0 | 0,02 | ±5 %, dans les deux sens |
| 60 ticks | 9 | 6 | 1 (graine 6, `complet` à 68 %) | 0,17 (au-dessus de 0,05 54 % du temps) | −1 à −5 % dans les 6 populations |

- **Toujours pas de vainqueur** : `complet` élimine l'autre espèce dans 9 graines, `complet_faim` dans 6, et une graine garde les deux (10 contre 6 en comptant l'espèce majoritaire, comme avec l'échelle par défaut). Les gagnants changent d'une graine à l'autre, pas le total.
- **Mais le capteur sert un peu** : avec l'échelle de 60, le couper fait baisser la population de chacune des 6 populations `complet_faim` gagnantes (−2,5 % en moyenne). Six baisses sur six arrivent une fois sur 32 au hasard. Avec l'échelle de 600, les écarts allaient dans les deux sens.
- **Pourquoi le duel ne le montre pas** : un avantage de quelques pour cent de population ne pèse rien face au hasard du départ, qui décide du vainqueur avant 30 000 ticks dans presque toutes les graines. Il faudrait des centaines de graines pour le voir dans un duel.
- **Limites** : un effet de quelques pour cent sur une seule suite par population ; la population de ces suites dépasse l'équilibre (500 à 600, créatures rechargées hors pression de nourriture), même biais dans les deux bras.
- **Retenu** : `HUNGER_SCALE = 60` dans `config.py`.

### Duels de populations évoluées : faim, bruit, mémoire contre `complet` (22/11/2026)

Nouveau protocole, pour enlever la loterie du goulot de départ : chaque espèce évolue d'abord **seule**, 16 graines × 120 000 ticks (1×1, réglages actuels, dont `HUNGER_SCALE = 60`) ; puis chaque duel part de 100 créatures évoluées de chaque espèce, tirées des populations finales de même numéro de graine (`--from-population` avec deux fichiers), et dure 120 000 ticks. Résultats : `experiments/results/20261122_15*_seul_*` et `experiments/results/20261122_15*_duel_evolues_*`.

**Seules** (moyenne des 10 derniers relevés) : les quatre espèces se valent.

| Espèce | Extinctions | Population | Vitesse |
|---|---|---|---|
| `complet` | 1/16 | 206 ± 21 | 1,36 ± 0,79 |
| `complet_faim` | 0/16 | 193 ± 23 | 1,76 ± 0,92 |
| `complet_bruit` | 1/16 | 187 ± 28 | 2,05 ± 1,08 |
| `complet_memoire` | 0/16 | 202 ± 18 | 1,38 ± 0,71 |

**Duels** (une graine éteinte seule n'a pas de duel : 15, 14 et 15 duels) :

| Contre `complet` | `complet` gagne | L'autre gagne | Les deux restent | Élimination (médiane) | p (bilatéral) |
|---|---|---|---|---|---|
| `complet_faim` | 9 (+1 mixte) | 5 | 1 | 24 300 ticks | 0,30 |
| `complet_bruit` | 8 (+1 mixte) | 5 | 1 | 18 600 ticks | 0,42 |
| `complet_memoire` | 10 (+1 mixte) | 4 | 1 | 51 900 ticks | 0,12 |
| **Total** | **30 sur 44** (espèce majoritaire) | 14 | | | 0,02 |

- **Aucun duel ne tranche seul.** Ensemble, `complet` l'emporte 30 fois sur 44 contre les espèces qui ont une entrée ou une mémoire en plus (p = 0,02). C'est un indice qu'une entrée en plus ne paie pas, voire coûte un peu (plus de poids à muter, plus de bruit), pas une preuve : les trois duels d'une même graine partagent la même population `complet`, et trois comparaisons regroupées gonflent la chance d'un faux positif.
- **Pas de lignée `complet` « championne »** : sur les 14 graines communes aux trois duels, `complet` bat ses trois adversaires dans 4 graines (4,4 attendues si les duels étaient indépendants) et les perd tous dans 1 (0,4 attendue : la graine 2, éliminée en moins de 12 000 ticks les trois fois).
- **Le nouveau protocole ne rend pas les duels plus nets** : une espèce élimine toujours l'autre, vite (médiane 18 600 à 51 900 ticks, soit environ 10 à 27 durées de vie de ~1 900 ticks), et le sens change d'une graine à l'autre, comme avec des fondateurs au hasard (10 contre 6). Le vainqueur dépend surtout de la paire de lignées qui se rencontrent (les lignées d'une même espèce vont de 0,5 à 4 en vitesse), bien plus que de l'espèce.
- **Limites** : 1×1 seulement ; un seul tirage de duel par paire de populations ; comparaison regroupée.
- Pour séparer l'effet de l'espèce de celui de la lignée, il faudrait faire se rencontrer chaque population de l'une avec plusieurs de l'autre (seed *i* contre seed *j*), ou mesurer une valeur sélective par remplacement d'entrées plutôt que par duel. Fait : section suivante.

### Rejeux et duels croisés : chance, lignée ou espèce ? (22/11/2026)

Suite de la section précédente, mêmes populations évoluées seules, mêmes réglages (1×1, 120 000 ticks). Résultats : `experiments/results/20261122_2*_rejeu*` et `experiments/results/20261122_2*_croise*` ; tableaux complets et scripts : `experiments/results/20261122_230145_croise3_complet_memoire/rejeux_croises.txt`.

- **Rejeux** (`--replica 1` et `2`) : mêmes fondateurs, autre hasard du monde (positions, nourriture, mutations).
- **Duels croisés** (`--shift 1`, `2`, `3`) : la population `complet` de la graine *i* rencontre la population adverse de la graine *j* placée 1, 2 ou 3 rangs plus loin. Avec le duel d'origine, chaque lignée rencontre 4 adversaires différents.

**1. Le hasard du monde ne décide presque rien.** Sur les duels tranchés au moins deux fois, le même camp gagne à chaque rejeu dans 37 cas sur 40 (13/14 contre faim, 12/13 contre bruit, 12/13 contre mémoire). Une fois les fondateurs choisis, l'issue est écrite : ce sont les lignées, pas la chance du monde.

**2. Duels croisés** (151 duels tranchés, décalages 0 à 3) :

| Contre `complet` | `complet` gagne | Prédit par la lignée `complet` | Prédit par la lignée adverse | Lignées adverses battues en majorité |
|---|---|---|---|---|
| `complet_faim` | 32 sur 51 (63 %) | 70 % | 88 % | 9 sur 16 |
| `complet_bruit` | 30 sur 48 (62 %) | 62 % | 81 % | 8 sur 15 |
| `complet_memoire` | 39 sur 52 (75 %) | 79 % | 91 % | 13 sur 16 (p = 0,02) |

« Prédit par la lignée » : le vainqueur d'un duel deviné d'après les autres duels de cette lignée (sans celui-là). Répondre toujours « l'espèce majoritaire » donne 63 %, 62 % et 75 %.

- **La lignée adverse explique la plupart des issues** (81 à 91 % de bonnes prédictions), la lignée `complet` beaucoup moins (62 à 79 %, à peine mieux que la majorité). Une population faim, bruit ou mémoire est « forte » ou « faible » quel que soit le `complet` d'en face ; les populations `complet` d'un même run se ressemblent davantage. Exception : la population `complet` de la graine 2 perd ses 12 duels.
- **`complet_memoire` est vraiment plus faible** : 13 de ses 16 lignées perdent la majorité de leurs duels contre des `complet` variés (test du signe au niveau des lignées, p = 0,02 ; les duels d'une même lignée ne comptent pas comme indépendants). La mémoire coûte : sans doute plus de poids à faire évoluer pour un bénéfice nul dans ce monde.
- **Faim et bruit : pas d'effet d'espèce.** 9 lignées faim sur 16 et 8 lignées bruit sur 15 perdent en majorité : le hasard. L'avantage apparent de `complet` (62-63 % des duels) vient de quelques lignées adverses faibles, qui perdent tous leurs duels.
- Le 30 sur 44 de la section précédente mélangeait donc un vrai handicap (mémoire) et deux nuls (faim, bruit).
- **Limites** : 1×1 ; une population évoluée par graine et par espèce (16 lignées) ; les décalages réutilisent les mêmes lignées, d'où des tests au niveau des lignées plutôt que des duels.

### Ce qui fait une lignée forte, et à quoi sert la mémoire (22/11/2026)

**1. Traits mesurés seul contre résultats en duel.** Pour chacun des 151 duels croisés, on compare les deux populations telles qu'elles étaient seules (moyenne des 10 derniers relevés de `seul_*`). Sorties et script : `experiments/results/20261122_230145_croise3_complet_memoire/lignees.txt`.

| Trait (mesuré seul) | Le camp où il est le plus élevé gagne |
|---|---|
| Population | **79 %** (120 sur 151) |
| Âge moyen à la mort | 72 % |
| Part du temps sans nourriture en vue | 72 % |
| Taille, génération max | 56 %, 44 % (aucun lien) |
| Enfants, morts de faim | 34 %, 35 % |
| Énergie moyenne | 28 % |
| Vitesse | **26 %** : le plus rapide perd 3 fois sur 4 |
| Nourriture mangée par créature | 21 % |

- **La population qu'une lignée tient seule prédit le duel** (79 %, de même contre faim, bruit et mémoire). Une lignée gagne si elle fait vivre plus de créatures avec la même nourriture : des créatures lentes, économes, qui vivent longtemps et mangent peu chacune.
- **Les lignées rapides perdent presque tout** : les 10 lignées sur 62 qui roulent à plus de 2,5 gagnent 6 % de leurs duels. Seules, elles ne tiennent que 151 créatures contre 206. Contraste avec la sélection *dans* une population, qui pousse vers la vitesse (section « La vitesse avec les règles actuelles ») : courir rapporte à l'individu face à ses voisins, mais une population de coureurs nourrit moins de monde et perd face à une population d'économes.
- **La mémoire perd au-delà de ce que prédit la population** : 9 duels où la population mémoire était plus nombreuse seule mais a perdu, contre 4 pour faim et 3 pour bruit.

**2. La mémoire sert-elle ?** Sur les 16 populations `complet_memoire` évoluées seules, puis en duel avec la mémoire coupée (entrées de mémoire forcées à 0 à chaque tick). Sorties et script : `experiments/results/20261122_232435_duel_memoire_coupee/sonde_memoire.txt`.

- **Les cellules de mémoire sont actives** : valeur absolue moyenne 0,52 à 0,93, écart-type 0,2 à 0,6 ; remplacer la mémoire réelle par 0 change les sorties autant que faire passer l'énergie de 0 à 1 (virage 0,11 à 0,39, vitesse jusqu'à 0,94).
- **Seule, la couper coûte** : population −3,1 % en moyenne (deux mondes par population, ticks 5 000 à 20 000), plus basse dans 13 populations sur 16 (p = 0,02).
- **En duel, la couper fait perdre plus et plus vite** : contre les mêmes `complet` (15 duels d'origine), `complet` gagne 12 fois (au lieu de 10), `complet_memoire` 1 fois (au lieu de 4), les deux restent 2 fois ; élimination médiane 17 400 ticks au lieu de 51 900. Les 3 graines où la mémoire gagnait (1, 3, 14) basculent.
- **Donc la mémoire n'est pas un poids mort** : les réseaux qui l'ont s'en servent et en dépendent. Le handicap de l'espèce vient de ce que l'évolution en fait : avec 2 entrées et 2 sorties de plus qui se rebouclent, elle trouve des réseaux moins bons dans l'ensemble que ceux de `complet`, même s'ils tirent parti de leur mémoire. Le gain de la mémoire (quelques %) ne compense pas.
- **Limites** : la coupure ne montre que la dépendance d'un réseau à sa mémoire, pas ce qu'aurait donné une espèce sans mémoire partie du même point ; 1×1.

### La vitesse dans le temps : coureurs et économes (23/11/2026)

Les 62 populations évoluées seules de la section précédente (4 espèces, 1×1), relevé tous les 600 ticks. Sorties et script : `experiments/results/20261122_150050_seul_complet/vitesse_dans_le_temps.txt`.

Hypothèse testée : une « tragédie des communs », où chaque créature gagnerait à courir et où la population s'accélérerait peu à peu en tenant de moins en moins de monde. **Elle ne tient pas.**

| | Lignées | Vitesse 10-20k / 40-60k / 100-120k ticks | Population 10-20k / 40-60k / 100-120k |
|---|---|---|---|
| Rapides à la fin (> 2,5) | 11 | 2,94 / 3,70 / 3,54 | 85 / 120 / 149 |
| Les autres | 51 | 2,87 / 2,49 / 1,34 | 92 / 145 / 203 |

- **Presque toutes les populations partent vite** (~2,9 au début, 55 sur 62 dépassent 2,5 dans les 25 000 premiers ticks), **puis la plupart ralentissent** pendant que leur population monte : corrélation vitesse-population dans le temps négative dans 54 sur 62 (−0,65 en moyenne).
- **Les lignées rapides sont celles qui restent bloquées** dans le régime du départ, presque à la vitesse maximale (4) : elles ne s'accélèrent pas au fil du temps, elles ne ralentissent jamais.
- **À la fin, la vitesse fixe presque la population** : corrélation −0,97 entre populations. Le coût du mouvement (0,03 par unité de vitesse, contre 0,04 à l'arrêt) fixe ce qu'une même nourriture peut faire vivre : un coureur à 4 dépense 2,3 fois plus qu'un marcheur à 1.
- **Tension avec le gradient de sélection** (rho +0,27 vers la vitesse, section « La vitesse avec les règles actuelles ») : si les plus rapides laissaient vraiment plus de petits pour des raisons héritables, les populations s'accéléreraient. Or 51 sur 62 ralentissent. La vitesse d'une créature est sans doute surtout un effet de son état (une créature qui voit de la nourriture et a de l'énergie accélère et se reproduit), pas de ses gènes.

### Coût du mouvement : un levier pour la vitesse (23/11/2026)

`complet` seul, 1×1, 16 graines × 120 000 ticks, `ENERGY_MOVE_COST` de 0,015 à 0,06 (0,03 = réglage actuel, run `seul_complet`). Résultats : `experiments/results/20261123_0*_cout_mouvement_*` ; sorties et script : `experiments/results/20261123_015215_cout_mouvement_06/cout_mouvement.txt`.

| Coût par unité de vitesse | Extinctions | Vitesse (médiane) | Population | Coureurs (> 2,5) | Population d'un coureur |
|---|---|---|---|---|---|
| 0,015 | 0/16 | 2,38 | 208 ± 10 | 7/16 | 190 à 210 |
| **0,03** (actuel) | 1/16 | 1,18 | 205 ± 20 | 1/15 | 142 |
| 0,045 | 3/16 | 0,87 | 197 ± 26 | 1/13 | 113 |
| 0,06 | 6/16 | 0,73 | 188 ± 33 | 1/10 | 94 |

- **Le coût règle la vitesse, pas la population** : la vitesse médiane est divisée par 3 de 0,015 à 0,06, la population des lignées lentes bouge peu (215 → 199).
- **À bas coût, courir n'est plus un piège** : à 0,015, 7 lignées sur 16 courent, et elles tiennent presque autant de monde que les autres (190 à 210). Les vitesses varient sans que ça coûte de la population.
- **À haut coût, le piège du coureur s'aggrave** : il en reste une par réglage, bloquée près de 4, qui tient de moins en moins de monde (142 → 94).
- **Un coût élevé tue au départ** : toutes les extinctions ont lieu avant 13 000 ticks, dans le goulot (3/16 à 0,045, 6/16 à 0,06). Les fondateurs au hasard bougent beaucoup et s'épuisent avant d'apprendre.
- **Pour le jeu** : 0,03 est un compromis. Moins (0,015-0,02) donne des mondes plus variés en vitesse et sans extinction ; plus donne des mondes lents mais des débuts risqués.

### Mémoire contre `complet` dans la partie réelle : 2×2, 60° (23/11/2026)

Même protocole qu'en 1×1, avec les réglages de la partie : monde 2×2, champ de vision 60°. `complet` et `complet_memoire` évoluent seules (16 graines × 120 000 ticks), puis duels croisés 100 + 100 aux décalages 0, 1 et 2 (48 duels, chaque lignée contre 3 adversaires). Lancé comme un lot (`experiments.lot`). Résultats : `experiments/results/20261123_*_2x2_*` ; sorties et script : `experiments/results/20261123_114711_2x2_croise_complet_memoire_s2/analyse_2x2.txt`.

| Seules | Extinctions | Population | Vitesse | Coureurs (> 2,5) |
|---|---|---|---|---|
| `complet` | 0/16 | 455 ± 26 | 0,71 ± 0,12 | 0 |
| `complet_memoire` | 0/16 | 430 ± 24 | 0,80 ± 0,11 | 0 |

- **`complet` gagne 44 duels tranchés sur 45** (15/16, 16/16 et 13/16 par décalage ; 3 coexistences au décalage 2, la mémoire n'en gagne qu'un). Élimination médiane 40 200 ticks.
- **Au niveau des lignées** : 15 lignées `complet` sur 16 gagnent la majorité de leurs duels (une à égalité), et les 16 lignées mémoire perdent la majorité des leurs (test du signe p < 0,001).
- **Le handicap de la mémoire est donc confirmé, et bien plus net qu'en 1×1** (75 % des duels). Seule, la mémoire tient 5 % de créatures en moins (430 contre 455). En duel, elle perd même quand sa lignée était plus nombreuse seule (8 duels sur 44).
- **Ce qui prédit le vainqueur** : la population tenue seule, 82 % des duels (79 % en 1×1). Le plus lent gagne 71 % des duels.
- **Pas de coureurs en 2×2 à 60°** : les 32 populations restent entre 0,49 et 1,05 de vitesse. Le piège du coureur vu en 1×1 à 120° n'apparaît pas avec les réglages de la partie.
- **Durée** : 20 à 28 min par run de 16 graines. Le run `seul_complet_memoire` a duré 8 h 30 à cause d'une pause volontaire (`experiments.pause`) : les résultats n'en dépendent pas.

### Carte des réglages et préréglages (23/11/2026)

Quels réglages du menu donnent une évolution facile, dure, équitable ou complexe ? Base : 1×1, 60°, 60 nourritures, `complet` + `complet_faim`, 8 graines × 120 000 ticks. Puis chaque réglage changé seul, sur deux valeurs (21 runs, ~1 h 10, un lot). Scores calculés par `python -m experiments.carte <runs>` :

- **Survie** : extinctions (au départ = avant 20 000 ticks), population sur les 10 derniers relevés.
- **Progrès** : population finale divisée par celle de 10 000 à 20 000 ticks, générations atteintes.
- **Variété** : écart de vitesse entre graines, écart relatif de taille.
- **Équité** : graines où les deux espèces vivent encore à la fin, et durée de la perdante (élimination médiane).
- **Complexité** : sur 30 créatures finales par graine, rejouées 1 500 ticks. *Entrées utilisées* : entrées dont le passage du 10e au 90e centile change la sortie de plus de 0,05 en moyenne (sur 9, 10 pour `complet_faim`). *Non-linéarité* : 1 − R² d'un ajustement linéaire des sorties sur les entrées (0 = une simple somme pondérée ; plus haut = seuils, tout ou rien).

Résultats : `experiments/results/20261123_1*_carte_*`, tables dans `experiments/results/carte_reglages/`.

| Réglage changé | Extinctions | Population | Générations | Vitesse ± graines | Entrées | Non-linéarité | Élimination médiane |
|---|---|---|---|---|---|---|---|
| base | 0/8 | 219 | 69 | 0,80 ± 0,21 | 5,3 | 0,18 | 14 400 |
| vision 120° / 360° | 0 / 2 | 206 / 204 | 72 / 66 | 1,30 / 1,32 | 7,1 / 8,5 | 0,17 / 0,16 | 9 000 / 8 700 |
| nourriture 30 / 40 | 1 / 0 | 160 / 186 | 60 / 62 | 0,95 / 0,96 | 5,5 / 5,6 | 0,15 / 0,19 | 10 800 / 12 000 |
| énergie nourriture 15 / 60 | **5** / 0 | 136 / 272 | 57 / 65 | 1,07 / 0,68 | 6,4 / 4,9 | 0,15 / 0,18 | 9 600 / 18 000 |
| repousse 0 / 300 | 0 / 0 | **385** / **84** | 63 / 60 | 1,65 ± 0,77 / 1,17 | 5,1 / 6,1 | 0,16 / 0,08 | **30 000** / 15 300 |
| mutation 0,05 / 0,3 | 0 / 0 | 200 / 218 | 72 / 59 | 1,35 / 0,84 | 5,1 / 5,8 | 0,15 / **0,27** | 13 800 / 24 600 |
| reproduction 80 / 180 | 0 / 0 | 221 / 170 | **98** / 49 | 0,81 / 1,70 | 5,3 / 5,2 | 0,21 / 0,15 | 9 300 / 13 800 |
| âge max 3 000 / jamais | 0 / 0 | 197 / 220 | 85 / 57 | 1,18 / 0,86 | 5,9 / 5,3 | 0,17 / 0,19 | 11 100 / 15 600 |
| poison 0 / 20 | 0 / 0 | 217 / 213 | 63 / 63 | 0,99 / 0,83 | 5,1 / 6,4 | 0,18 / 0,17 | 14 700 / 9 300 |
| obstacles 0 / 25 | 0 / 1 | 217 / 208 | 61 / 66 | 0,89 / 1,15 | 5,4 / 6,7 | 0,19 / 0,24 | 12 000 / 13 200 |
| taille fixe / neutre | 0 / 0 | 151 / 155 | 57 / 54 | 1,09 / 1,05 | 4,7 / 4,8 | 0,11 / 0,12 | 12 900 / 15 600 |

- **Survie** : la nourriture décide. Repousse immédiate ou énergie 60 : bien plus de créatures (385, 272). Énergie 15 : 5 graines sur 8 s'éteignent au départ. Repousse 300 : 84 créatures, mais aucune extinction.
- **Progrès** : les générations suivent le rythme des naissances (reproduction à 80 : 98 générations ; âge max 3 000 : 85).
- **Variété** : la repousse immédiate disperse le plus les vitesses entre graines (± 0,77) ; le mode `neutre` laisse la taille dériver (écart 0,25 contre 0,01).
- **Équité** : une espèce élimine toujours l'autre (1 coexistence en 168 graines), avec des victoires partagées (à peu près 4 contre 4). Seule la durée change : la perdante tient le plus longtemps avec une nourriture abondante (repousse 0 : 30 000 ticks) ou une mutation forte (24 600).
- **Complexité** : une vision plus large fait utiliser plus d'entrées (8,5 sur 9 à 360°, en partie parce que les capteurs voient plus souvent quelque chose) ; mutation forte, obstacles nombreux et reproduction rapide rendent les réseaux moins linéaires. La taille fixe ou neutre les rend plus simples (0,11).

**Les réglages ne s'additionnent pas.** Combinés, les meilleurs de chaque objectif (validation : 8 graines, vision 120°) donnent : « dur » (40 nourritures, repousse 300, 20 poisons) 8 extinctions sur 8 ; « compliqué » (20 poisons, 25 obstacles, mutation 0,3, reproduction 80) 7 sur 8. Des variantes plus douces (30 000 ticks, les extinctions arrivent tôt) ont donné les préréglages retenus :

| Préréglage | Réglages (le reste : défauts, vision 120°) | Extinctions | Population | Résultat |
|---|---|---|---|---|
| Facile | énergie 60, repousse 0, pas de poison | 0/8 | 400 (plafond) | coexistence 2/8, la perdante tient 39 000 ticks |
| Équitable | énergie 60, repousse 0, mutation 0,3 | 0/8 | 400 (plafond) | coexistence 2/8, 21 300 ticks, non-linéarité 0,33 |
| Dur | repousse 300, 20 poisons | 2/8 | ~40 | (30 000 ticks) |
| Compliqué | 25 obstacles, mutation 0,3 | 0/8 | ~100 | 7 entrées sur 9, non-linéarité 0,22 (30 000 ticks) |

Ils sont dans `presets/` (versionnés) et apparaissent en tête des préréglages du panneau Paramètres (◀ ▶, puis Appliquer). Ils ne changent ni la taille du monde ni les espèces ; les nombres de nourritures, poisons et obstacles sont par écran, valables en 2×2. Limites : base en 1×1 (le jeu tourne en 2×2) ; Dur et Compliqué validés sur 30 000 ticks seulement.

### Optimisation du calcul (23/11/2026)

Trois changements, chacun vérifié **identique au bit près** : mêmes trajectoires sur 3 000 ticks (empreinte de toutes les positions, énergies et nourritures, trois mondes dont un avec toutes les espèces et 15 obstacles), et un run de 8 graines donne les mêmes `timeline.csv` octet pour octet. Banc : population évoluée en 2×2 à 60° (~1 350 créatures), 1 000 ticks, un processus.

| Étape | 2×2 (~1 350 créatures) | 1×1 (400) |
|---|---|---|
| Avant | 10,7 ms | 2,10 ms |
| 1. État des créatures dans des tableaux permanents (`CreatureStore`, `core/creature.py`) | 8,8 ms | |
| 2. Grille spatiale pour la vision et les contacts (`core/grid.py`) | 4,0 ms | 1,74 ms |
| 3. Numba pour la vision et les contacts (`core/kernels.py`) | **2,2 ms** | **1,08 ms** |

- **Tableaux permanents** : la position, l'énergie, l'âge... de chaque créature vivent dans un tableau numpy par champ ; une créature lit et écrit sa ligne. Le tick ne recopie plus chaque objet dans des tableaux (~25 fois par tick) puis en retour.
- **Grille** : le monde est découpé en cases au moins aussi larges que la vue ; une créature n'est comparée qu'aux objets des 9 cases autour d'elle (11 % des nourritures en 2×2, contre toutes). Gain surtout dans les grands mondes : en 1×1, les 9 cases couvrent presque tout.
- **Numba** : la recherche de l'objet le plus proche en vue (nourriture, poison, obstacle et son contour) et le choix du gagnant de chaque nourriture sont compilés. Mêmes formules dans le même ordre que numpy, d'où des résultats identiques. Le multithreading (boucle parallèle sur les créatures) n'apporte presque rien : 3,0 ms sur un cœur, 2,2 ms sur 8. Le gain vient de la compilation. Dans les expériences, chaque graine prend un seul fil : les graines remplissent déjà les cœurs.
- **Run réel** : 8 graines × 4 000 ticks en 2×2 à partir de populations évoluées : 110 s → 26 s (×4,2).
- Numba est facultatif (`requirements.txt`, ou `pip install .[fast]`) : sans lui, ou avec `EVOLUTION_NUMBA=0`, le code numpy donne les mêmes résultats, plus lentement. Compilé au premier lancement (quelques secondes), puis gardé en cache dans `__pycache__`. `tests/test_world.py` compare les deux chemins.
- Ce qui reste (2,2 ms) : contour des obstacles et poussées (~0,4 ms), contacts côté Python (~0,3 ms), réseaux et déplacements (~0,4 ms), naissances et morts.

### Coût du calcul (22/11/2026)

Les coûts par tick des sections précédentes datent d'avant l'optimisation de la vision (commit `ea4fc90` : l'angle n'est plus calculé que pour les objets à portée, résultat identique au bit près). Banc de 300 ticks, un processus :

| Scène | Avant | Après |
|---|---|---|
| 2×2, ~900 créatures | 17,0 ms | 11,0 ms (−35 %) |
| 1×1, 200 à 400 créatures | 1,63 ms | 1,38 ms (−15 %) |

Dans la partie réelle (2×2, ~440 créatures), un tick coûte 7,4 ms une fois optimisé (les ~6 ms des tableaux précédents sont déduits de la durée des runs, pas mesurés de la même façon). Le temps va à la vision (42 %), aux contacts nourriture-créature (22 %) et aux réseaux et déplacements (22 %). Garder les coordonnées des objets dans un tableau n'a rien apporté (essayé, abandonné) : les objets réapparaissent presque à chaque tick.

### Mode générations (supprimé le 08/11, historique)

Le monde durci (×2, 5 nourritures, 20 poisons à 80, 25 obstacles) avec une sélection sur l'âge d'abord menait au piège d'immobilité sur 4 graines sur 4. Dans le monde réparé (10 nourritures), l'évolution progressait sur 4 graines sur 4. Résultats dans `experiments/results/20261108_20*` (format de l'époque, lisible par `experiments.summary`).


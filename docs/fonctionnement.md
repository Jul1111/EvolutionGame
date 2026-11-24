# Fonctionnement de la simulation

## Comment ça marche

**Le monde.** Un tore de 1280 × 720 : ce qui sort d'un côté rentre de l'autre. 60 sources de nourriture quand la population est petite (15 quand elle est grande), 5 poisons et 6 obstacles (valeurs par écran, `WORLD_SCALE` multiplie la surface).

**La nourriture.** Une nourriture mangée disparaît 60 ticks puis réapparaît toujours ailleurs, au hasard : hors obstacles, jamais sur une créature ni à moins de 20 de son bord (`SPAWN_CLEARANCE`). L'endroit est tiré au moment où elle réapparaît ; s'il n'y a aucune place libre, elle attend le tick suivant. Quand plusieurs créatures la touchent, celle dont le bord est le plus proche gagne. Une créature ne mange que si le repas rentre en entier dans sa réserve.

**Le poison.** La créature la plus proche qui le touche perd 40 d'énergie. Il disparaît 60 ticks puis réapparaît ailleurs, avec la même règle que la nourriture : jamais sur une créature ni à moins de 20 de son bord.

**Les obstacles.** Disques, carrés ou triangles pleins (dessinés en anémones). On ne peut pas y entrer : la créature glisse le long, et dépense de l'énergie en poussant.

**L'énergie et le mouvement.** Coût par tick : 0,04 + 0,03 × vitesse. Vitesse de 0 à 4, qui change progressivement. Plus on va vite, moins on tourne.

**Le gène de taille** (`SIZE_MODE`). Chaque créature porte une taille, de 0,5 à 2. Les fondateurs ont 1 ; un petit reçoit la taille de son parent multipliée par un facteur au hasard (exp(N(0 ; 0,05))).
- `actif` (défaut) : rayon de contact (nourriture, poison, obstacles), réserve d'énergie et énergie d'une naissance (seuil, coût, petit) proportionnels à la taille. Coût de base ∝ taille^0,75 (loi de Kleiber : un grand corps coûte moins cher à entretenir par unité de taille), coût du mouvement ∝ taille. Une nourriture donne toujours 30 : un grand doit manger plus pour faire un petit, mais tient plus longtemps sans manger.
- `neutre` : la taille mute mais ne change rien. Témoin : ce que la taille fait par simple hasard (dérive génétique).
- `fixe` : tout le monde à 1.
- Couleur «taille» (touche C) : de petit (rouge) à grand (vert). Les créatures sont dessinées à leur taille.

**Deux sortes de nourriture et le gène de régime** (`FOOD_TYPES = 2`, désactivé par défaut). Une nourriture sur deux est de la sorte 1 (dessinée en jaune). Chaque créature porte un régime entre 0 et 1 : une nourriture de sorte k lui donne `FOOD_ENERGY × (1 − |régime − k|)^DIET_EXPONENT`. Avec l'exposant 2 (défaut), un spécialiste (0 ou 1) tire tout de sa nourriture et rien de l'autre, un généraliste (0,5) un quart des deux : les spécialistes sont avantagés. Les fondateurs sont spécialistes, un sur deux de chaque nourriture (`DIET_FOUNDERS`, ou au hasard), un petit reçoit celui de son parent + N(0 ; 0,05) (`DIET_MUTATION_STD` ; à 0,15 une espèce garde un groupe de spécialistes par sorte de nourriture, `docs/experiences.md`). Le capteur «valeur nourriture» (espèces `regime`, `regime_faim`) donne ce que rapporterait la nourriture la plus proche en vue : la créature ne connaît pas son propre régime, c'est ainsi qu'elle distingue sa nourriture. Colonnes `diet_mean`, `diet_low` (part sous 0,25), `diet_high` (au-dessus de 0,75), `diet__<espèce>`.

**Trois ou quatre sortes, niches asymétriques.** Avec `FOOD_TYPES` = 3 ou 4 (bleue et rose en plus), les sortes se répartissent entre 0 et 1 : la sorte k nourrit le mieux le régime k/(N−1) et donne `FOOD_ENERGY × (1 − |régime − k/(N−1)| × (N−1))^DIET_EXPONENT`, rien au-delà des sortes voisines (à deux sortes, la formule ci-dessus). Les fondateurs spécialistes se partagent les sortes à tour de rôle ; colonnes `diet_kind<k>` en plus (part des spécialistes de chaque sorte). `FOOD_KIND_SHARES` donne la part de chaque sorte parmi les nourritures (par exemple `(1, 3)` : une nourriture sur quatre de la sorte 0) et `FOOD_KIND_ENERGY` un facteur d'énergie par sorte (par exemple `(2.0, 0.667)` : la sorte 0 deux fois plus riche) ; le capteur «valeur nourriture» en tient compte. Vides par défaut : parts égales, même énergie.

**Les prédateurs** (`PREDATION = True`, désactivé par défaut). Au tick `PREDATOR_START` (20 000, une fois le goulot de départ passé), `PREDATOR_FOUNDERS` prédateurs par écran (5) arrivent, avec des réseaux tirés au hasard, de l'espèce `PREDATOR_PROFILE` (`predateur`). Un prédateur ne mange jamais de nourriture, seulement les créatures des autres espèces (ses proies) ; les prédateurs ne se mangent pas entre eux. Avec `PREDATOR_POPULATION` (un fichier de population sauvegardée, ou une liste : la graine *s* prend le fichier (*s* − 1) mod *n*), les prédateurs qui arrivent sont tirés de ce fichier (génomes et tailles, sans remise) au lieu d'être aléatoires. Dans `experiments.run`, avec `PREDATION`, les prédateurs d'une population de départ (`--from-population`) sont écartés ; `--cycle` fait partir chaque graine d'un seul des fichiers donnés au lieu d'un mélange.
- Chaque proie, dans l'ordre de la liste, est tuée par le prédateur le plus proche qui la touche (centres plus proches que la somme des rayons, distance mesurée au bord du prédateur), qui ne digère pas et dont la réserve peut recevoir le repas. Le prédateur gagne `PREDATION_EFFICIENCY` × l'énergie de la proie (0,75 : le reste est perdu, toute l'énergie vient des plantes), puis digère `PREDATOR_DIGEST` ticks (200) sans pouvoir attaquer. La proie meurt (cause « mangé »).
- Mêmes règles de vie que les autres (coût, naissance, vieillesse) ; coût de base multiplié par `PREDATOR_COST_FACTOR` (1). La nourriture suit seulement le nombre de proies.
- Capteurs : `prey` (distance et angle de la proie la plus proche en vue, pour les prédateurs), `predator` (du prédateur le plus proche en vue, pour les proies). Même cône et même portée que pour la nourriture ; une créature ne voit jamais les siens par ces capteurs.
- Mesures (colonnes ajoutées seulement avec des prédateurs) : `deaths_eaten`, `prey`, `predators`, `kill_rate` (proies par 1000 ticks de vie de prédateur), pour les proies `prey_threat_frac` (part du temps avec un prédateur en vue), `prey_speed_threat` / `prey_speed_calm` (vitesse avec et sans), `prey_toward` (virage vers lui : négatif = s'en détourne), et pour les prédateurs `pred_chase_frac`, `pred_speed_chase`, `pred_speed_idle`, `pred_toward`.

**Le réseau** (espèce `complet`). 9 entrées → 6 neurones cachés → 2 sorties (virage, vitesse demandée), 74 poids. Entrées : distance et angle de la nourriture visible la plus proche, énergie, vitesse, «peut manger», distance et angle du poison, distance au bord et angle de l'obstacle. La vision est un cône de 120° et de portée 200. Pas de mémoire.

**La vie et la mort** (`evolution/continuous.py`).
1. Départ : 200 créatures aux réseaux tirés au hasard.
2. Une créature d'au moins 10 s qui a 120 d'énergie fait un petit (au plus un toutes les 5 s) : elle perd 60, le petit naît à côté avec 50 et hérite de son réseau plus un bruit gaussien (écart-type 0,1), et de sa taille mutée. Seuil, coût et énergie du petit sont multipliés par la taille du parent quand le gène est actif.
3. Mort de faim (énergie 0) ou de vieillesse (100 s).
4. Plafond de calcul : 400 créatures. Les naissances qu'il bloque sont comptées : si ce n'est pas 0, la population n'est plus réglée par la nourriture.
5. Une extinction arrête tout.

## Les espèces (profils de réseau)

Un profil dit quels capteurs alimentent le réseau, la taille de la couche cachée, si la vitesse est une sortie, et le nombre de cellules de mémoire. Plusieurs espèces peuvent partager le monde (menu Réseau).

| Profil | Entrées | Sorties | Poids |
|---|---|---|---|
| `complet` (défaut) | nourriture, énergie, vitesse, peut manger, poison, obstacle ; 6 cachés | virage, vitesse | 74 |
| `complet_faim` | `complet` + faim (temps depuis la dernière nourriture vue, 0 → 1 en 1 s) | virage, vitesse | 80 |
| `complet_bruit` | `complet` + bruit (valeur au hasard à chaque tick, entre -1 et 1) | virage, vitesse | 80 |
| `complet_memoire` | `complet` + 2 cellules de mémoire (sorties renvoyées en entrée au tick suivant) | virage, vitesse, 2 mémoires | 100 |
| `complet_12`, `complet_16` | `complet` avec 12 ou 16 neurones cachés | virage, vitesse | 146, 194 |
| `regime` | `complet` + valeur de la nourriture la plus proche pour son régime (`FOOD_TYPES = 2`) | virage, vitesse | 80 |
| `regime_faim` | `regime` + faim | virage, vitesse | 86 |
| `proie` | `complet` + prédateur le plus proche (`PREDATION`) | virage, vitesse | 86 |
| `predateur` | proie la plus proche, énergie, vitesse, obstacle ; 6 cachés ; mange les autres espèces, jamais la nourriture | virage, vitesse | 56 |
| `chasseur` | nourriture | virage, vitesse | 6 |
| `chasseur_rassasie` | nourriture + peut manger | virage, vitesse | 8 |
| `prudent` | nourriture + poison, 3 cachés | virage, vitesse | 23 |
| `vitesse_fixe` | nourriture | virage (vitesse fixe) | 3 |
| `scripte` | règles écrites à la main (`brain/scripted.py`), n'évolue pas : point de référence | virage, vitesse | 0 |

## Explorer quand rien n'est en vue

Sans rien en vue, les entrées de `complet` sont presque constantes : il ne peut qu'aller tout droit, tourner en rond ou s'arrêter. `complet_faim`, `complet_bruit` et `complet_memoire` lui donnent chacune un moyen d'agir autrement, sans coder l'exploration à leur place.

- **Mesurer** : courbes «Part du temps sans nourriture en vue», «Vitesse sans nourriture en vue», «Virage sans nourriture en vue» (colonnes `blind_frac`, `blind_speed`, `blind_turn` de `timeline.csv`). Explorer = aller vite et assez droit quand rien n'est en vue. «En vue» = une nourriture disponible dans le cône (une nourriture mangée réapparaît ailleurs).
- **Duel** : cocher plusieurs espèces dans l'écran de réglages. Elles partagent le monde ; le panneau Population montre la courbe et l'effectif de chacune (colonnes `pop__<espèce>`). Celle qui envahit le monde porte quelque chose d'utile. Sans affichage : `python -m experiments.run --name duel_faim --profiles complet complet_faim --ticks 120000`, puis la table «Espèces» (part moyenne, graines où elle est majoritaire, graines où elle s'est éteinte).
- Les 200 fondateurs sont partagés entre les espèces : chacune part plus petite, le risque d'extinction au départ augmente.

## Configuration

`config.py` est la seule référence. Le menu peut remplacer certaines valeurs (`saves/settings.json`, écarts seulement). Les expériences sans affichage ne lisent jamais `settings.json`. Les valeurs sont des valeurs de départ, réglées par des expériences notées dans les commentaires.


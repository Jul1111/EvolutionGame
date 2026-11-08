# Fonctionnement de la simulation

## Comment ça marche

**Le monde.** Un tore de 1280 × 720 : ce qui sort d'un côté rentre de l'autre. 40 sources de nourriture, 5 poisons et 6 obstacles (valeurs par écran, `WORLD_SCALE` multiplie la surface).

**La nourriture.** Une nourriture mangée disparaît 60 ticks puis réapparaît toujours ailleurs, au hasard : hors obstacles, jamais sur une créature ni à moins de 20 de son bord (`SPAWN_CLEARANCE`). L'endroit est tiré au moment où elle réapparaît ; s'il n'y a aucune place libre, elle attend le tick suivant. Quand plusieurs créatures la touchent, celle dont le bord est le plus proche gagne. Une créature ne mange que si le repas rentre en entier dans sa réserve.

**Le poison.** La créature la plus proche qui le touche perd 40 d'énergie. Il disparaît 60 ticks puis réapparaît ailleurs, avec la même règle que la nourriture : jamais sur une créature ni à moins de 20 de son bord.

**Les obstacles.** Disques, carrés ou triangles pleins (dessinés en anémones). On ne peut pas y entrer : la créature glisse le long, et dépense de l'énergie en poussant.

**L'énergie et le mouvement.** Coût par tick : 0,04 + 0,03 × vitesse. Vitesse de 0 à 4, qui change progressivement. Plus on va vite, moins on tourne.

**Le gène de taille** (`SIZE_MODE`). Chaque créature porte une taille, de 0,5 à 2. Les fondateurs ont 1 ; un petit reçoit la taille de son parent multipliée par un facteur au hasard (exp(N(0 ; 0,05))).
- `actif` (défaut) : rayon de contact (nourriture, poison, obstacles), réserve d'énergie et énergie d'une naissance (seuil, coût, petit) proportionnels à la taille. Coût de base ∝ taille^0,75 (loi de Kleiber : un grand corps coûte moins cher à entretenir par unité de taille), coût du mouvement ∝ taille. Une nourriture donne toujours 30 : un grand doit manger plus pour faire un petit, mais tient plus longtemps sans manger.
- `neutre` : la taille mute mais ne change rien. Témoin : ce que la taille fait par simple hasard (dérive génétique).
- `fixe` : tout le monde à 1.
- Couleur «taille» (touche C) : de petit (rouge) à grand (vert). Les créatures sont dessinées à leur taille.

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
| `complet_faim` | `complet` + faim (temps depuis la dernière nourriture vue, 0 → 1 en 10 s) | virage, vitesse | 80 |
| `complet_bruit` | `complet` + bruit (valeur au hasard à chaque tick, entre -1 et 1) | virage, vitesse | 80 |
| `complet_memoire` | `complet` + 2 cellules de mémoire (sorties renvoyées en entrée au tick suivant) | virage, vitesse, 2 mémoires | 100 |
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


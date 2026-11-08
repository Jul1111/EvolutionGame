# EvolutionGame

Simulation en Python et pygame de l'évolution d'une population de créatures pilotées par un réseau de neurones.

Les créatures n'apprennent rien pendant leur vie. Ce sont les générations qui évoluent : les 20 dernières survivantes d'une génération donnent la suivante, avec des mutations aléatoires sur les poids de leur réseau.

## Lancer le projet

Il faut Python 3, `pygame` et `numpy`. Il n'y a pas encore de fichier `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install pygame numpy
python main.py
```

La simulation reprend automatiquement la dernière sauvegarde si elle existe (voir «Sauvegardes»).

## Commandes

| Touche | Action |
|---|---|
| ↑ / ↓ | Vitesse de simulation (×1, 2, 5, 10, 20, 50, 100) |
| Espace | Pause |
| → | Avancer d'un tick (en pause) |
| Clic gauche | Sélectionner une créature dans le monde, ou utiliser la barre de menu |
| D | Mode debug : désactivé → plus ancienne créature vivante → toutes les créatures vivantes |
| C | Changer le mode de couleur des créatures |
| G | Afficher ou masquer les courbes |
| N | Graphe du réseau : masqué → petit (barre latérale) → grand (par-dessus le monde) |
| L | Légende des couleurs et des symboles |
| B | Sélectionner la meilleure créature (rang 1) |
| T | Suivre la lignée du meilleur : la sélection revient sur le meilleur parent à chaque génération |
| P | Panneau Paramètres |
| H ou ? | Aide et raccourcis |
| F ou F11 | Plein écran |
| Échap | Fermer le menu ouvert, puis quitter le plein écran, puis quitter |

## Interface

**Barre de contrôle** (en haut à gauche du monde) : pause / reprendre, un tick, vitesse (- et +), debug, couleur, légende, meilleure créature, suivi de la lignée, réseau (masqué / petit / grand), paramètres, aide. Chaque bouton a une infobulle avec son raccourci. En pause, un bandeau « PAUSE » s'affiche.

**Survol.** Une créature survolée affiche son rang, son énergie, sa vitesse, son âge et ses compteurs. Un libellé de la barre latérale (Vivantes, Temps aveugle, Rang, chaque entrée et sortie du réseau...) s'explique après une demi-seconde d'arrêt.

**Panneau Paramètres** (touche P ou menu Paramètres) : une ligne par réglage, avec flèches ◀ ▶, la valeur en vigueur et, en orange, la valeur en attente (`vigueur → attente`). Les changements s'appliquent au début de la génération suivante. « Appliquer maintenant » termine la génération en cours (le classement se fait alors sur une génération inachevée). « Annuler les changements » vide les valeurs en attente.

**Grand réseau** (touche N, deuxième appui) : le graphe du réseau de la créature sélectionnée, agrandi, avec le nom et la valeur de chaque entrée et sortie. On peut cliquer une autre créature pendant qu'il est affiché.

**Barre de menu** (en haut, à droite : vitesse et pause). Chaque commande clavier a son équivalent dans un menu déroulant.

| Menu | Contenu |
|---|---|
| Simulation | Pause, avancer d'un tick, accélérer, ralentir |
| Affichage | Debug (cône de vision, trait vers la nourriture la plus proche et, en violet, vers le poison le plus proche), couleur, courbes, graphe du réseau, plein écran |
| Courbes | Une case par courbe à afficher, dans la couleur de la courbe : meilleur âge, nourriture (moyenne, max, totale, par minute), vitesse (moyenne, sans nourriture en vue, rapport des deux), part aveugle, virage aveugle, énergie, vivantes, poison (parents, total, rapport poison / nourriture). Défaut : meilleur âge, nourriture moy., vitesse moy., poison touché (parents). Chaque courbe a sa propre échelle. La sélection n'est pas conservée au redémarrage |
| Paramètres | Ouvrir le panneau Paramètres, mutation, parents conservés, nombre de nourritures, énergie d'une nourriture, délai de réapparition, repas avant épuisement, positions de la nourriture (fixes ou aléatoires), nombre de poisons, dégâts d'un poison, nombre d'obstacles. Un clic passe à la valeur suivante parmi des valeurs prédéfinies. La valeur est appliquée au début de la génération suivante (marquée d'un `*` en attendant), et n'est pas conservée au redémarrage : `config.py` reste la référence |
| Sauvegarde | Terminer la génération maintenant, repartir de zéro (confirmation demandée) |
| Aide | Aide et raccourcis, légende |

La sauvegarde des génomes et le CSV s'écrivent automatiquement à chaque fin de génération. «Terminer la génération maintenant» force cette fin (sélection, CSV, sauvegarde) : le classement se fait alors sur une génération inachevée. «Repartir de zéro» met de côté `latest.npz` et `stats.csv` (renommés avec la date), rien n'est supprimé.

**Courbes.** Avec beaucoup de courbes choisies, le bandeau sous le monde (fenêtre haute) est le meilleur endroit : la légende y tient sur une ou deux colonnes. Dans la barre latérale, la place est comptée et les noms sont raccourcis.

**Barre latérale** (panneaux empilés) : Génération, Créature sélectionnée, Entrées/sorties du réseau, et les courbes (dans la barre latérale, ou en bande sous le monde si la fenêtre est assez haute). Quand le graphe du réseau est affiché et qu'il n'y a pas de bande, les courbes sont masquées pour lui laisser la place.

**Graphe du réseau.** Entrées à gauche, couche cachée au milieu, sorties à droite. La luminosité d'un neurone suit son activation (vert si positive, rouge si négative). Un lien est vert ou rouge selon le signe du signal qu'il transporte (poids × activation de la source), et plus épais quand ce signal est fort. Un lien sans signal reste faiblement visible selon la taille de son poids. Les biais ne sont pas dessinés.

## Comment ça marche

**Le monde.** Un tore de 1280 × 720 : une créature qui sort d'un côté réapparaît de l'autre. Il contient 10 sources de nourriture, 5 poisons et 6 obstacles.

**La nourriture.**
- Une nourriture mangée disparaît pendant 60 ticks, puis revient au même endroit.
- Après 3 repas, une source est épuisée : elle se déplace au hasard. Sans cela, les créatures campent à côté d'une source.
- Quand plusieurs créatures touchent la même nourriture, la plus proche gagne.

**Les obstacles.**
- Dessinés comme des anémones de mer vues de dessus : tapis sombre qui suit exactement la zone de collision (fin liseré sur le contour), trois couronnes de tentacules en spirale qui ondulent, bouche au centre. Palette indigo, teal ou lilas selon l'obstacle (la nourriture est verte, le poison violet, les créatures orange). Rendu seulement : la collision reste celle des formes pleines (disque, carré ou triangle équilatéral, forme et rotation tirées au hasard), inscrites dans un cercle de rayon 20 à 45, tirés au hasard au début de chaque génération puis fixes. Deux obstacles sont toujours séparés d'au moins 30 : une créature (16 de large) peut toujours passer.
- Une créature ne peut pas y entrer. Elle est repoussée au bord et glisse le long (sa vitesse n'est pas coupée, elle dépense donc de l'énergie en poussant).
- Nourriture, poison et créatures ne naissent jamais dans un obstacle, et la nourriture ne réapparaît jamais dedans.
- Le réseau voit l'obstacle le plus proche dans son champ de vision, par deux entrées : distance **au bord** (0 = contact) et angle vers le centre. Il ne voit pas à travers : rien ne cache la nourriture derrière un obstacle (non fait).
- Réglable depuis le menu Paramètres (nombre). 0 obstacle = monde d'avant, avec deux entrées constantes.

**Le poison.**
- Losange violet dans le monde. La créature la plus proche qui le touche perd 40 d'énergie (elle meurt si elle tombe à 0), puis le poison disparaît 60 ticks et revient à un endroit au hasard.
- Il n'est pas limité par la satiété : une créature rassasiée est aussi touchée.
- Le réseau voit le poison le plus proche dans son champ de vision, par deux entrées dédiées. Un poison en attente de retour est invisible.
- Réglable depuis le menu Paramètres (nombre, dégâts). 0 poison = monde d'avant, avec deux entrées constantes.

**L'énergie.**
- Chaque créature démarre à 100 d'énergie, avec un maximum de 200. Une nourriture donne 30.
- Une créature ne mange que si le repas rentre en entier (énergie ≤ 170), sinon elle laisse la nourriture aux autres.
- Coût par tick : 0,04 + 0,03 × vitesse. À 0 d'énergie, elle meurt.

**Le mouvement.**
- La vitesse va de 0 à 4. Elle change progressivement (accélération et freinage limités à 0,25 par tick).
- Plus la créature va vite, moins elle peut tourner (rayon de virage plus large).

**Le réseau.** Feed-forward en numpy : 9 entrées → 6 neurones cachés (tanh) → 2 sorties (tanh), soit 74 paramètres.

| Entrées | Sorties |
|---|---|
| Distance à la nourriture disponible la plus proche (1 = rien en vue) | Virage |
| Angle relatif à cette nourriture | Vitesse demandée |
| Énergie | |
| Vitesse actuelle | |
| Peut manger (1 si le repas rentre, 0 sinon) | |
| Distance au poison le plus proche (1 = rien en vue) | |
| Angle relatif à ce poison | |
| Distance au bord de l'obstacle le plus proche (1 = rien en vue) | |
| Angle relatif à cet obstacle | |

La vision est un cône : portée de 200 (`VISION_RANGE`), ouverture de 120° centrée sur le cap (`VISION_FOV_DEGREES`, réglable dans Paramètres, 360 = tout autour). Ce qui est hors du cône est invisible, nourriture comme poison. Une créature ne voit donc pas ce qui est derrière elle : la part de créatures « aveugles » monte (environ 63 % à 10 nourritures contre 24 % en vision circulaire), pense à ajuster `FOOD_COUNT`. Le réseau n'a pas de mémoire.

**L'évolution.**
1. Une génération compte 100 créatures.
2. Elle s'arrête quand il reste 20 vivantes, ou au plafond de 36 000 ticks (10 minutes simulées).
3. Les 20 meilleures sont classées par (âge, nourriture mangée), l'énergie restante ne départageant que les égalités exactes.
4. Elles passent telles quelles dans la génération suivante (élitisme), avec 80 enfants : copie d'un parent plus un bruit gaussien (écart-type 0,1) sur chaque poids. Pas de croisement.
5. Chaque génération repart dans un monde neuf, avec des créatures neuves.

La seed est fixée (42) : un lancement de zéro est reproductible. Une reprise de sauvegarde ne l'est pas exactement, car l'état du générateur aléatoire n'est pas sauvegardé.

## Sauvegardes et statistiques

Tout est dans `saves/`, ignoré par git.

- `latest.npz` : génomes des 20 parents et numéro de génération, écrasé à chaque fin de génération. Au lancement, `LOAD_ON_START = True` reprend cette sauvegarde.
- `stats.csv` : une ligne par génération.
- Si la taille du réseau a changé, l'ancienne sauvegarde est mise de côté (`latest_incompatible_<date>.npz`) et l'évolution repart de zéro.
- Si l'évolution repart de zéro, l'ancien `stats.csv` est mis de côté (`stats_ancien_<date>.csv`).

Colonnes de `stats.csv` (âges en ticks, 60 ticks = 1 seconde simulée) :

| Colonne | Sens |
|---|---|
| `generation`, `ticks`, `alive`, `best_age` | Numéro, durée, vivantes à la fin, âge du meilleur |
| `mean_food`, `max_food` | Nourriture mangée par les parents |
| `mean_speed`, `mean_energy` | Vitesse et énergie des parents au dernier tick |
| Toutes les autres colonnes | Une colonne par constante de `config.py`, nommée en minuscules (`mutation_std`, `food_respawn_delay`, `vision_range`...), avec la valeur en vigueur pendant la génération. Booléens : 1/0. Listes et couleurs : JSON. Les chemins (`SAVE_DIR`, `GENOMES_FILE`, `STATS_FILE`) sont exclus. Si `config.py` gagne une constante, la colonne est ajoutée au fichier existant (cases vides pour les anciennes lignes) ; si une colonne disparaît, l'ancien fichier est mis de côté |
| `food_count` | Nombre de nourritures du monde pour cette génération |
| `total_food` | Nourriture mangée par toute la population |
| `mean_poison`, `total_poison` | Poisons touchés : moyenne des parents, total de la population |
| `obstacle_frac` | Part de leur vie que les parents passent collés à un obstacle |
| `blind_frac`, `blind_speed`, `blind_turn` | Part du temps sans aucune nourriture à portée, vitesse et virage dans ces moments (parents) |

## Configuration

Tout se règle dans `config.py`. Plusieurs valeurs sont des valeurs de départ à ajuster, pas des résultats établis.

| Paramètre | Valeur | Rôle |
|---|---|---|
| `POPULATION_SIZE`, `PARENTS_COUNT` | 100, 20 | Taille d'une génération, nombre de parents |
| `FOOD_COUNT` | 10 | Nombre de sources |
| `FOOD_RESPAWN_DELAY`, `FOOD_MAX_EATS` | 60, 3 | Délai de retour, repas avant épuisement |
| `POISON_COUNT`, `POISON_ENERGY` | 5, 40 | Nombre de poisons, énergie perdue au contact |
| `OBSTACLE_COUNT`, `OBSTACLE_SHAPES`, `OBSTACLE_RADIUS_MIN`, `OBSTACLE_RADIUS_MAX`, `OBSTACLE_MIN_GAP` | 6, les 3 formes, 20, 45, 30 | Nombre, formes possibles, taille (rayon du cercle circonscrit) et écart minimal entre cercles circonscrits |
| `ENERGY_MAX`, `FOOD_ENERGY` | 200, 30 | Satiété, énergie d'une nourriture |
| `ENERGY_BASE_COST`, `ENERGY_MOVE_COST` | 0,04, 0,03 | Coût d'énergie par tick |
| `CREATURE_ACCELERATION`, `CREATURE_MAX_TURN`, `TURN_SPEED_PENALTY` | 0,25, 0,25, 0,5 | Mouvement |
| `MUTATION_STD` | 0,1 | Force des mutations |
| `NN_HIDDEN` | 6 | Neurones cachés |
| `GEN_MAX_TICKS` | 36000 | Plafond de durée d'une génération |

Changer `NN_INPUTS`, `NN_HIDDEN` ou `NN_OUTPUTS` rend les sauvegardes incompatibles. Les libellés affichés dans l'interface (`INPUT_LABELS`, `OUTPUT_LABELS`) doivent suivre le même ordre que les vecteurs de `World.sense` et `Creature.update`. Un `assert` vérifie leur nombre.

## Structure du projet

```
main.py                 Boucle pygame, événements, fin de génération
config.py               Toutes les constantes
core/
  world.py              Monde : nourriture, repas, capteurs, fin de génération
  creature.py           Créature : mouvement, énergie, compteurs d'exploration
  food.py               Nourriture (délai, épuisement)
  physics.py            Distances et angles sur le tore
brain/
  network.py            Réseau de neurones (génome = vecteur à plat)
evolution/
  population.py         Sélection des parents, construction de la génération suivante
  mutation.py           Mutation gaussienne
rendering/
  scene.py              Dessin du monde et des créatures
  hud.py                Panneaux de la barre latérale, graphe du réseau et courbes
  menu.py               Barre de menu et menus déroulants
  overlay.py            Barre de contrôle, légende, aide, infobulles, panneau Paramètres, grand réseau
  obstacles.py          Sprites des obstacles (anémones animées)
  layout.py, display.py Mise en page, plein écran
utils/
  persistence.py        Sauvegarde et chargement des génomes
  logger.py             Écriture de stats.csv
saves/                  Sauvegardes et statistiques (ignoré par git)
```

## Lire les résultats

- `alive` proche de 100 au plafond de 36 000 ticks : presque tout le monde survit, la sélection par la survie n'agit plus. Il faut durcir le monde (par exemple moins de nourriture).
- `mean_food` des parents qui monte puis plafonne : la population a «résolu» le monde tel qu'il est.
- `blind_frac` élevé avec une vitesse faible : les créatures attendent plutôt qu'elles ne cherchent.
- Les premières générations peuvent sélectionner des créatures quasi immobiles : rester sur place coûte 0,04 par tick, donc une créature immobile survit environ 2500 ticks. Cela se corrige en quelques générations dans les exécutions observées.

## Limites connues

- Le réseau n'a pas de mémoire. Quand rien n'est en vue, ses entrées sont constantes.
- L'exploration n'est pas démontrée : les mesures disponibles montrent surtout des créatures qui attendent ou campent. Les règles de réapparition et d'épuisement sont là pour changer ça, sans résultat établi à ce jour.
- Le coût de calcul est dominé par la simulation (un réseau numpy par créature et par tick). Il n'a pas été profilé finement.
- Les résultats d'une exécution unique ne prouvent pas grand-chose : les trajectoires varient d'une exécution à l'autre.

## Pistes

Dans cet ordre : poison avec deux canaux de perception, obstacles, autres créatures, zones riches et pauvres, monde plus vaste, mémoire dans le réseau.

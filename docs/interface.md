# Interface et commandes

## Commandes

| Touche | Action |
|---|---|
| ↑ / ↓ | Vitesse de simulation demandée (×1 à ×100). La simulation ne prend que ce que le dessin laisse d'une image à 30 FPS (`MIN_FPS`, au moins `SIM_MIN_BUDGET_MS` = 4 ms) : la fenêtre reste fluide, et quand la machine ne suit pas, la vitesse réelle s'affiche en orange |
| Espace / → | Pause / avancer d'un tick (en pause) |
| Clic | Sélectionner une créature, ou utiliser les menus |
| Molette, glisser, + - 0 1 | Zoom (jusqu'à 4 fois plus loin que la carte entière : le tore apparaît répété, assombri, autour de la carte encadrée), déplacer la vue, toute la carte, échelle d'un écran |
| V | Caméra sur la créature sélectionnée |
| B | Sélectionner la créature qui a eu le plus de petits ; à sa mort, la sélection passe à la nouvelle meilleure (jusqu'au prochain clic sur une créature) |
| T | Suivre la lignée : à la mort de la sélection, passer à son plus jeune descendant vivant, ou à la nouvelle meilleure si la lignée est éteinte |
| S | Sauvegarder la population (`saves/populations/<date>_manuelle.npz`) |
| D, C, L | Debug (cône de vision et cibles), couleur des créatures (espèce, énergie, vitesse, nourriture, taille, lignée), légende |
| G, N | Courbes (masquées, panneau, grand), graphe du réseau (masqué, petit, grand) |
| Tab, M, E | Masquer les panneaux, mini-carte, naissances et morts dans le monde |
| P, H ou ?, F | Paramètres, aide, plein écran |
| Échap | Fermer, puis quitter le plein écran, puis quitter |

## Interface

- **Style** : le monde occupe toute la fenêtre. Barre de menu, barre d'outils, panneaux et fenêtres flottent par-dessus en verre dépoli (`rendering/glass.py` : flou de ce qui est dessous, teinte, coins arrondis). Tab masque les panneaux. Surcoût mesuré sans écran : environ 0,5 ms par image en 1440×900, 2 ms en 2880×1800.
- **Couleurs** : avec une seule espèce, la couleur montre l'énergie (corail → ambre → bleu ciel). Aucune couleur de créature n'est verte : le vert est réservé à la nourriture (l'espèce «Complet» est passée de menthe à saumon). Mode «lignée» : une couleur par fondateur, transmise aux descendants (calculée à l'affichage dans `rendering/lineage.py`, sans toucher à la simulation ; une population chargée repart avec une lignée par créature).
- **Mini-carte** (M, en bas à gauche) : tout le monde, les créatures, les anémones et le cadre de la vue (coupé aux bords du tore). Un clic y déplace la vue (et coupe la caméra sur la sélection).
- **Courbes en grand** (G, deuxième appui) : axe du temps gradué, curseur qui lit toutes les valeurs à l'instant survolé, cases à cocher pour chaque courbe. Chaque courbe garde sa propre échelle (de 0 à son maximum).
- **Naissances et morts** (E) : un anneau clair s'ouvre à chaque naissance, une petite croix grise s'efface à chaque mort. 80 effets au plus à la fois.
- **Grand réseau** (N, deuxième appui) : déplaçable en glissant son titre.
- **Écran «Nouvelle simulation»** : à chaque lancement, rien ne tourne avant d'avoir cliqué. On y règle tout (dont le nombre de créatures au départ, la taille du monde, le gène de taille ; les espèces dans le menu Réseau), puis «Lancer», ou «Reprendre la population gardée» si le jeu a été fermé en cours de partie. Échap quitte. Le menu Sauvegarde → «Nouvelle simulation...» rouvre cet écran, avec «Annuler» pour revenir à la partie en cours.
- **Panneau Population** : vivantes sur le plafond de calcul, temps simulé, naissances et morts par minute simulée (dernier relevé de `timeline.csv`), générations moyenne et maximale, nombre de lignées vivantes et part de la plus grande, mini-courbe de la population (ou les espèces s'il y en a plusieurs). Statut «Extinction» quand tout le monde est mort.
- **Panneau Créature** : énergie, vitesse, âge, repas et poisons, temps aveugle, taille, génération de lignée et nombre de petits.
- **Réseau** : entrées et sorties de la créature sélectionnée, en barres ou en graphe.
- **Courbes dans le temps** (menu Courbes) : une valeur toutes les 10 s simulées, lue dans `saves/timeline.csv`. Population, naissances, morts (faim, vieillesse), repas et poisons par 1000 ticks de vie, vitesse, énergie, génération de lignée, âge à la mort, nourriture disponible, naissances bloquées par le plafond.
- **Paramètres** (touche P, aussi écran «Nouvelle simulation») : deux colonnes en sections (Évolution, Perception, Nourriture, Dangers, Monde, Espèces), description complète du réglage survolé en bas, et **préréglages** : «Enregistrer les réglages actuels» écrit `saves/presets/preset_<date>.json` (réglages et espèces), les flèches parcourent les préréglages, «Appliquer» les reprend. Réglages : mutation, seuil de reproduction, âge maximal, champ de vision, nourriture (au départ, abondance pendant, nourriture ensuite, raréfaction en, énergie, délai : la nourriture peut se raréfier une fois le premier goulot passé, désactivé par défaut), poison (nombre, dégâts), obstacles, taille du monde (1×1, 2×2 ou 3×3 écrans), gène de taille (fixe, neutre, actif). Tout s'applique tout de suite, sauf les obstacles, la taille du monde et le gène de taille (au prochain départ de zéro, marqués en orange). Nourriture et obstacles sont donnés par écran : un monde 2×2 en a 4 fois plus. Les fondateurs (200) et le plafond de créatures (400) ne changent pas avec la taille du monde : dans un grand monde, la population peut buter sur le plafond (courbe «Naissances bloquées»). La vue s'ouvre à l'échelle d'un écran (touche 1) : dézoomer (molette, 0) pour voir toute la carte. Comme la population ne dépasse jamais 400, un grand monde reste à peu près aussi rapide (seuls nourriture et obstacles sont plus nombreux). Les choix sont gardés dans `saves/settings.json`, qui ne contient que les écarts avec `config.py`.
- **Menu Réseau** : espèces des fondateurs, appliquées au prochain départ de zéro.
- **Menu Sauvegarde** : sauvegarder la population, charger la dernière sauvegardée, nouvelle simulation (ouvre l'écran de réglages).
- **Extinction** : la simulation se met en pause avec un message. Repartir de zéro ou charger une population.
- À la fermeture, la population est gardée (`saves/autosave.npz`) et proposée au lancement suivant (bouton «Reprendre»). Après une extinction, il n'y a rien à garder.


## Rendu par la carte graphique

`RENDERER` dans `config.py` (ou la variable d'environnement `EVOLUTION_RENDERER`) :

- `auto` (défaut) : la carte graphique dessine (`rendering/gpu.py`) si SDL trouve un moteur matériel (Metal sur Mac, OpenGL, Direct3D). Sinon, le processeur, comme avant.
- `gpu` : la carte graphique même sans moteur matériel (moteur logiciel de SDL : plus lent que le processeur).
- `cpu` : le processeur.

Le moteur utilisé s'affiche à côté des FPS (panneau Population : «GPU» ou «CPU»).

Fonctionnement : le monde (fond, sprites, anémones, traits, cercles) est dessiné par la carte graphique (`rendering/canvas.py`, même code de dessin que le processeur). L'interface (panneaux, texte) est toujours dessinée par le processeur sur un calque transparent ; seules les zones dessinées sont envoyées à la carte graphique. Le verre dépoli est fait par la carte graphique : copie de la zone, trois réductions de moitié (moyenne), teinte, agrandissement, coins arrondis par masque. Avant chaque verre, l'interface déjà dessinée est envoyée : un menu par-dessus un panneau floute bien le panneau.

Comparer sur ta machine : lancer une fois normalement, une fois avec `EVOLUTION_RENDERER=cpu python main.py`, et lire les FPS à ×1 et la vitesse réelle à ×100.

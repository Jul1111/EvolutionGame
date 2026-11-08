# Interface et commandes

## Commandes

| Touche | Action |
|---|---|
| ↑ / ↓ | Vitesse de simulation (×1 à ×100) |
| Espace / → | Pause / avancer d'un tick (en pause) |
| Clic | Sélectionner une créature, ou utiliser les menus |
| Molette, glisser, + - 0 1 | Zoom (jusqu'à 4 fois plus loin que la carte entière : le tore apparaît répété, assombri, autour de la carte encadrée), déplacer la vue, toute la carte, échelle d'un écran |
| V | Caméra sur la créature sélectionnée |
| B | Sélectionner la créature qui a eu le plus de petits |
| T | Suivre la lignée : à la mort de la sélection, passer à son plus jeune descendant vivant |
| S | Sauvegarder la population (`saves/populations/<date>_manuelle.npz`) |
| D, C, L | Debug (cône de vision et cibles), couleur des créatures, légende |
| G, N | Courbes, graphe du réseau (masqué, petit, grand) |
| P, H ou ?, F | Paramètres, aide, plein écran |
| Échap | Fermer, puis quitter le plein écran, puis quitter |

## Interface

- **Écran «Nouvelle simulation»** : à chaque lancement, rien ne tourne avant d'avoir cliqué. On y règle tout (dont le nombre de créatures au départ, la taille du monde, le gène de taille ; les espèces dans le menu Réseau), puis «Lancer», ou «Reprendre la population gardée» si le jeu a été fermé en cours de partie. Échap quitte. Le menu Sauvegarde → «Nouvelle simulation...» rouvre cet écran, avec «Annuler» pour revenir à la partie en cours.
- **Panneau Population** : vivantes sur le plafond de calcul, temps simulé, naissances et morts depuis le départ, génération de lignée moyenne et maximale. Statut «Extinction» quand tout le monde est mort.
- **Panneau Créature** : énergie, vitesse, âge, repas et poisons, temps aveugle, taille, génération de lignée et nombre de petits.
- **Réseau** : entrées et sorties de la créature sélectionnée, en barres ou en graphe.
- **Courbes dans le temps** (menu Courbes) : une valeur toutes les 10 s simulées, lue dans `saves/timeline.csv`. Population, naissances, morts (faim, vieillesse), repas et poisons par 1000 ticks de vie, vitesse, énergie, génération de lignée, âge à la mort, nourriture disponible, naissances bloquées par le plafond.
- **Paramètres** (touche P) : mutation, seuil de reproduction, âge maximal, champ de vision, nourriture (nombre, énergie, délai), poison (nombre, dégâts), obstacles, taille du monde (1×1, 2×2 ou 3×3 écrans), gène de taille (fixe, neutre, actif). Tout s'applique tout de suite, sauf les obstacles, la taille du monde et le gène de taille (au prochain départ de zéro, marqués en orange). Nourriture, obstacles et plafond sont donnés par écran : un monde 2×2 en a 4 fois plus. Les fondateurs restent 200. La vue s'ouvre à l'échelle d'un écran (touche 1) : dézoomer (molette, 0) pour voir toute la carte. Une fois la population développée, un monde 2×2 tourne environ 4 fois plus lentement. Les choix sont gardés dans `saves/settings.json`, qui ne contient que les écarts avec `config.py`.
- **Menu Réseau** : espèces des fondateurs, appliquées au prochain départ de zéro.
- **Menu Sauvegarde** : sauvegarder la population, charger la dernière sauvegardée, nouvelle simulation (ouvre l'écran de réglages).
- **Extinction** : la simulation se met en pause avec un message. Repartir de zéro ou charger une population.
- À la fermeture, la population est gardée (`saves/autosave.npz`) et proposée au lancement suivant (bouton «Reprendre»). Après une extinction, il n'y a rien à garder.


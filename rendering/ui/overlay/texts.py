"""Texts of the interface: tool bar, settings explanations, tips, help. (French: this is what the player reads.)"""

# Tool bar: (action, icon, title, shortcut). None = separator, "speed" = speed read-out.
TOOLBAR = [
    ("pause", "pause", "Pause / Reprendre", "Espace"),
    ("step", "step", "Avancer d'un tick (en pause)", "→"),
    ("speed_down", "minus", "Ralentir la simulation", "↓"),
    "speed",
    ("speed_up", "plus", "Accélérer la simulation", "↑"),
    None,
    ("debug", "cone", "Debug : cône de vision et cibles (off, sélection, toutes)", "D"),
    ("graph", "net", "Réseau de neurones : masqué, petit, grand", "N"),
    ("chart", "curves", "Courbes : masquées, panneau, grand", "G"),
    None,
    ("best", "kids", "Sélectionner la créature qui a eu le plus de petits (à sa mort : la nouvelle meilleure)", "B"),
    ("follow", "branch", "Suivre la lignée : à la mort de la sélection, son plus jeune descendant (sinon la nouvelle meilleure)", "T"),
    ("cam_follow", "target", "Caméra sur la sélection", "V"),
    None,
    ("params_panel", "sliders", "Paramètres de simulation", "P"),
    ("help", "help", "Aide et raccourcis", "H"),
]

# Label, explanation of every setting of the panel (keys = main.PARAMS)
PARAM_INFO = {
    "mutation": ("Mutation", "Amplitude du bruit ajouté à chaque poids d'un enfant."),
    "repro": ("Seuil de reproduction", "Énergie qu'il faut atteindre pour faire un petit (le parent perd 60, le petit naît avec 50)."),
    "age_max": ("Âge maximal", "Mort de vieillesse. Sans elle, des immortels bloquent le renouvellement."),
    "fov": ("Champ de vision", "Ouverture du cône de vision. Tout autour = 360°."),
    "food": ("Nourriture max", "Sources de nourriture par écran quand la population est petite, et au départ : beaucoup, pour que des créatures tirées au hasard passent le premier goulot."),
    "food_min": ("Nourriture min", "Sources par écran quand la population est grande : la nourriture suit la population. Égale au max = la nourriture ne change jamais."),
    "food_pressure": ("Population de rareté", "Créatures nées dans ce monde (pas les fondateurs) à partir desquelles la nourriture est au minimum. Entre 0 et ce nombre : baisse en ligne droite."),
    "food_adapt": ("Réaction en", "Temps simulé pour que la nourriture suive un changement de population : progressif, pour éviter le yo-yo. «aussitôt» = immédiat."),
    "food_energy": ("Énergie d'une nourriture", "Énergie gagnée à chaque repas."),
    "diet_mutation": ("Mutation du régime", "Avec deux sortes de nourriture : de combien le régime d'un petit s'écarte de celui de son parent. À 0,05 une seule nourriture finit mangée ; à 0,15 l'espèce garde presque toujours deux groupes de spécialistes, et en refait un quand il disparaît."),
    "predation": ("Prédateurs", "Oui : des prédateurs (contour à pointes rouges) arrivent pendant la partie. Ils ne mangent jamais de nourriture, seulement les créatures des autres espèces qu'ils touchent. Cocher l'espèce «Proie» pour des proies qui voient les prédateurs. Au prochain départ de zéro."),
    "predator_start": ("Arrivée des prédateurs", "Temps de la partie où les prédateurs arrivent, avec des réseaux au hasard. Mieux vaut laisser les proies passer le goulot de départ (environ 4 minutes). Au prochain départ de zéro."),
    "predator_founders": ("Prédateurs à l'arrivée", "Nombre de prédateurs qui arrivent, par écran. Au prochain départ de zéro."),
    "predation_efficiency": ("Énergie tirée d'une proie", "Part de l'énergie de la proie que gagne le prédateur qui la mange ; le reste est perdu. Plus elle est haute, plus les prédateurs se multiplient vite."),
    "predator_digest": ("Digestion", "Après un repas, le prédateur ne peut plus attaquer pendant ce temps : limite ce qu'il peut manger, et freine l'explosion des prédateurs."),
    "predator_cost": ("Coût de base d'un prédateur", "Ce qu'un prédateur dépense à l'arrêt, par rapport à une autre créature de sa taille."),
    "food_types": ("Sortes de nourriture", "Deux : une nourriture sur deux est jaune, et chaque créature hérite d'un régime (0 = mange le vert, 1 = le jaune). Un spécialiste tire tout de sa nourriture et rien de l'autre : deux espèces peuvent se partager le monde. Trois ou quatre : nourritures bleue et rose en plus, réparties entre 0 et 1 (chacune ne nourrit que les régimes proches du sien). Doubler l'énergie d'une nourriture (60). Couleur «régime» : touche C. Au prochain départ de zéro."),
    "respawn": ("Délai de réapparition", "Temps avant qu'une nourriture mangée soit de nouveau disponible."),
    "poison_count": ("Nombre de poisons", "Sources de poison dans le monde. 0 = aucun."),
    "poison_energy": ("Dégâts d'un poison", "Énergie perdue au contact d'un poison."),
    "founders": ("Créatures au départ", "Fondateurs aux réseaux tirés au hasard, quelle que soit la taille du monde. Au prochain départ."),
    "size_mode": ("Gène de taille", "Fixe : tous à 1. Neutre : la taille mute sans rien changer (témoin de dérive). Actif : plus grand = touche de plus loin, réserve plus grande, coûte plus. Au prochain départ de zéro."),
    "world_scale": ("Taille du monde", "Côté du monde en écrans. 2×2 = 4 fois plus de surface, de nourriture et de créatures, et environ 4 fois plus lent. Au prochain départ de zéro."),
    "obstacle_count": ("Nombre d'obstacles", "Obstacles (formes et places tirées au hasard). S'applique au prochain départ de zéro. 0 = aucun."),
}

# Explanations shown when the mouse rests on a label of the side bar: (logical y of the row, text)
GEN_TIPS = [
    (38, "Vivantes sur le plafond de calcul ({pop_max} : {pop_screen} par écran). Au plafond, les naissances sont bloquées : la population n'est plus réglée par la nourriture."),
    (68, "Temps simulé depuis le départ de cette population."),
    (86, "Naissances et morts depuis le départ. Une créature naît quand son parent atteint le seuil d'énergie."),
    (104, "Génération de lignée : nombre d'ancêtres depuis les fondateurs tirés au hasard (0)."),
]
CREATURE_TIPS = [
    (36, "Énergie restante. À 0, la créature meurt. Plafond : {energy_max:g} × taille (si la taille agit)."),
    (66, "Vitesse actuelle, de 0 à {speed_max:g}. Elle change progressivement vers la vitesse demandée par le réseau."),
    (96, "Âge : durée de vie de cette créature (temps simulé)."),
    (114, "Nourritures mangées / poisons touchés depuis sa naissance."),
    (132, "Temps aveugle : part de sa vie passée sans aucune nourriture dans son champ de vision (cône)."),
    (150, "Taille (gène du corps, de {size_min:g} à {size_max:g}), génération de lignée et nombre de petits. Les petits sont la seule chose que la sélection naturelle récompense."),
]
NET_TIPS = {
    "Faim": "Temps depuis la dernière nourriture vue, de 0 à 1 en {hunger} s. Seule entrée qui change quand rien n'est en vue.",
    "Bruit": "Valeur au hasard à chaque tick, entre -1 et 1 : permet une marche aléatoire.",
    "Distance": "Distance à la nourriture visible la plus proche, divisée par la portée. 1 = rien en vue.",
    "Angle": "Direction de cette nourriture par rapport au cap. 0 = droit devant, + = à droite, - = à gauche.",
    "Énergie": "Énergie de la créature, divisée par le maximum.",
    "Vitesse": "Vitesse actuelle, divisée par la vitesse maximale.",
    "Peut manger": "oui = le repas rentrerait en entier dans l'énergie restante. non = la créature est trop pleine.",
    "Dist. poison": "Distance au poison visible le plus proche. 1 = rien en vue.",
    "Angle poison": "Direction de ce poison par rapport au cap (+ = à droite).",
    "Dist. obstacle": "Distance au bord de l'obstacle visible le plus proche. 1 = rien en vue.",
    "Angle obstacle": "Direction de cet obstacle par rapport au cap (+ = à droite).",
    "Virage": "Sortie du réseau : -1 = tourne à gauche à fond, +1 = tourne à droite à fond.",
    "Vit. cible": "Sortie du réseau : vitesse demandée. -1 = à l'arrêt, +1 = vitesse maximale.",
}

HELP_KEYS = [
    ("Espace", "Pause / reprendre"), ("→", "Avancer d'un tick (en pause)"), ("↑  ↓", "Vitesse de simulation"),
    ("D", "Debug : off / sélection / toutes"), ("C", "Couleur : espèce, énergie, vitesse, nourriture, taille, lignée"),
    ("L", "Légende"), ("G", "Courbes : masquées / panneau / grand"), ("N", "Réseau : masqué / petit / grand"),
    ("Tab", "Masquer ou afficher les panneaux"), ("M", "Mini-carte"), ("E", "Naissances et morts dans le monde"),
    ("B", "Sélectionner la créature qui a eu le plus de petits"), ("T", "Suivre la lignée"),
    ("S", "Sauvegarder la population"),
    ("+  -  0  1", "Zoom avant, arrière, toute la carte, échelle d'un écran"), ("V", "Caméra sur la sélection"),
    ("P", "Paramètres"), ("F", "Plein écran"), ("H  ?", "Cette aide"), ("Échap", "Fermer, puis quitter"),
]
# Columns and sections of the settings panel (keys = main.PARAMS). Unknown keys go to «Autres».
PARAM_COLUMNS = (
    (("Évolution", ("mutation", "repro", "age_max", "size_mode")), ("Perception", ("fov",)),
     ("Nourriture", ("food", "food_min", "food_pressure", "food_adapt", "food_energy", "respawn", "food_types",
                     "diet_mutation"))),
    (("Dangers", ("poison_count", "poison_energy", "obstacle_count")), ("Monde", ("founders", "world_scale")),
     ("Prédateurs", ("predation", "predator_start", "predator_founders", "predation_efficiency", "predator_digest",
                     "predator_cost"))),
)

HELP_MOUSE = [
    "Molette : zoom sur le pointeur. Glisser dans le monde : déplacer la vue.",
    "Clic sur une créature : fiche, réseau et trajectoire.",
    "Clic dans le vide : désélectionner. Clic sur la mini-carte : y aller.",
    "Glisser le titre du grand réseau : le déplacer.",
    "Survol d'une créature : résumé rapide.",
    "Survol d'un bouton ou d'un libellé : explication.",
]

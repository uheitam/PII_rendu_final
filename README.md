## Fonctionnalites

- Generation d'un menu hebdomadaire a partir des repas coches dans le calendrier.
- Filtrage des recettes selon les allergies et restrictions alimentaires.
- Scoring des recettes selon le temps, le prix, la nutrition et la variete.
- Affichage d'une recette principale par repas selectionne.
- Proposition d'alternatives pour un repas via le panneau de swap.
- Affichage de vignettes, de titres et d'informations de base sur les recettes.

## Principe de fonctionnement

L'application charge le fichier de donnees `data/df.recipes.csv`, extrait les options disponibles pour les allergies et regimes, puis calcule un score global pour chaque recette candidate.

Le budget n'est pas un montant en euros: il correspond a une preference relative sur une echelle de prix de 1 a 3.

- `Economique` -> classe prix `1`
- `Standard` -> classe prix `2`
- `Confort` -> classe prix `3`

Le score final combine 4 criteres:

- nutrition
- temps de preparation
- prix
- variete

## Prerequis

- Python 3.9 ou superieur
- Les dependances du fichier `requirements.txt`
- Un terminal capable d'activer un environnement virtuel PowerShell sous Windows

## Installation et lancement

Depuis la racine du projet:

- python -m venv .venv
- .\.venv\Scripts\Activate.ps1
- pip install -r requirements.txt


## Lancement

python main.py

## Utilisation

1. Renseigne les contraintes dans l'onglet `Mes Contraintes`.
2. Choisir les jours et repas a planifier dans `Mon Calendrier`.
3. Cliquer sur `Generer mon menu`.
4. Consulter les recettes proposees dans `Mon Menu`.
5. Utiliser le panneau `Alternatives` pour afficher des propositions de remplacement sur un repas.

## Structure du projet

- `main.py`: point d'entree de l'application.
- `app.py`: interface graphique principale.
- `scoring.py`: logique de filtrage et de calcul des scores.
- `ui_helpers.py`: chargement du dataset, extraction des options et gestion des vignettes.
- `utils.py`: fonctions utilitaires de normalisation et de traitement du texte.
- `data/df.recipes.csv`: base de donnees des recettes.

## Donnees

Le projet s'appuie sur un fichier CSV local. Si le fichier `data/df.recipes.csv` est absent ou inaccessible, l'interface ne pourra pas charger correctement les recettes.

## Remarques

- Les images des recettes sont chargees depuis les URL fournies par le jeu de donnees. En cas d'echec reseau, une vignette de remplacement est affichee.
- Le mode de variete utilise actuellement la configuration par defaut de l'application.

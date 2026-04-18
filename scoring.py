from pathlib import Path

import pandas as pd

from utils import normalize_text, split_tokens


DEFAULT_NUTRITION_TARGETS = {
    'calories': 700.0,
    'protein': 30.0,
    'fat': 25.0,
    'carbohydrates': 80.0,
}

DEFAULT_NUTRITION_WEIGHTS = {
    'calories': 0.25,
    'protein': 0.25,
    'fat': 0.25,
    'carbohydrates': 0.25,
}

DEFAULT_FINAL_WEIGHTS = {
    'nutrition': 0.25,
    'temps': 0.25,
    'prix': 0.25,
    'variete': 0.25,
}

ALLERGY_SYNONYMS = {
    'arachide': {'arachide', 'arachides', 'peanut', 'peanuts'},
    'gluten': {'gluten'},
    'lait': {'lait', 'milk', 'dairy', 'lactose'},
}

DIET_SYNONYMS = {
    'vegetarien': {'vegetarian', 'vegan'},
    'halal': {'halal'},
}

BUDGET_TO_PRICE_PREF = {
    'economique': 1,
    'standard': 2,
    'confort': 3,
}

DATASET_PATH = Path(__file__).resolve().parent / 'data' / 'df.recipes.csv'


def _merge_and_normalize_weights(default_weights, custom_weights=None):
    """
    Fusionne les poids utilisateur et normalise pour garder une echelle stable.

    Regles MVP:
    - chaque poids est borne entre 0 et 1
    - la somme des poids est ramenee a 1 (si somme > 0)
    """
    weights = dict(default_weights)
    if custom_weights:
        weights.update(custom_weights)

    clipped = {
        key: max(0.0, min(1.0, float(value)))
        for key, value in weights.items()
    }

    total = sum(clipped.values())
    if total <= 0:
        return dict(default_weights)

    return {key: value / total for key, value in clipped.items()}


def _is_recipe_compatible(row, allergies_user=None, diets_user=None):
    """Applique le filtrage binaire strict sur allergies et regimes."""
    allergies_user = allergies_user or []
    diets_user = diets_user or []

    recipe_allergens = split_tokens(row.get('allergens', ''))
    recipe_diets = split_tokens(row.get('cultural_restriction', ''))

    for allergen in allergies_user:
        normalized_allergen = normalize_text(allergen)
        expected_tokens = ALLERGY_SYNONYMS.get(normalized_allergen, {normalized_allergen})
        if recipe_allergens.intersection(expected_tokens):
            return False

    for diet in diets_user:
        normalized_diet = normalize_text(diet)
        accepted_tokens = DIET_SYNONYMS.get(normalized_diet, {normalized_diet})
        if not recipe_diets.intersection(accepted_tokens):
            return False

    return True


def _score_proximite(valeur, cible):
    """Score lineaire de proximite entre une valeur recette et une cible utilisateur."""
    if pd.isna(valeur) or cible <= 0:
        return 0.0
    ecart_relatif = abs(float(valeur) - float(cible)) / float(cible)
    return max(0.0, 1.0 - ecart_relatif)


def calcul_score_nutrition(row, nutrition_targets=None, nutrition_weights=None):
    """Calcule le score nutritionnel (0-100) via somme ponderee des sous-scores macro."""
    targets = dict(DEFAULT_NUTRITION_TARGETS)
    if nutrition_targets:
        targets.update(nutrition_targets)

    weights = _merge_and_normalize_weights(DEFAULT_NUTRITION_WEIGHTS, nutrition_weights)

    score_calories = _score_proximite(row.get('calories', 0), targets['calories'])
    score_proteines = _score_proximite(row.get('protein', 0), targets['protein'])
    score_lipides = _score_proximite(row.get('fat', 0), targets['fat'])
    score_glucides = _score_proximite(row.get('carbohydrates', 0), targets['carbohydrates'])

    score_normalise = (
        (weights['calories'] * score_calories)
        + (weights['protein'] * score_proteines)
        + (weights['fat'] * score_lipides)
        + (weights['carbohydrates'] * score_glucides)
    )
    return max(0.0, min(100.0, score_normalise * 100.0))

def calcul_score_temps(row, temps_max_user):
    """
    Calcule le score de temps d'une recette en fonction de la demande de l'utilisateur.
    """
    # 1. On recupere le temps de preparation de la recette.
    temps_prep = row['prep_time']

    # Si la valeur est absente, score minimal.
    if pd.isna(temps_prep):
        return 0

    # 2. Cas ideal: recette dans le temps max utilisateur.
    if temps_prep <= temps_max_user:
        return 100

    # 3. Zone de tolerance simple (+50%) avec penalite lineaire.
    elif temps_prep <= (1.5 * temps_max_user):
        surplus = temps_prep - temps_max_user
        marge_max = 0.5 * temps_max_user
        penalite = (surplus / marge_max) * 100
        return 100 - penalite

    # 4. Trop long: score nul.
    else:
        return 0


def calcul_score_prix(row, user_price_pref=2):
    """Calcule le score prix (0-100) selon la formule du document Scoring."""
    recipe_price = row.get('price', 2)
    if pd.isna(recipe_price):
        return 0.0

    ecart = abs(float(recipe_price) - float(user_price_pref))
    score_normalise = (2.0 - ecart) / 2.0
    return max(0.0, min(100.0, score_normalise * 100.0))


def calcul_score_variete(row, occurrences=None, mode='different'):
    """Calcule le score variete (0-100) a partir du nombre d'occurrences de la recette."""
    occurrences = occurrences or {}
    recipe_id = row.get('recipeId', '')
    nombre_occurrences = int(occurrences.get(recipe_id, 0))

    if mode == 'familiers':
        score_normalise = nombre_occurrences / (1 + nombre_occurrences)
    else:
        score_normalise = 1 / (1 + nombre_occurrences)

    return max(0.0, min(100.0, score_normalise * 100.0))


def calcul_score_global(
    row,
    temps_max_user,
    user_price_pref=2,
    final_weights=None,
    nutrition_targets=None,
    nutrition_weights=None,
    occurrences=None,
    variete_mode='different',
):
    """Agrège les 4 sous-scores dans un score global unique (0-100)."""
    weights = _merge_and_normalize_weights(DEFAULT_FINAL_WEIGHTS, final_weights)

    score_nutrition = calcul_score_nutrition(
        row,
        nutrition_targets=nutrition_targets,
        nutrition_weights=nutrition_weights,
    )
    score_temps = calcul_score_temps(row, temps_max_user)
    score_prix = calcul_score_prix(row, user_price_pref=user_price_pref)
    score_variete = calcul_score_variete(row, occurrences=occurrences, mode=variete_mode)

    score = (
        weights['nutrition'] * score_nutrition
        + weights['temps'] * score_temps
        + weights['prix'] * score_prix
        + weights['variete'] * score_variete
    )

    return {
        'score_nutrition': score_nutrition,
        'score_temps': score_temps,
        'score_prix': score_prix,
        'score_variete': score_variete,
        'score_global': max(0.0, min(100.0, score)),
    }


def _load_and_score_recipes(
    temps_max_user,
    budget_user='Standard',
    allergies_user=None,
    diets_user=None,
    final_weights=None,
    nutrition_targets=None,
    nutrition_weights=None,
    occurrences=None,
    variete_mode='different',
    excluded_recipe_ids=None,
):
    """
    Charge les recettes, applique le filtrage strict, calcule les sous-scores + score global.
    Retourne un DataFrame trié par score décroissant, en excluant les recettes spécifiées.
    
    Fonction interne utilisée par les fonctions publiques get_top_1_recipe et get_alternatives.
    """
    excluded_recipe_ids = excluded_recipe_ids or []
    
    try:
        df = pd.read_csv(DATASET_PATH, sep='|')
        df.columns = df.columns.str.strip()

        # --- FILTRAGE STRICT : Allergies & Régimes ---
        allergies_user = allergies_user or []
        diets_user = diets_user or []
        masque_compatibilite = df.apply(
            lambda row: _is_recipe_compatible(row, allergies_user=allergies_user, diets_user=diets_user),
            axis=1,
        )
        df = df[masque_compatibilite].copy()

        if df.empty:
            return df

        # --- EXCLUSION DES RECETTES DÉJÀ UTILISÉES ---
        if excluded_recipe_ids:
            df = df[~df.get('recipeId', '').isin(excluded_recipe_ids)].copy()
            if df.empty:
                return df

        # --- CALCUL DES SCORES ---
        user_price_pref = BUDGET_TO_PRICE_PREF.get(normalize_text(budget_user), 2)

        score_dicts = df.apply(
            lambda row: calcul_score_global(
                row,
                temps_max_user=temps_max_user,
                user_price_pref=user_price_pref,
                final_weights=final_weights,
                nutrition_targets=nutrition_targets,
                nutrition_weights=nutrition_weights,
                occurrences=occurrences,
                variete_mode=variete_mode,
            ),
            axis=1,
        )

        score_df = pd.DataFrame(score_dicts.tolist(), index=df.index)
        df = pd.concat([df, score_df], axis=1)

        # --- TRI FINAL ---
        df_shuffled = df.sample(frac=1, random_state=None).reset_index(drop=True)
        df_sorted = df_shuffled.sort_values(by='score_global', ascending=False, kind='mergesort')

        return df_sorted

    except FileNotFoundError:
        print(f"❌ ERREUR : Fichier introuvable à l'adresse : {DATASET_PATH}")
        return pd.DataFrame()
    except KeyError as e:
        print(f"❌ ERREUR : Il manque une colonne attendue dans le CSV : {e}")
        return pd.DataFrame()


def get_top_1_recipe(
    temps_max_user,
    budget_user='Standard',
    allergies_user=None,
    diets_user=None,
    final_weights=None,
    nutrition_targets=None,
    nutrition_weights=None,
    occurrences=None,
    variete_mode='different',
    excluded_recipe_ids=None,
):
    """
    Retourne la meilleure recette (1 seule) après scoring et tri.
    Exclut les recettes dont l'ID est dans excluded_recipe_ids.
    """
    df_sorted = _load_and_score_recipes(
        temps_max_user=temps_max_user,
        budget_user=budget_user,
        allergies_user=allergies_user,
        diets_user=diets_user,
        final_weights=final_weights,
        nutrition_targets=nutrition_targets,
        nutrition_weights=nutrition_weights,
        occurrences=occurrences,
        variete_mode=variete_mode,
        excluded_recipe_ids=excluded_recipe_ids,
    )

    if df_sorted.empty:
        return pd.DataFrame()

    top_1 = df_sorted.head(1)
    return top_1


def get_alternatives(
    temps_max_user,
    budget_user='Standard',
    allergies_user=None,
    diets_user=None,
    final_weights=None,
    nutrition_targets=None,
    nutrition_weights=None,
    occurrences=None,
    variete_mode='different',
    excluded_recipe_ids=None,
    num_alternatives=4,
):
    """
    Retourne les N meilleures alternatives (par défaut 4) après scoring et tri.
    Exclut les recettes dont l'ID est dans excluded_recipe_ids.
    """
    df_sorted = _load_and_score_recipes(
        temps_max_user=temps_max_user,
        budget_user=budget_user,
        allergies_user=allergies_user,
        diets_user=diets_user,
        final_weights=final_weights,
        nutrition_targets=nutrition_targets,
        nutrition_weights=nutrition_weights,
        occurrences=occurrences,
        variete_mode=variete_mode,
        excluded_recipe_ids=excluded_recipe_ids,
    )

    if df_sorted.empty:
        return pd.DataFrame()

    alternatives = df_sorted.head(num_alternatives)
    return alternatives


def get_top_5_recettes(
    temps_max_user,
    budget_user='Standard',
    allergies_user=None,
    diets_user=None,
    final_weights=None,
    nutrition_targets=None,
    nutrition_weights=None,
    occurrences=None,
    variete_mode='different',
):
    """Retourne les 5 meilleures recettes en reutilisant le moteur commun."""
    return get_alternatives(
        temps_max_user=temps_max_user,
        budget_user=budget_user,
        allergies_user=allergies_user,
        diets_user=diets_user,
        final_weights=final_weights,
        nutrition_targets=nutrition_targets,
        nutrition_weights=nutrition_weights,
        occurrences=occurrences,
        variete_mode=variete_mode,
        excluded_recipe_ids=None,
        num_alternatives=5,
    )



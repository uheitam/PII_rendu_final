from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from PIL import Image, ImageOps

from utils import normalize_text


# Fonctions utilitaires pour l'interface graphique.
# Ce fichier regroupe tout ce qui aide app.py a charger les donnees,
# nettoyer les textes et afficher les images des recettes.
DATASET_PATH = Path(__file__).resolve().parent / "data" / "df.recipes.csv"


def load_dataset():
    """Charge le fichier CSV des recettes et nettoie les noms de colonnes."""
    try:
        dataset = pd.read_csv(DATASET_PATH, sep="|")
    except FileNotFoundError:
        return pd.DataFrame()

    dataset.columns = dataset.columns.str.strip()
    return dataset


def extract_options(dataset, column_name):
    """Extrait les valeurs uniques d'une colonne pour creer une liste de choix."""
    if dataset.empty or column_name not in dataset.columns:
        return []

    tokens = set()
    for value in dataset[column_name].dropna():
        # On normalise le texte pour comparer proprement les valeurs du CSV.
        raw = normalize_text(value)
        if not raw or raw in {"notallergens", "notrestriction"}:
            continue

        # Certaines cellules contiennent plusieurs valeurs separees par differents caracteres.
        for separator in ["/", ";", "|"]:
            raw = raw.replace(separator, ",")

        for chunk in raw.split(","):
            token = chunk.strip()
            if token and token not in {"notallergens", "notrestriction"}:
                tokens.add(token)

    return sorted(tokens, key=str.lower)


def display_label(value):
    """Retourne un libelle plus lisible pour l'affichage dans l'interface."""
    return str(value).title()


def safe_text(value, fallback="Non renseigné"):
    """Remplace les valeurs manquantes ou vides par un texte de secours."""
    if pd.isna(value):
        return fallback

    text = str(value).strip()
    return text if text else fallback


def _placeholder_thumbnail(size):
    """Crée une image de remplacement quand aucune miniature n'est disponible."""
    return Image.new("RGB", size, color="#d9d0c4")


def load_thumbnail_image(url, size):
    """Telecharge une image de recette ou retourne une image de remplacement."""
    url = str(url).strip()
    if not url.startswith("http"):
        return _placeholder_thumbnail(size)

    try:
        # On telecharge l'image distante avec un delai limite pour eviter de bloquer l'interface.
        response = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        image = Image.open(BytesIO(response.content)).convert("RGB")
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS

        # On adapte l'image a la taille attendue par l'interface.
        return ImageOps.fit(image, size, method=resample)
    except Exception:
        # En cas d'erreur reseau ou d'image invalide, on affiche un visuel de secours.
        return _placeholder_thumbnail(size)
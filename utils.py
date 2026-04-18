import pandas as pd


def normalize_text(value):
    """Normalise une valeur texte pour les comparaisons simples."""
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def split_tokens(value):
    """Decoupe une cellule texte en tokens normalises."""
    raw = normalize_text(value)
    if not raw or raw in {"notallergens", "notrestriction"}:
        return set()

    for separator in ["/", ";", "|"]:
        raw = raw.replace(separator, ",")

    tokens = set()
    for chunk in raw.split(","):
        token = chunk.strip()
        if token:
            tokens.add(token)
    return tokens

"""Normalização conservadora de texto em português."""
import re
import unicodedata

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9% ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def has_negated_action(text: str) -> bool:
    """Bloqueia fallback de IA quando uma frase nega explicitamente uma ação."""
    normalized = normalize_text(text)
    action_words = r"(?:abre|abrir|abra|executa|inicia|liga|coloca|muda|aumenta|abaixa|passa)"
    return bool(
        re.search(rf"\bnao\b(?:\s+\w+){{0,3}}\s+{action_words}\b", normalized)
        or re.search(rf"\bnao\s+(?:quero|pode)\b(?:\s+\w+){{0,2}}\s+{action_words}\b", normalized)
    )

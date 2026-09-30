from jarvis.utils.text import normalize_text

def test_normalize_accents_and_spaces():
    assert normalize_text("  Próxima   MÚSICA! ") == "proxima musica"

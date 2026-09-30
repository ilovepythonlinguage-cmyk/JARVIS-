import pytest
from jarvis.core.intent_parser import IntentParser
from jarvis.core.models import Intent

@pytest.fixture
def parser():
    return IntentParser(
        {"vscode": {"aliases": ["vscode", "vs code", "visual studio code", "code"]}},
        {"youtube": {"aliases": ["youtube"]}},
        {
            "downloads": {"aliases": ["downloads", "minha pasta downloads"]},
            "projects": {"aliases": ["projetos", "minha pasta de projetos"]},
        },
    )

@pytest.mark.parametrize(("text", "intent", "slots"), [
    ("abre o vscode", Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("Abra o Visual Studio Code", Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("abre o youtube", Intent.OPEN_WEBSITE, {"target": "youtube"}),
    ("abre minha pasta Downloads", Intent.OPEN_FOLDER, {"target": "downloads"}),
    ("abre minha pasta de projetos", Intent.OPEN_FOLDER, {"target": "projects"}),
    ("pesquisa python listas", Intent.WEB_SEARCH, {"query": "python listas"}),
    ("pesquise no youtube curso de python", Intent.YOUTUBE_SEARCH, {"query": "curso de python"}),
    ("volume 50", Intent.SET_VOLUME, {"level": 50}),
    ("próxima música", Intent.MEDIA_NEXT, {}),
    ("que horas são", Intent.GET_TIME, {}),
    ("quanto espaço tenho no disco", Intent.DISK_USAGE, {}),
    ("cancela", Intent.CANCEL, {}),
])
def test_commands(parser, text, intent, slots):
    command = parser.parse(text)
    assert command.intent is intent
    assert command.slots == slots

@pytest.mark.parametrize("text", [
    "", "execute rm -rf", "abre aplicativo inventado", "volume 101",
    "desliga tudo", "talvez reinicie o computador", "rode este script",
])
def test_rejects_unknown_or_unsafe_commands(parser, text):
    assert parser.parse(text).intent is Intent.UNKNOWN

def test_dangerous_actions_require_exact_phrase(parser):
    assert parser.parse("desliga o computador").intent is Intent.SHUTDOWN
    assert parser.parse("reinicia o computador").intent is Intent.REBOOT

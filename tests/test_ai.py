import json
import socket
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from jarvis.actions.base import ActionContext, ActionResult
from jarvis.ai.base import AIProvider, AIProviderError
from jarvis.ai.ollama import OllamaProvider
from jarvis.core.assistant import Assistant
from jarvis.core.intent_parser import IntentParser
from jarvis.core.models import Intent


APPS = {
    "vscode": {"aliases": ["vscode", "vs code", "visual studio code", "code"]},
    "brave": {"aliases": ["brave", "navegador"]},
}


class FakeAI(AIProvider):
    def __init__(self, answers):
        self.answers = iter(answers)
        self.calls = []

    def ask(self, prompt, history=()):
        self.calls.append((prompt, list(history)))
        answer = next(self.answers)
        if isinstance(answer, Exception):
            raise answer
        return answer


def payload(type_, **kwargs):
    return json.dumps({"type": type_, **kwargs})


def make_assistant(ai=None, max_history=6):
    settings = SimpleNamespace(confirmation_timeout=10)
    parser = IntentParser(APPS, {}, {})
    context = ActionContext(settings, APPS, {}, {})
    return Assistant(parser, context, Mock(), ai_provider=ai, max_history=max_history)


def action(action_name, **arguments):
    return payload("action", action=action_name, arguments=arguments)


def test_local_parser_runs_without_calling_ai():
    ai = FakeAI([])
    assistant = make_assistant(ai)
    with patch("jarvis.core.assistant.registry.execute", return_value=ActionResult(True, "ok")) as execute:
        assistant.process_text("abre o vscode")
    assert execute.call_args.args[0].intent is Intent.OPEN_APPLICATION
    assert execute.call_args.args[0].slots == {"target": "vscode"}
    assert not ai.calls


@pytest.mark.parametrize(("phrase", "answer", "intent", "slots"), [
    ("po, abre o vs code ai", action("open_application", name="vs code"), Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("mano abre o brave pra mim", action("open_application", target="brave"), Intent.OPEN_APPLICATION, {"target": "brave"}),
    ("cara coloca o volume em 50", action("set_volume", level=50), Intent.SET_VOLUME, {"level": 50}),
    ("passa pra próxima música aí", action("media_next"), Intent.MEDIA_NEXT, {}),
])
def test_natural_language_uses_validated_ai_action(phrase, answer, intent, slots):
    assistant = make_assistant(FakeAI([answer]))
    with patch("jarvis.core.assistant.registry.execute", return_value=ActionResult(True, "ok")) as execute:
        assistant.process_text(phrase)
    command = execute.call_args.args[0]
    assert (command.intent, command.slots) == (intent, slots)


def test_conversational_reply():
    assistant = make_assistant(FakeAI([payload("reply", message="Fala. O que manda?")]))
    result = assistant.process_text("eae jarvis")
    assert result.message == "Fala. O que manda?"


@pytest.mark.parametrize("phrase", ["não abre o vscode", "po não abre o brave", "cancela", "cancelar"])
def test_negation_never_calls_ai_or_executes(phrase):
    ai = FakeAI([])
    assistant = make_assistant(ai)
    with patch("jarvis.core.assistant.registry.execute") as execute:
        result = assistant.process_text(phrase)
    execute.assert_not_called()
    assert not ai.calls
    assert result.message == "Ação cancelada."


@pytest.mark.parametrize("bad", [
    "não é json", "", payload("action", action="run_shell", command="rm -rf /"),
    action("open_application", target="inexistente"), action("set_volume", level=150),
])
def test_invalid_ai_output_never_executes(bad):
    assistant = make_assistant(FakeAI([bad]))
    with patch("jarvis.core.assistant.registry.execute") as execute:
        assistant.process_text("pedido natural")
    execute.assert_not_called()


@pytest.mark.parametrize("failure", [AIProviderError("offline"), AIProviderError("timeout")])
def test_ai_failure_is_graceful(failure):
    result = make_assistant(FakeAI([failure])).process_text("uma pergunta")
    assert not result.success
    assert "indisponível" in result.message


def test_ai_sensitive_action_still_requires_confirmation():
    assistant = make_assistant(FakeAI([action("shutdown")]))
    with patch("jarvis.core.assistant.registry.execute", return_value=ActionResult(True, "ok")) as execute:
        first = assistant.process_text("você pode desligar esta máquina?")
        execute.assert_not_called()
        assistant.process_text("sim")
    assert first.requires_confirmation
    execute.assert_called_once()


def test_history_is_bounded_and_sent_to_next_request():
    ai = FakeAI([payload("reply", message="Legal."), payload("reply", message="É um bloco reutilizável.")])
    assistant = make_assistant(ai, max_history=2)
    assistant.process_text("estou estudando python")
    assistant.process_text("o que é uma função?")
    assert ai.calls[1][1] == [
        {"role": "user", "content": "estou estudando python"},
        {"role": "assistant", "content": "Legal."},
    ]
    assert len(assistant.history) == 2


class FakeHTTPResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.body


def test_ollama_provider_extracts_structured_content():
    response = FakeHTTPResponse(b'{"message":{"content":"{\\"type\\":\\"reply\\",\\"message\\":\\"Oi\\"}"}}')
    with patch("jarvis.ai.ollama.request.urlopen", return_value=response):
        result = OllamaProvider("http://localhost:11434", "llama3.2:1b").ask("oi")
    assert json.loads(result)["message"] == "Oi"


@pytest.mark.parametrize("response", [
    socket.timeout(),
    FakeHTTPResponse(b"json invalido"),
    FakeHTTPResponse(b'{"message":{"content":""}}'),
])
def test_ollama_provider_normalizes_transport_invalid_json_and_empty_response(response):
    effect = response if isinstance(response, Exception) else None
    returned = None if effect else response
    with patch("jarvis.ai.ollama.request.urlopen", side_effect=effect, return_value=returned):
        with pytest.raises(AIProviderError):
            OllamaProvider("http://localhost:11434", "llama3.2:1b").ask("oi")

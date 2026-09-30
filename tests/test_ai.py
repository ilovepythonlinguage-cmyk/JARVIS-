import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from jarvis.actions.base import ActionContext, ActionResult
from jarvis.ai.base import AIProviderError
from jarvis.ai.interpreter import AIInterpreter, NO_AI_MESSAGE
from jarvis.ai.ollama import OllamaProvider
from jarvis.core.assistant import Assistant
from jarvis.core.intent_parser import IntentParser
from jarvis.core.models import Intent

APPS = {"vscode": {"aliases": ["vscode"]}, "brave": {"aliases": ["brave"]}}


def payload(action, arguments=None):
    return json.dumps({"type": "action", "action": action, "arguments": arguments or {}})


def make_assistant(response: str):
    provider = Mock()
    provider.complete.return_value = response
    ai = AIInterpreter(provider, APPS, {}, {}, max_history=6)
    settings = SimpleNamespace(confirmation_timeout=10)
    context = ActionContext(settings, APPS, {}, {})
    assistant = Assistant(IntentParser(APPS, {}, {}), context, Mock(), ai=ai)
    return assistant, provider


@pytest.mark.parametrize(("phrase", "response", "intent", "slots"), [
    ("po, abre o vs code ai", payload("open_application", {"name": "vscode"}), Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("mano abre o visual studio code pra mim", payload("open_application", {"name": "vscode"}), Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("pode abrir o code aí?", payload("open_application", {"name": "vscode"}), Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("abre aquele vs code pra começar", payload("open_application", {"name": "vscode"}), Intent.OPEN_APPLICATION, {"target": "vscode"}),
    ("mano abre o brave pra mim", payload("open_application", {"name": "brave"}), Intent.OPEN_APPLICATION, {"target": "brave"}),
    ("po abre o brave aí", payload("open_application", {"name": "brave"}), Intent.OPEN_APPLICATION, {"target": "brave"}),
    ("cara volume em 50", payload("set_volume", {"value": 50}), Intent.SET_VOLUME, {"level": 50}),
    ("passa a próxima música aí", payload("media_next"), Intent.MEDIA_NEXT, {}),
])
def test_ai_routes_informal_commands(phrase, response, intent, slots):
    assistant, _ = make_assistant(response)
    with patch("jarvis.core.assistant.registry.execute", return_value=ActionResult(True, "ok")) as execute:
        assistant.process_text(phrase)
    command = execute.call_args.args[0]
    assert command.intent is intent
    assert command.slots == slots


def test_known_local_command_does_not_call_ai():
    assistant, provider = make_assistant(payload("run_shell", {"command": "bad"}))
    with patch("jarvis.core.assistant.registry.execute", return_value=ActionResult(True, "ok")) as execute:
        assistant.process_text("abre o vscode")
    assert execute.call_args.args[0].intent is Intent.OPEN_APPLICATION
    provider.complete.assert_not_called()


@pytest.mark.parametrize("phrase", ["não abre o vscode", "po não abre o brave", "não quero abrir o brave"])
def test_negated_action_never_calls_ai_or_executes(phrase):
    assistant, provider = make_assistant(payload("open_application", {"name": "vscode"}))
    with patch("jarvis.core.assistant.registry.execute") as execute:
        result = assistant.process_text(phrase)
    assert result.success
    provider.complete.assert_not_called()
    execute.assert_not_called()


def test_conversation_reply_and_short_history():
    assistant, provider = make_assistant(json.dumps({"type": "reply", "message": "Olá. Como posso ajudar?"}))
    result = assistant.process_text("olá jarvis")
    assert result.message == "Olá. Como posso ajudar?"
    assistant.process_text("estou estudando python")
    assistant.process_text("listas")
    assistant.process_text("e tu?")
    last_messages = provider.complete.call_args.args[0]
    assert len(last_messages[1:-1]) <= 6


@pytest.mark.parametrize(("response", "expected"), [
    ("não é JSON", "Não entendi o pedido."),
    ("", "Não entendi o pedido."),
    (payload("run_shell", {"command": "rm -rf /"}), "Não posso executar essa ação."),
    (payload("open_application", {"name": "malware"}), "Não posso executar essa ação."),
])
def test_invalid_or_disallowed_ai_output_is_not_executed(response, expected):
    assistant, _ = make_assistant(response)
    with patch("jarvis.core.assistant.registry.execute") as execute:
        result = assistant.process_text("pedido informal")
    assert result.message == expected
    execute.assert_not_called()


@pytest.mark.parametrize("error", [AIProviderError("offline"), AIProviderError("timeout")])
def test_provider_failure_keeps_assistant_running(error):
    assistant, provider = make_assistant("")
    provider.complete.side_effect = error
    result = assistant.process_text("uma pergunta")
    assert result.message == NO_AI_MESSAGE


def test_ollama_timeout_becomes_recoverable_error():
    provider = OllamaProvider("http://localhost:11434", "llama3.2:1b", timeout=0.01)
    with patch("jarvis.ai.ollama.urlopen", side_effect=TimeoutError):
        with pytest.raises(AIProviderError):
            provider.list_models()

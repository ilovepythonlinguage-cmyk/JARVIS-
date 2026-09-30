from types import SimpleNamespace
from unittest.mock import Mock, patch
from jarvis.actions.base import ActionContext, ActionResult
from jarvis.core.assistant import Assistant
from jarvis.core.intent_parser import IntentParser


def make_assistant():
    settings = SimpleNamespace(confirmation_timeout=10)
    context = ActionContext(settings, {}, {}, {})
    return Assistant(IntentParser({}, {}, {}), context, Mock())

def test_shutdown_is_not_executed_without_confirmation():
    assistant = make_assistant()
    with patch("jarvis.core.assistant.registry.execute") as execute:
        result = assistant.process_text("desliga o computador")
        assert result.requires_confirmation
        execute.assert_not_called()
        assistant.process_text("não")
        execute.assert_not_called()

def test_shutdown_executes_only_after_yes():
    assistant = make_assistant()
    with patch("jarvis.core.assistant.registry.execute", return_value=ActionResult(True, "ok")) as execute:
        assistant.process_text("desliga o computador")
        assistant.process_text("sim")
        execute.assert_called_once()

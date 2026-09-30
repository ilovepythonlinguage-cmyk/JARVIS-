from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from jarvis.core.models import Command, Intent

@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str
    requires_confirmation: bool = False

@dataclass
class ActionContext:
    settings: Any
    apps: dict[str, Any]
    websites: dict[str, Any]
    folders: dict[str, Any]

ActionHandler = Callable[[Command, ActionContext], ActionResult]

class ActionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[Intent, ActionHandler] = {}

    def register(self, *intents: Intent) -> Callable[[ActionHandler], ActionHandler]:
        def decorator(handler: ActionHandler) -> ActionHandler:
            for intent in intents:
                if intent in self._handlers:
                    raise ValueError(f"Action duplicada: {intent.value}")
                self._handlers[intent] = handler
            return handler
        return decorator

    def execute(self, command: Command, context: ActionContext) -> ActionResult:
        handler = self._handlers.get(command.intent)
        return handler(command, context) if handler else ActionResult(False, "Não entendi o comando.")

    def supports(self, intent: Intent) -> bool:
        return intent in self._handlers

    @property
    def action_names(self) -> tuple[str, ...]:
        return tuple(intent.value for intent in self._handlers)

registry = ActionRegistry()

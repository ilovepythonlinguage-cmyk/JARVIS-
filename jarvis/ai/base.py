from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


class AIProviderError(RuntimeError):
    """Falha recuperável no provedor local de IA."""


@dataclass(frozen=True)
class AIResponse:
    """Resposta estruturada e ainda não autorizada de um provedor de IA."""

    type: str
    message: str | None = None
    action: str | None = None
    arguments: dict[str, Any] | None = None


class AIProvider(ABC):
    """Ponto de extensão opcional; comandos locais não dependem de IA."""
    @abstractmethod
    def ask(self, prompt: str, history: Sequence[dict[str, str]] = ()) -> str:
        raise NotImplementedError

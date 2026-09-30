from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypedDict

class ChatMessage(TypedDict):
    role: str
    content: str

class AIProviderError(RuntimeError):
    """Falha recuperável de um provider local de IA."""

class AIProvider(ABC):
    """Ponto de extensão opcional; comandos locais não dependem de IA."""
    @abstractmethod
    def complete(self, messages: Sequence[ChatMessage]) -> str:
        raise NotImplementedError

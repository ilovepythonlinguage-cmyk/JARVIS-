from abc import ABC, abstractmethod
from collections.abc import Sequence


class AIProviderError(RuntimeError):
    """Falha recuperável no provedor local de IA."""

class AIProvider(ABC):
    """Ponto de extensão opcional; comandos locais não dependem de IA."""
    @abstractmethod
    def ask(self, prompt: str, history: Sequence[dict[str, str]] = ()) -> str:
        raise NotImplementedError

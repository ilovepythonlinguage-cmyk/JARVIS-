from abc import ABC, abstractmethod

class AIProvider(ABC):
    """Ponto de extensão opcional; comandos locais não dependem de IA."""
    @abstractmethod
    def ask(self, prompt: str) -> str:
        raise NotImplementedError

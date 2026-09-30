from abc import ABC, abstractmethod

class SpeechRecognizer(ABC):
    @abstractmethod
    def recognize_once(self) -> str:
        """Abre o microfone, reconhece uma frase e fecha o dispositivo."""
        raise NotImplementedError

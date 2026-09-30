"""Cliente HTTP mínimo para a API local do Ollama."""
from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jarvis.ai.base import AIProvider, AIProviderError, ChatMessage


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 8):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _request(self, path: str, payload: dict[str, object] | None = None) -> object:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - URL local configurada
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"Ollama indisponível: {exc}") from exc

    def complete(self, messages: Sequence[ChatMessage]) -> str:
        result = self._request("/api/chat", {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2, "num_predict": 160},
        })
        if not isinstance(result, dict):
            raise AIProviderError("Resposta inválida do Ollama")
        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise AIProviderError("Resposta vazia ou inválida do Ollama")
        return message["content"].strip()

    def list_models(self) -> set[str]:
        result = self._request("/api/tags")
        if not isinstance(result, dict) or not isinstance(result.get("models"), list):
            raise AIProviderError("Lista de modelos inválida")
        names: set[str] = set()
        for model in result["models"]:
            if isinstance(model, dict) and isinstance(model.get("name"), str):
                names.add(model["name"])
        return names

    def model_available(self) -> bool:
        names = self.list_models()
        return self.model in names or f"{self.model}:latest" in names

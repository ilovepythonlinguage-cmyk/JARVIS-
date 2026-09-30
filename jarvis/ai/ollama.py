"""Cliente mínimo da API local do Ollama, sem dependências HTTP extras."""
from __future__ import annotations

import json
import socket
from collections.abc import Sequence
from urllib import error, request

from jarvis.ai.base import AIProvider, AIProviderError

SYSTEM_PROMPT = """Você é Jarvis, assistente em português brasileiro, direto e natural.
Responda SOMENTE JSON: {"type":"reply","message":"resposta curta"} ou
{"type":"action","action":"nome permitido","arguments":{...}}.
Nunca crie comandos de terminal. Use somente ações e alvos informados pelo usuário."""


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def ask(self, prompt: str, history: Sequence[dict[str, str]] = ()) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history,
                    {"role": "user", "content": prompt}]
        body = json.dumps({"model": self.model, "messages": messages, "stream": False,
                           "format": "json", "options": {"temperature": 0.2}}).encode()
        req = request.Request(f"{self.base_url}/api/chat", data=body,
                              headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
            raise AIProviderError("Ollama indisponível") from exc
        content = payload.get("message", {}).get("content") if isinstance(payload, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("Ollama retornou uma resposta vazia")
        return content.strip()

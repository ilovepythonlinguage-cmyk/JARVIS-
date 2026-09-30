"""Cliente mínimo da API local do Ollama, sem dependências HTTP extras."""
from __future__ import annotations

import json
import socket
from collections.abc import Sequence
from urllib import error, request

from jarvis.ai.base import AIProvider, AIProviderError

SYSTEM_PROMPT = """Você é Jarvis, um assistente em português brasileiro.
Responda SOMENTE com um objeto JSON, sem markdown nem texto adicional.

Regras:
1. Se o usuário pedir uma ação disponível, responda com
   {"type":"action","action":"nome permitido","arguments":{...}}.
2. Se estiver conversando, cumprimentando, perguntando algo ou pedindo explicação,
   responda com {"type":"reply","message":"resposta"}.
3. Nunca invente uma action para uma conversa normal.
4. Responda em português brasileiro.
5. Mantenha respostas conversacionais curtas por padrão.
6. Use linguagem natural e levemente informal quando apropriado.
7. Nunca crie comandos de terminal. Use somente ações e alvos informados pelo usuário.

Exemplos:
Usuário: eae jarvis
Resposta: {"type":"reply","message":"Fala. O que manda?"}
Usuário: oi jarvis
Resposta: {"type":"reply","message":"Oi! Como posso ajudar?"}
Usuário: tudo bem?
Resposta: {"type":"reply","message":"Tudo certo por aqui. E com você?"}
Usuário: o que é uma variável em python?
Resposta: {"type":"reply","message":"É um nome que guarda um valor para você usar no código."}
Usuário: me explica rapidinho o que é uma lista
Resposta: {"type":"reply","message":"Uma lista reúne vários valores em uma única coleção ordenada."}
Usuário: po, abre o vs code ai
Resposta: {"type":"action","action":"open_application","arguments":{"name":"vscode"}}
Usuário: mano abre o brave pra mim
Resposta: {"type":"action","action":"open_application","arguments":{"name":"brave"}}
Usuário: volume 50
Resposta: {"type":"action","action":"set_volume","arguments":{"level":50}}
Usuário: não abre o vscode
Resposta: {"type":"reply","message":"Beleza, não vou abrir."}"""


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

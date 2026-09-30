"""Fallback híbrido: valida JSON do LLM antes de produzir comandos locais."""
from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any

from jarvis.ai.base import AIProvider, AIProviderError, ChatMessage
from jarvis.core.models import Command, Intent

LOG = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o roteador do Jarvis. Responda SOMENTE um objeto JSON.
Para conversa: {"type":"reply","message":"resposta curta em português brasileiro"}.
Para ação: {"type":"action","action":"nome","arguments":{...}}.
Ações permitidas: open_application(name), open_website(name), open_folder(name),
web_search(query), youtube_search(query), set_volume(value), volume_up, volume_down,
mute, unmute, media_play_pause, media_next, media_previous, media_stop, get_time,
get_date, memory_usage, cpu_usage, disk_usage. Nunca solicite shell, terminal, código,
shutdown, reboot, exclusão ou processos. Se não entender, responda
{"type":"reply","message":"Não entendi o pedido."}. Seja curto e natural."""

NO_AI_MESSAGE = "Não entendi o comando. A inteligência local não está disponível."


@dataclass(frozen=True)
class AIInterpretation:
    command: Command | None = None
    reply: str | None = None


class AIInterpreter:
    def __init__(self, provider: AIProvider, apps: dict[str, Any], websites: dict[str, Any],
                 folders: dict[str, Any], max_history: int = 6):
        self.provider = provider
        self.apps = apps
        self.websites = websites
        self.folders = folders
        self.history: deque[ChatMessage] = deque(maxlen=max_history)

    def interpret(self, text: str) -> AIInterpretation:
        messages: list[ChatMessage] = [{"role": "system", "content": self._prompt()}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": text})
        try:
            raw = self.provider.complete(messages)
            result = self._validate(raw, text)
        except AIProviderError as exc:
            LOG.warning("Fallback de IA indisponível: %s", exc)
            return AIInterpretation(reply=NO_AI_MESSAGE)
        if result.reply:
            self._remember(text, result.reply)
        elif result.command:
            self._remember(text, json.dumps({"action": result.command.intent.value}, ensure_ascii=False))
        return result

    def _prompt(self) -> str:
        return (f"{SYSTEM_PROMPT}\nAplicativos: {', '.join(self.apps)}. "
                f"Sites: {', '.join(self.websites)}. Pastas: {', '.join(self.folders)}.")

    def _remember(self, user: str, assistant: str) -> None:
        self.history.append({"role": "user", "content": user})
        self.history.append({"role": "assistant", "content": assistant})

    def _validate(self, raw: str, original_text: str) -> AIInterpretation:
        if not raw:
            return AIInterpretation(reply="Não entendi o pedido.")
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return AIInterpretation(reply="Não entendi o pedido.")
        if not isinstance(payload, dict):
            return AIInterpretation(reply="Não entendi o pedido.")
        if payload.get("type") == "reply":
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return AIInterpretation(reply=message.strip()[:500])
            return AIInterpretation(reply="Não entendi o pedido.")
        if payload.get("type") != "action" or not isinstance(payload.get("arguments", {}), dict):
            return AIInterpretation(reply="Não entendi o pedido.")
        return self._action(str(payload.get("action", "")), payload.get("arguments", {}), original_text)

    def _action(self, name: str, arguments: dict[str, Any], original: str) -> AIInterpretation:
        no_args = {
            "volume_up": Intent.VOLUME_UP, "volume_down": Intent.VOLUME_DOWN,
            "mute": Intent.MUTE, "unmute": Intent.UNMUTE,
            "media_play_pause": Intent.MEDIA_PLAY_PAUSE, "media_next": Intent.MEDIA_NEXT,
            "media_previous": Intent.MEDIA_PREVIOUS, "media_stop": Intent.MEDIA_STOP,
            "get_time": Intent.GET_TIME, "get_date": Intent.GET_DATE,
            "memory_usage": Intent.MEMORY_USAGE, "cpu_usage": Intent.CPU_USAGE,
            "disk_usage": Intent.DISK_USAGE,
        }
        if name in no_args and not arguments:
            return AIInterpretation(command=Command(no_args[name], original_text=original))
        catalogs = {
            "open_application": (Intent.OPEN_APPLICATION, self.apps),
            "open_website": (Intent.OPEN_WEBSITE, self.websites),
            "open_folder": (Intent.OPEN_FOLDER, self.folders),
        }
        if name in catalogs:
            intent, catalog = catalogs[name]
            target = arguments.get("name")
            if isinstance(target, str) and target in catalog and set(arguments) == {"name"}:
                return AIInterpretation(command=Command(intent, {"target": target}, original))
        if name in {"web_search", "youtube_search"}:
            query = arguments.get("query")
            if isinstance(query, str) and query.strip() and len(query) <= 300 and set(arguments) == {"query"}:
                intent = Intent.WEB_SEARCH if name == "web_search" else Intent.YOUTUBE_SEARCH
                return AIInterpretation(command=Command(intent, {"query": query.strip()}, original))
        if name == "set_volume" and set(arguments) in ({"value"}, {"level"}):
            value = arguments.get("value", arguments.get("level"))
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100:
                return AIInterpretation(command=Command(Intent.SET_VOLUME, {"level": value}, original))
        return AIInterpretation(reply="Não posso executar essa ação.")

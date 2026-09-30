from __future__ import annotations
import logging
import json
import re
import threading
import time
from jarvis import actions  # noqa: F401
from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.ai.base import AIProvider, AIProviderError
from jarvis.core.intent_parser import IntentParser
from jarvis.core.models import Command, Intent
from jarvis.speech.base_stt import SpeechRecognizer
from jarvis.speech.base_tts import TextToSpeech
from jarvis.utils.audio import beep

LOG = logging.getLogger(__name__)
SENSITIVE = {Intent.SHUTDOWN, Intent.REBOOT}

class Assistant:
    def __init__(self, parser: IntentParser, context: ActionContext, tts: TextToSpeech,
                 recognizer: SpeechRecognizer | None = None, ai_provider: AIProvider | None = None,
                 max_history: int = 6):
        self.parser, self.context, self.tts, self.recognizer = parser, context, tts, recognizer
        self.ai_provider = ai_provider
        self.max_history = max(0, max_history)
        self.history: list[dict[str, str]] = []
        self.pending: tuple[Command, float] | None = None
        self._listening = threading.Lock()

    def process_text(self, text: str) -> ActionResult:
        command = self.parser.parse(text)
        LOG.info('Reconhecido: "%s"', text)
        LOG.info("Intent: %s", command.intent.value)
        if self.pending:
            pending, deadline = self.pending
            if time.monotonic() > deadline:
                self.pending = None
                return ActionResult(False, "A confirmação expirou. Ação cancelada.")
            if command.intent is Intent.CONFIRM:
                self.pending = None
                result = registry.execute(pending, self.context)
                self._respond(result)
                return result
            if command.intent is Intent.CANCEL:
                self.pending = None
                result = ActionResult(True, "Ação cancelada.")
                self._respond(result)
                return result
            return ActionResult(False, "Responda sim ou não.")
        if command.intent is Intent.CANCEL:
            result = ActionResult(True, "Ação cancelada.")
            self._respond(result)
            return result
        if command.intent is Intent.UNKNOWN:
            if self._is_negated_or_cancelled(text):
                result = ActionResult(True, "Ação cancelada.")
                self._respond(result)
                return result
            return self._fallback_to_ai(text)
        return self._execute(command)

    def _execute(self, command: Command, respond: bool = True) -> ActionResult:
        if command.intent in SENSITIVE:
            self.pending = (command, time.monotonic() + self.context.settings.confirmation_timeout)
            action = "desligar" if command.intent is Intent.SHUTDOWN else "reiniciar"
            result = ActionResult(True, f"Tem certeza que deseja {action}?", True)
            if respond:
                self._respond(result)
            return result
        result = registry.execute(command, self.context)
        if respond:
            self._respond(result)
        return result

    @staticmethod
    def _is_negated_or_cancelled(text: str) -> bool:
        normalized = " " + re.sub(r"[^a-z0-9áàâãéêíóôõúç ]", " ", text.lower()) + " "
        return any(token in normalized for token in (" não ", " nao ", " cancela ", " cancelar ",
                                                      " não quero ", " nao quero "))

    def _fallback_to_ai(self, text: str) -> ActionResult:
        if not self.ai_provider:
            result = ActionResult(False, "Não entendi o comando.")
            self._respond(result)
            return result
        aliases = {kind: sorted(mapping) for kind, mapping in (
            ("aplicativos", self.parser.catalogs[Intent.OPEN_APPLICATION]),
            ("sites", self.parser.catalogs[Intent.OPEN_WEBSITE]),
            ("pastas", self.parser.catalogs[Intent.OPEN_FOLDER]),
        )}
        prompt = (f"Frase: {text}\nAções permitidas: {', '.join(registry.action_names)}. "
                  f"Catálogos/aliases: {json.dumps(aliases, ensure_ascii=False)}. "
                  "Para abrir use arguments.target; volume usa arguments.level; buscas usam arguments.query.")
        try:
            raw = self.ai_provider.ask(prompt, tuple(self.history))
        except AIProviderError:
            result = ActionResult(False, "Minha IA local está indisponível agora.")
            self._respond(result)
            return result
        result, assistant_message = self._validate_ai_response(raw)
        self._remember("user", text)
        self._remember("assistant", assistant_message)
        self._respond(result)
        return result

    def _validate_ai_response(self, raw: str) -> tuple[ActionResult, str]:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return ActionResult(False, "Não entendi o comando."), "Não entendi o comando."
        if not isinstance(data, dict) or data.get("type") not in {"reply", "action"}:
            return ActionResult(False, "Não entendi o comando."), "Não entendi o comando."
        if data["type"] == "reply":
            message = data.get("message")
            if isinstance(message, str) and message.strip() and len(message) <= 500:
                return ActionResult(True, message.strip()), message.strip()
            return ActionResult(False, "Não entendi o comando."), "Não entendi o comando."
        action, arguments = data.get("action"), data.get("arguments")
        if not isinstance(action, str) or not isinstance(arguments, dict):
            return ActionResult(False, "Não entendi o comando."), "Não entendi o comando."
        try:
            intent = Intent(action)
        except ValueError:
            return ActionResult(False, "Ação não permitida."), "Ação não permitida."
        command = self._validated_command(intent, arguments)
        if command is None or not registry.supports(intent):
            return ActionResult(False, "Ação ou argumentos inválidos."), "Ação ou argumentos inválidos."
        result = self._execute(command, respond=False)
        return result, result.message

    def _validated_command(self, intent: Intent, arguments: dict) -> Command | None:
        if intent in {Intent.OPEN_APPLICATION, Intent.OPEN_WEBSITE, Intent.OPEN_FOLDER}:
            target = arguments.get("target", arguments.get("name"))
            if not isinstance(target, str):
                return None
            key = self.parser.catalogs[intent].get(self.parser.normalize_alias(target))
            return Command(intent, {"target": key}) if key else None
        if intent is Intent.SET_VOLUME:
            level = arguments.get("level")
            return Command(intent, {"level": level}) if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= 100 else None
        if intent in {Intent.WEB_SEARCH, Intent.YOUTUBE_SEARCH}:
            query = arguments.get("query")
            return Command(intent, {"query": query.strip()}) if isinstance(query, str) and query.strip() and len(query) <= 300 else None
        return Command(intent) if not arguments else None

    def _remember(self, role: str, content: str) -> None:
        if not self.max_history:
            return
        self.history.append({"role": role, "content": content})
        del self.history[:-self.max_history]

    def _respond(self, result: ActionResult) -> None:
        (LOG.info if result.success else LOG.warning)(result.message)
        self.tts.speak(result.message)

    def listen_once(self) -> None:
        if not self.recognizer or not self._listening.acquire(blocking=False):
            LOG.debug("Escuta ignorada: já ocupado ou STT ausente")
            return
        try:
            LOG.info("Hotkey pressionada; ouvindo...")
            if self.context.settings.start_beep:
                beep(880)
            text = self.recognizer.recognize_once()
            if self.context.settings.stop_beep:
                beep(550)
            if text:
                result = self.process_text(text)
                if result.requires_confirmation:
                    self._listen_for_confirmation()
            else:
                self._respond(ActionResult(False, "Não entendi o comando."))
        except RuntimeError as exc:
            LOG.error("%s", exc)
        finally:
            self._listening.release()

    def _listen_for_confirmation(self) -> None:
        if not self.recognizer:
            return
        try:
            text = self.recognizer.recognize_once()
            self.process_text(text or "cancelar")
        except RuntimeError as exc:
            LOG.error("Falha ao ouvir confirmação: %s", exc)
            self.pending = None

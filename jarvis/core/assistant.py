from __future__ import annotations
import logging
import threading
import time
from jarvis import actions  # noqa: F401
from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.ai.interpreter import AIInterpreter
from jarvis.core.intent_parser import IntentParser
from jarvis.core.models import Command, Intent
from jarvis.speech.base_stt import SpeechRecognizer
from jarvis.speech.base_tts import TextToSpeech
from jarvis.utils.audio import beep
from jarvis.utils.text import has_negated_action

LOG = logging.getLogger(__name__)
SENSITIVE = {Intent.SHUTDOWN, Intent.REBOOT}

class Assistant:
    def __init__(self, parser: IntentParser, context: ActionContext, tts: TextToSpeech,
                 recognizer: SpeechRecognizer | None = None, ai: AIInterpreter | None = None):
        self.parser, self.context, self.tts, self.recognizer = parser, context, tts, recognizer
        self.ai = ai
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
        if command.intent in SENSITIVE:
            self.pending = (command, time.monotonic() + self.context.settings.confirmation_timeout)
            action = "desligar" if command.intent is Intent.SHUTDOWN else "reiniciar"
            result = ActionResult(True, f"Tem certeza que deseja {action}?", True)
            self._respond(result)
            return result
        if command.intent is Intent.UNKNOWN and has_negated_action(text):
            result = ActionResult(True, "Tudo bem, não vou executar essa ação.")
            self._respond(result)
            return result
        if command.intent is Intent.UNKNOWN and self.ai:
            interpretation = self.ai.interpret(text)
            if interpretation.command:
                LOG.info("Intent da IA validada: %s", interpretation.command.intent.value)
                result = registry.execute(interpretation.command, self.context)
            else:
                result = ActionResult(True, interpretation.reply or "Não entendi o pedido.")
            self._respond(result)
            return result
        result = registry.execute(command, self.context)
        self._respond(result)
        return result

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

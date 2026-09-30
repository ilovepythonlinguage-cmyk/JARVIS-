#!/usr/bin/env python3
from __future__ import annotations
import argparse
import logging
import threading
from jarvis.actions.base import ActionContext
from jarvis.configuration import CONFIG_DIR, load_settings, load_yaml
from jarvis.core.assistant import Assistant
from jarvis.core.hotkey import GlobalHotkey
from jarvis.core.intent_parser import IntentParser
from jarvis.speech.local_tts import EspeakTTS
from jarvis.speech.vosk_stt import VoskRecognizer
from jarvis.utils.logger import configure_logging

def build_assistant(with_voice: bool = True) -> Assistant:
    settings = load_settings()
    apps = load_yaml(CONFIG_DIR / "apps.yaml")
    sites = load_yaml(CONFIG_DIR / "websites.yaml")
    folders = load_yaml(CONFIG_DIR / "folders.yaml")
    parser = IntentParser(apps, sites, folders)
    context = ActionContext(settings, apps, sites, folders)
    tts = EspeakTTS(settings.tts_enabled, settings.language.lower())
    recognizer = VoskRecognizer(settings.model_path, settings.sample_rate, settings.block_size,
                                settings.silence_timeout, settings.max_recording_seconds,
                                settings.silence_threshold, settings.audio_device) if with_voice else None
    return Assistant(parser, context, tts, recognizer)

def text_mode(assistant: Assistant) -> None:
    print("Modo texto do Jarvis. Digite 'sair' para encerrar.")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if text.lower() in {"sair", "exit", "quit"}:
            return
        result = assistant.process_text(text)
        print(result.message)

def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente pessoal Jarvis")
    parser.add_argument("--debug", action="store_true", help="ativa logs detalhados")
    parser.add_argument("--text", action="store_true", help="testa comandos sem microfone/hotkey")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.log_level, args.debug)
    log = logging.getLogger("jarvis")
    log.info("Jarvis iniciado")
    assistant = build_assistant(with_voice=not args.text)
    if args.text:
        text_mode(assistant)
        return 0
    hotkey = GlobalHotkey(settings.hotkey, lambda: threading.Thread(target=assistant.listen_once, daemon=True).start())
    try:
        hotkey.run()
    except (RuntimeError, KeyboardInterrupt) as exc:
        if isinstance(exc, RuntimeError):
            log.error("%s", exc)
            return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

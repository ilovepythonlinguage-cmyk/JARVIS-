#!/usr/bin/env python3
from __future__ import annotations
import argparse
import importlib.util
import logging
import os
import shutil
import threading
from jarvis.actions.base import ActionContext
from jarvis.ai.base import AIProviderError
from jarvis.ai.interpreter import AIInterpreter
from jarvis.ai.ollama import OllamaProvider
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
    ai = None
    if settings.ai.enabled:
        provider = OllamaProvider(settings.ai.base_url, settings.ai.model, settings.ai.timeout_seconds)
        ai = AIInterpreter(provider, apps, sites, folders, settings.ai.max_history)
    return Assistant(parser, context, tts, recognizer, ai)

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

def doctor() -> int:
    settings = load_settings()
    print("Diagnóstico do Jarvis")
    for module in ("yaml", "vosk", "sounddevice", "pynput"):
        status = "OK" if importlib.util.find_spec(module) else "AVISO"
        print(f"[{status}] Dependência Python: {module}")
    for command in ("espeak-ng", "playerctl", "pactl", "wpctl"):
        status = "OK" if shutil.which(command) else "AVISO"
        print(f"[{status}] Comando: {command}")
    if settings.model_path.is_dir():
        print(f"[OK] Modelo Vosk: {settings.model_path}")
    else:
        print(f"[AVISO] Modelo Vosk ausente: {settings.model_path}")
    session = os.environ.get("XDG_SESSION_TYPE", "não detectada")
    print(f"[{'OK' if session == 'x11' and os.environ.get('DISPLAY') else 'AVISO'}] Sessão gráfica: {session}")
    if not settings.ai.enabled:
        print("[AVISO] IA desativada; comandos locais continuam funcionando.")
        return 0
    provider = OllamaProvider(settings.ai.base_url, settings.ai.model, settings.ai.timeout_seconds)
    try:
        models = provider.list_models()
    except AIProviderError:
        print("[AVISO] Ollama não está disponível. Comandos locais continuam funcionando.")
        return 0
    print("[OK] Ollama encontrado")
    print("[OK] Ollama API acessível")
    if provider.model in models or f"{provider.model}:latest" in models:
        print(f"[OK] Modelo {provider.model} disponível")
    else:
        print(f"[AVISO] Modelo {provider.model} não está instalado; execute: ollama pull {provider.model}")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente pessoal Jarvis")
    parser.add_argument("--debug", action="store_true", help="ativa logs detalhados")
    parser.add_argument("--text", action="store_true", help="testa comandos sem microfone/hotkey")
    parser.add_argument("--doctor", action="store_true", help="verifica ambiente, áudio, hotkey e IA local")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.log_level, args.debug)
    if args.doctor:
        return doctor()
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

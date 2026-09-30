"""Carregamento validado dos arquivos YAML de configuração."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent / "config"

@dataclass(frozen=True)
class AISettings:
    enabled: bool = True
    provider: str = "ollama"
    model: str = "llama3.2:1b"
    base_url: str = "http://localhost:11434"
    timeout_seconds: float = 8
    max_history: int = 6

@dataclass(frozen=True)
class Settings:
    hotkey: str = "F8"
    language: str = "pt-BR"
    tts_enabled: bool = True
    start_beep: bool = True
    stop_beep: bool = True
    silence_timeout: float = 1.5
    max_recording_seconds: float = 15
    sample_rate: int = 16000
    block_size: int = 4000
    silence_threshold: int = 500
    browser: str = "brave-browser"
    log_level: str = "INFO"
    vosk_model_path: str = "models/vosk-model-small-pt-0.3"
    audio_device: int | str | None = None
    confirmation_timeout: float = 10
    ai: AISettings = AISettings()

    @property
    def model_path(self) -> Path:
        path = Path(self.vosk_model_path).expanduser()
        return path if path.is_absolute() else ROOT / path

def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Arquivo de configuração não encontrado: {path}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"YAML inválido em {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"A configuração {path} deve conter um mapa YAML")
    return data

def load_settings(path: Path | None = None) -> Settings:
    values = load_yaml(path or CONFIG_DIR / "config.yaml")
    known = Settings.__dataclass_fields__
    unknown = values.keys() - known.keys()
    if unknown:
        raise RuntimeError(f"Opções desconhecidas: {', '.join(sorted(unknown))}")
    ai_values = values.pop("ai", {})
    if not isinstance(ai_values, dict):
        raise RuntimeError("A opção ai deve conter um mapa YAML")
    unknown_ai = ai_values.keys() - AISettings.__dataclass_fields__.keys()
    if unknown_ai:
        raise RuntimeError(f"Opções de IA desconhecidas: {', '.join(sorted(unknown_ai))}")
    ai = AISettings(**ai_values)
    if ai.provider != "ollama":
        raise RuntimeError(f"Provider de IA não suportado: {ai.provider}")
    if ai.max_history < 0 or ai.max_history > 20:
        raise RuntimeError("ai.max_history deve estar entre 0 e 20")
    if ai.timeout_seconds <= 0:
        raise RuntimeError("ai.timeout_seconds deve ser positivo")
    return Settings(**values, ai=ai)

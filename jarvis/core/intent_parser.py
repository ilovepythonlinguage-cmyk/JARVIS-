"""Parser determinístico: regras explícitas e aliases configuráveis."""
from __future__ import annotations
import re
from typing import Any
from jarvis.core.models import Command, Intent
from jarvis.utils.text import normalize_text

class IntentParser:
    def __init__(self, apps: dict[str, Any], websites: dict[str, Any], folders: dict[str, Any]):
        self.catalogs = {
            Intent.OPEN_APPLICATION: self._alias_map(apps),
            Intent.OPEN_WEBSITE: self._alias_map(websites),
            Intent.OPEN_FOLDER: self._alias_map(folders),
        }

    @staticmethod
    def _alias_map(items: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in items.items():
            result[normalize_text(key)] = key
            for alias in value.get("aliases", []):
                result[normalize_text(str(alias))] = key
        return result

    def parse(self, text: str) -> Command:
        normalized = normalize_text(text)
        base = {"original_text": text}
        if not normalized:
            return Command(Intent.UNKNOWN, **base)
        if normalized in {"sim", "confirmo", "pode", "pode sim"}:
            return Command(Intent.CONFIRM, **base)
        if normalized in {"nao", "cancela", "cancelar", "pare", "deixa"}:
            return Command(Intent.CANCEL, **base)
        # Ações perigosas têm correspondência exata, nunca fuzzy.
        if normalized in {"desliga o computador", "desligar o computador", "desliga computador"}:
            return Command(Intent.SHUTDOWN, **base)
        if normalized in {"reinicia o computador", "reiniciar o computador", "reinicia computador"}:
            return Command(Intent.REBOOT, **base)
        rules: list[tuple[set[str], Intent]] = [
            ({"que horas sao", "qual e a hora", "qual a hora", "horas"}, Intent.GET_TIME),
            ({"qual a data de hoje", "que dia e hoje", "data de hoje"}, Intent.GET_DATE),
            ({"aumenta o volume", "aumentar volume", "volume mais"}, Intent.VOLUME_UP),
            ({"abaixa o volume", "diminui o volume", "baixar volume", "volume menos"}, Intent.VOLUME_DOWN),
            ({"muta", "mute", "silencia o volume"}, Intent.MUTE),
            ({"desmuta", "tira do mudo", "reativa o som"}, Intent.UNMUTE),
            ({"pausa", "pausa a musica", "continua", "continuar musica", "toca a musica"}, Intent.MEDIA_PLAY_PAUSE),
            ({"proxima musica", "proxima", "avanca a musica"}, Intent.MEDIA_NEXT),
            ({"musica anterior", "anterior", "volta a musica"}, Intent.MEDIA_PREVIOUS),
            ({"para a musica", "parar musica"}, Intent.MEDIA_STOP),
            ({"uso da memoria", "uso de memoria", "quanto de memoria ram estou usando"}, Intent.MEMORY_USAGE),
            ({"uso do processador", "uso de cpu", "quanto de cpu estou usando"}, Intent.CPU_USAGE),
            ({"quanto espaco tenho no disco", "uso do disco", "espaco em disco"}, Intent.DISK_USAGE),
            ({"bloqueia o computador", "bloquear computador", "trava o computador"}, Intent.LOCK),
        ]
        for phrases, intent in rules:
            if normalized in phrases:
                return Command(intent, **base)
        match = re.fullmatch(r"volume\s+(\d{1,3})(?:\s*por cento)?", normalized)
        if match:
            level = int(match.group(1))
            return Command(Intent.SET_VOLUME, {"level": level}, text) if level <= 100 else Command(Intent.UNKNOWN, **base)
        youtube = re.match(r"^(?:pesquisa|pesquise|procura|procurar)\s+(?:no|na)\s+youtube\s+(.+)$", normalized)
        if youtube:
            return Command(Intent.YOUTUBE_SEARCH, {"query": youtube.group(1)}, text)
        search = re.match(r"^(?:pesquisa|pesquise|procura|procurar)\s+(.+)$", normalized)
        if search:
            return Command(Intent.WEB_SEARCH, {"query": search.group(1)}, text)
        opened = re.match(r"^(?:abre|abra|abrir)\s+(.+)$", normalized)
        if opened:
            target = opened.group(1).strip()
            candidates = [target]
            for prefix in ("minha pasta ", "meu ", "minha ", "o ", "a "):
                if target.startswith(prefix):
                    candidates.append(target.removeprefix(prefix).strip())
            for candidate in candidates:
                for intent in (Intent.OPEN_APPLICATION, Intent.OPEN_WEBSITE, Intent.OPEN_FOLDER):
                    key = self.catalogs[intent].get(candidate)
                    if key:
                        return Command(intent, {"target": key}, text)
        return Command(Intent.UNKNOWN, **base)

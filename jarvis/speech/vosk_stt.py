from __future__ import annotations
import json
import logging
import queue
import struct
import time
from pathlib import Path
from typing import Any
from jarvis.speech.base_stt import SpeechRecognizer

LOG = logging.getLogger(__name__)

class VoskRecognizer(SpeechRecognizer):
    def __init__(self, model_path: Path, sample_rate: int = 16000, block_size: int = 4000,
                 silence_timeout: float = 1.5, max_seconds: float = 15,
                 silence_threshold: int = 500, device: int | str | None = None):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.silence_timeout = silence_timeout
        self.max_seconds = max_seconds
        self.silence_threshold = silence_threshold
        self.device = device
        self._model: Any = None

    def _load_model(self) -> Any:
        if not self.model_path.is_dir():
            raise RuntimeError(f"Modelo Vosk não encontrado em {self.model_path}")
        if self._model is None:
            try:
                from vosk import Model
                self._model = Model(str(self.model_path))
            except ImportError as exc:
                raise RuntimeError("Vosk não está instalado. Execute ./install.sh") from exc
        return self._model

    @staticmethod
    def _peak(data: bytes) -> int:
        samples = struct.iter_unpack("<h", data)
        return max((abs(value[0]) for value in samples), default=0)

    def recognize_once(self) -> str:
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer
        except ImportError as exc:
            raise RuntimeError("Dependências de voz ausentes. Execute ./install.sh") from exc
        audio: queue.Queue[bytes] = queue.Queue()
        recognizer = KaldiRecognizer(self._load_model(), self.sample_rate)
        started = time.monotonic()
        last_voice: float | None = None

        def callback(indata: bytes, frames: int, timing: Any, status: Any) -> None:
            if status:
                LOG.debug("Status do áudio: %s", status)
            audio.put(bytes(indata))

        try:
            with sd.RawInputStream(samplerate=self.sample_rate, blocksize=self.block_size, device=self.device,
                                   dtype="int16", channels=1, callback=callback):
                while time.monotonic() - started < self.max_seconds:
                    try:
                        data = audio.get(timeout=1)
                    except queue.Empty:
                        continue
                    recognizer.AcceptWaveform(data)
                    now = time.monotonic()
                    if self._peak(data) >= self.silence_threshold:
                        last_voice = now
                    elif last_voice is not None and now - last_voice >= self.silence_timeout:
                        break
        except Exception as exc:
            raise RuntimeError(f"Não foi possível capturar o microfone: {exc}") from exc
        return str(json.loads(recognizer.FinalResult()).get("text", "")).strip()

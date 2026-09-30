import logging
import shutil
import subprocess
from jarvis.speech.base_tts import TextToSpeech

LOG = logging.getLogger(__name__)

class EspeakTTS(TextToSpeech):
    def __init__(self, enabled: bool = True, language: str = "pt-br"):
        self.enabled = enabled
        self.language = language

    def speak(self, text: str) -> None:
        if not self.enabled:
            return
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if not executable:
            LOG.warning("TTS habilitado, mas espeak-ng não está instalado")
            return
        try:
            subprocess.run([executable, "-v", self.language, text], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            LOG.warning("Falha no TTS: %s", exc)

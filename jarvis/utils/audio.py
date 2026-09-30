import logging
import math
import struct

LOG = logging.getLogger(__name__)

def beep(frequency: int = 880, duration: float = 0.09) -> None:
    """Toca um tom sem criar arquivos; falhas de áudio não derrubam o assistente."""
    try:
        import sounddevice as sd
        rate = 44100
        amplitude = 7000
        frames = b"".join(struct.pack("<h", int(amplitude * math.sin(2 * math.pi * frequency * i / rate)))
                          for i in range(int(rate * duration)))
        with sd.RawOutputStream(samplerate=rate, channels=1, dtype="int16") as stream:
            stream.write(frames)
    except Exception as exc:
        LOG.debug("Beep indisponível: %s", exc)

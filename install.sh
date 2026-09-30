#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

command -v python3 >/dev/null || { echo "ERRO: Python 3 não encontrado."; exit 1; }
echo "Python: $(python3 --version)"
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("ERRO: é necessário Python 3.10 ou superior")
PY

if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p models "$HOME/.config/systemd/user"
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" systemd/jarvis.service > "$HOME/.config/systemd/user/jarvis.service"
systemctl --user daemon-reload 2>/dev/null || true

missing=()
for cmd in espeak-ng playerctl pactl xdg-open cinnamon-screensaver-command; do
  command -v "$cmd" >/dev/null || missing+=("$cmd")
done
if ((${#missing[@]})); then
  echo "Dependências de sistema ausentes: ${missing[*]}"
  echo "No Linux Mint, instale conforme necessário:"
  echo "  sudo apt install espeak-ng playerctl pulseaudio-utils xdg-utils cinnamon-screensaver libportaudio2"
else
  echo "Dependências de sistema encontradas."
fi
if command -v ollama >/dev/null; then
  echo "Ollama encontrado: $(command -v ollama)"
else
  echo "AVISO: Ollama não encontrado; comandos locais funcionarão sem o fallback de IA."
fi

echo "Sessão: ${XDG_SESSION_TYPE:-não detectada}; DISPLAY=${DISPLAY:-não definido}"
if command -v arecord >/dev/null; then
  echo "Dispositivos de captura:"; arecord -l || echo "Nenhum dispositivo ALSA acessível."
else
  echo "Teste de microfone indisponível (instale alsa-utils para usar arecord -l)."
fi
.venv/bin/python - <<'PY'
try:
    import sounddevice as sd
    print("Dispositivos PortAudio:")
    print(sd.query_devices())
except Exception as exc:
    print(f"AVISO: não foi possível consultar áudio: {exc}")
PY
if [[ -n "${DISPLAY:-}" && "${XDG_SESSION_TYPE:-x11}" != wayland ]]; then
  echo "Ambiente compatível com o teste da hotkey via pynput (o teste real ocorre ao iniciar)."
else
  echo "AVISO: hotkey requer uma sessão gráfica X11; não execute o serviço por SSH/TTY."
fi
cat <<'MSG'

Instalação Python concluída.
1. Baixe um modelo Vosk pt-BR pequeno de https://alphacephei.com/vosk/models
2. Extraia-o em models/vosk-model-small-pt-0.3 (ou altere vosk_model_path).
3. Para IA local, instale Ollama e execute: ollama pull llama3.2:1b
4. Diagnóstico: .venv/bin/python main.py --doctor
5. Teste sem microfone: .venv/bin/python main.py --text
6. Inicie por voz: .venv/bin/python main.py
7. Autostart: systemctl --user enable --now jarvis.service
O instalador não executou sudo, não instalou pacotes apt e não habilitou o serviço.
MSG

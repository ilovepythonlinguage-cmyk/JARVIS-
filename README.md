# Jarvis — assistente pessoal por voz para Linux Mint

Jarvis é um assistente **local, sem interface gráfica e orientado a privacidade**. Em uma sessão Cinnamon/X11, ele permanece bloqueado à espera da hotkey (F8 por padrão); somente depois do toque abre o microfone, reconhece uma frase com Vosk, fecha a captura e executa uma ação previamente permitida. Não há escuta contínua, áudio salvo ou execução arbitrária de shell.

> O modo texto funciona em qualquer terminal. Voz, hotkey e ações de desktop precisam ser testadas na sessão gráfica real do Linux Mint — contêineres e SSH normalmente não têm microfone, servidor X ou sessão de áudio.

## Arquitetura

```text
main.py                         entrada, --text e --debug
jarvis/config/*.yaml            preferências e catálogos editáveis
jarvis/configuration.py         leitura tipada de YAML
jarvis/core/intent_parser.py    fala normalizada -> Command/Intent
jarvis/core/assistant.py        ciclo, resposta e confirmação
jarvis/core/hotkey.py           listener global X11 sob demanda
jarvis/actions/                 registry e ações permitidas
jarvis/speech/                  interfaces STT/TTS e Vosk/espeak
jarvis/ai/base.py               interface opcional para IA futura
jarvis/utils/                   texto, áudio e logging
tests/                          parser, normalização e segurança
systemd/jarvis.service          template de serviço do usuário
```

O `IntentParser` não executa nada: produz um `Command` tipado. O `ActionRegistry` associa somente intents conhecidas a handlers. Os handlers recebem dados já estruturados e chamam processos com listas de argumentos, sem `shell=True`. Desligar e reiniciar usam correspondência exata e ficam pendentes até uma segunda frase explícita (“sim”); “não” e “cancelar” descartam a operação.

## Requisitos

- Linux Mint Cinnamon, preferencialmente sessão **X11**;
- Python 3.10 ou mais novo, `python3-venv` e internet apenas durante a instalação;
- microfone reconhecido pelo PipeWire/PulseAudio/ALSA;
- modelo Vosk pequeno em português;
- pacotes recomendados: `libportaudio2`, `espeak-ng`, `playerctl`, `pulseaudio-utils`, `xdg-utils`, `cinnamon-screensaver` e `alsa-utils`.

Confira a sessão com `echo "$XDG_SESSION_TYPE"`. O backend `pynput` funciona sem root em X11. Por restrição de segurança do Wayland, este projeto deliberadamente exibe uma mensagem clara e encerra; entre na sessão “Cinnamon” (X11), em vez de executar o programa como root.

## Instalação no Linux Mint

```bash
git clone <URL-DESTE-REPOSITORIO> jarvis
cd jarvis
./install.sh
```

O instalador verifica Python, cria `.venv`, instala dependências Python, lista utilitários ausentes, consulta dispositivos de áudio quando possível e gera `~/.config/systemd/user/jarvis.service` com o caminho real do clone. Ele **não** chama `sudo`, não instala apt automaticamente e não habilita autostart.

Se o instalador listar dependências, instale somente as necessárias:

```bash
sudo apt update
sudo apt install python3-venv libportaudio2 espeak-ng playerctl \
  pulseaudio-utils xdg-utils cinnamon-screensaver alsa-utils
```

### Microfone

Liste entradas com `arecord -l` ou com:

```bash
.venv/bin/python -c 'import sounddevice as s; print(s.query_devices())'
```

O dispositivo padrão é usado quando `audio_device: null`. Para escolher outro, copie seu índice ou nome para `audio_device` em `jarvis/config/config.yaml`. Ajuste `silence_threshold` se a gravação terminar cedo (reduza) ou nunca detectar silêncio por ruído (aumente). O silêncio só começa a contar depois que voz é detectada; o limite absoluto continua sendo 15 segundos.

### Modelo Vosk pt-BR

1. Acesse a [lista oficial de modelos Vosk](https://alphacephei.com/vosk/models).
2. Baixe um modelo pequeno de português, adequado a computadores modestos.
3. Extraia a pasta para `models/vosk-model-small-pt-0.3`.
4. Se o nome/local for diferente, altere `vosk_model_path` em `jarvis/config/config.yaml`.

O modelo é carregado somente na primeira ativação. Durante a espera, o microfone permanece fechado e não há inferência de voz consumindo CPU.

## Configuração

`jarvis/config/config.yaml` contém:

```yaml
hotkey: F8
language: pt-BR
tts_enabled: true
start_beep: true
stop_beep: true
silence_timeout: 1.5
max_recording_seconds: 15
sample_rate: 16000
block_size: 4000
silence_threshold: 500
browser: brave-browser
log_level: INFO
vosk_model_path: models/vosk-model-small-pt-0.3
audio_device: null
confirmation_timeout: 10
```

Para trocar a tecla, edite `hotkey` (por exemplo, `F9`) e reinicie. Teclas especiais suportadas pelo `pynput` são usadas pelo nome. Para desligar a fala e manter logs, use `tts_enabled: false`. Se Brave não existir, URLs usam `xdg-open` e o navegador padrão.

## Como iniciar e usar

Teste primeiro sem tocar no desktop:

```bash
.venv/bin/python main.py --text
```

Digite comandos após `>` e use `sair` para encerrar. Atenção: o modo texto interpreta **e executa** ações válidas, exatamente como a voz. Desligamento/reinício ainda exigem confirmação.

Na sessão gráfica:

```bash
.venv/bin/python main.py
.venv/bin/python main.py --debug  # logs detalhados
```

Pressione F8 uma vez, aguarde o tom, fale e pare. Após cerca de 1,5 s de silêncio há um segundo tom. Outra pressão durante a captura é ignorada para impedir duas gravações simultâneas.

### Comandos disponíveis

| Categoria | Exemplos |
|---|---|
| Aplicativos | “abre o vscode”, “abra o Brave”, “abre o terminal” |
| Sites | “abre o YouTube”, “abre o GitHub”, “abre o ChatGPT” |
| Busca | “pesquisa como criar classes em Python” |
| YouTube | “pesquise no YouTube curso de Python” |
| Pastas | “abre downloads”, “abre minha pasta de projetos” |
| Volume | “aumenta o volume”, “abaixa o volume”, “volume 30”, “muta”, “desmuta” |
| Mídia | “pausa”, “continua”, “próxima música”, “música anterior”, “para a música” |
| Informação | “que horas são”, “qual a data de hoje”, “uso da memória”, “uso do processador”, “uso do disco” |
| Sessão | “bloqueia o computador” |
| Sensível | “desliga o computador”, “reinicia o computador”; depois “sim” ou “não” |

## Personalização dos catálogos

Os aliases são normalizados para minúsculas e sem acentos.

### Adicionar aplicativo

Em `jarvis/config/apps.yaml`, o comando é uma lista de argumentos fixa — nunca texto falado:

```yaml
editor:
  command: [xed]
  aliases: [editor, editor de texto, xed]
```

### Adicionar site

Em `jarvis/config/websites.yaml`:

```yaml
documentacao_python:
  url: https://docs.python.org/pt-br/3/
  aliases: [documentacao do python, docs python]
```

### Adicionar pasta

Em `jarvis/config/folders.yaml` (há expansão segura de `~`):

```yaml
faculdade:
  path: ~/Documentos/Faculdade
  aliases: [faculdade, pasta da faculdade]
```

A pasta precisa existir; caso contrário Jarvis relata o erro sem fechar.

## Criar uma nova action

1. Adicione um membro a `Intent` em `jarvis/core/models.py`.
2. Acrescente uma regra pequena e inequívoca ao parser.
3. Crie um handler em `jarvis/actions/`, usando `@registry.register(Intent.SEJA_QUAL_FOR)`.
4. Importe o módulo em `jarvis/actions/__init__.py` para registrá-lo.
5. Retorne `ActionResult` e crie testes de frases aceitas e rejeitadas.

Use `run_checked`/`run_detached` com argumentos separados. Nunca passe fala a `os.system`, `eval`, `exec`, shell ou caminho destrutivo. Novas ações destrutivas devem entrar em `SENSITIVE` e exigir confirmação conservadora. `SpeechRecognizer`, `TextToSpeech` e `AIProvider` são interfaces independentes: uma futura integração Whisper/LLM pode implementá-las sem mudar as ações locais.

## Testes e qualidade

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q main.py jarvis tests
.venv/bin/ruff check .
printf 'que horas são\nsair\n' | .venv/bin/python main.py --text
```

Os testes não desligam a máquina nem abrem programas: a execução sensível é substituída por mock.

## Inicialização automática com systemd --user

Depois de `./install.sh`:

```bash
systemctl --user enable --now jarvis.service  # habilitar e iniciar
systemctl --user start jarvis.service         # iniciar
systemctl --user stop jarvis.service          # parar
systemctl --user restart jarvis.service       # reiniciar
systemctl --user status jarvis.service        # status
journalctl --user -u jarvis.service -f        # logs ao vivo
systemctl --user disable --now jarvis.service # desabilitar
```

O serviço roda como seu usuário, usa a `.venv`, reinicia apenas em falhas e escreve no journal. Não use `sudo systemctl`: seria outro gerenciador e violaria o modelo sem root. Em algumas instalações, variáveis gráficas precisam ser importadas uma vez pela sessão:

```bash
systemctl --user import-environment DISPLAY XAUTHORITY XDG_SESSION_TYPE
systemctl --user restart jarvis.service
```

## Troubleshooting

- **“Modelo Vosk não encontrado”**: confirme `vosk_model_path` e que a pasta extraída contém os arquivos do modelo, não outra pasta intermediária.
- **“DISPLAY não definido”**: execute dentro do terminal da sessão Cinnamon, não em TTY/SSH; importe as variáveis para systemd como acima.
- **Wayland**: escolha Cinnamon/X11 na tela de login. Captura global genérica no Wayland é bloqueada por design.
- **Sem microfone / PortAudio**: instale `libportaudio2`, confira `sounddevice.query_devices()`, permissões e seleção de entrada nas Configurações de Som.
- **Detecção para cedo/tarde**: calibre `silence_threshold`, `silence_timeout`, `block_size` e `audio_device`.
- **Sem beep ou TTS**: verifique a saída padrão; instale `libportaudio2` para beep e `espeak-ng` para fala. Falhas são registradas, não encerram Jarvis.
- **Aplicativo não abre**: rode `command -v code` (ou o executável configurado) e corrija `apps.yaml`. Flatpaks podem usar uma lista fixa como `[flatpak, run, ID.DO.APP]`.
- **Mídia não responde**: instale `playerctl` e confirme que o player oferece MPRIS.
- **Volume não responde**: `pactl` é preferido; `wpctl` é fallback. Teste `pactl info` na mesma sessão.
- **Hotkey não responde**: confirme X11, `DISPLAY`, que F8 não está monopolizado e consulte `journalctl --user -u jarvis.service`.
- **Brave ausente**: instale-o, mude `browser`, ou deixe o fallback `xdg-open` abrir o navegador padrão.

## Privacidade e limites

O áudio permanece apenas nos buffers de memória de curta duração e não é escrito em disco. Vosk funciona offline. TTS e comandos também são locais. O projeto não inclui deleção, scripts por voz, encerramento de processos nem terminal arbitrário. A interface `AIProvider` está vazia de propósito: nenhuma chave, conta ou API externa é necessária para os comandos básicos.

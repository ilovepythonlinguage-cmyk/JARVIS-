import shutil
from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.actions.helpers import run_checked
from jarvis.core.models import Command, Intent

_MEDIA = {Intent.MEDIA_PLAY_PAUSE: "play-pause", Intent.MEDIA_NEXT: "next", Intent.MEDIA_PREVIOUS: "previous", Intent.MEDIA_STOP: "stop"}

@registry.register(*_MEDIA)
def media(command: Command, context: ActionContext) -> ActionResult:
    return run_checked(["playerctl", _MEDIA[command.intent]], "Controle de mídia executado.")

def _volume_tool() -> str | None:
    return "pactl" if shutil.which("pactl") else "wpctl" if shutil.which("wpctl") else None

@registry.register(Intent.VOLUME_UP, Intent.VOLUME_DOWN, Intent.SET_VOLUME, Intent.MUTE, Intent.UNMUTE)
def volume(command: Command, context: ActionContext) -> ActionResult:
    tool = _volume_tool()
    if not tool:
        return ActionResult(False, "Não encontrei pactl nem wpctl para controlar o volume.")
    if tool == "pactl":
        operations = {
            Intent.VOLUME_UP: ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
            Intent.VOLUME_DOWN: ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
            Intent.MUTE: ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"],
            Intent.UNMUTE: ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"],
            Intent.SET_VOLUME: ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{command.slots.get('level')}%"],
        }
    else:
        operations = {
            Intent.VOLUME_UP: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+", "--limit", "1.0"],
            Intent.VOLUME_DOWN: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"],
            Intent.MUTE: ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1"],
            Intent.UNMUTE: ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"],
            Intent.SET_VOLUME: ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{int(command.slots.get('level', 0)) / 100:.2f}"],
        }
    return run_checked(operations[command.intent], "Volume ajustado.")

from pathlib import Path
from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.actions.helpers import run_detached
from jarvis.core.models import Command, Intent

@registry.register(Intent.OPEN_FOLDER)
def open_folder(command: Command, context: ActionContext) -> ActionResult:
    target = command.slots["target"]
    path = Path(str(context.folders[target]["path"])).expanduser()
    if not path.is_dir():
        return ActionResult(False, f"A pasta {path} não existe.")
    return run_detached(["xdg-open", str(path)], f"Abrindo {target}.")

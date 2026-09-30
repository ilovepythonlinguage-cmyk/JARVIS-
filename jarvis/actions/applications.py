from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.actions.helpers import run_detached
from jarvis.core.models import Command, Intent

@registry.register(Intent.OPEN_APPLICATION)
def open_application(command: Command, context: ActionContext) -> ActionResult:
    target = command.slots["target"]
    item = context.apps[target]
    args = item.get("command")
    if isinstance(args, str):
        args = [args]
    if not isinstance(args, list) or not args or not all(isinstance(x, str) for x in args):
        return ActionResult(False, f"Comando inválido para {target} na configuração.")
    return run_detached(args, f"Abrindo {target}.")

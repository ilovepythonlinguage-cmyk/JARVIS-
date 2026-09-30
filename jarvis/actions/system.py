from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.actions.helpers import run_checked
from jarvis.core.models import Command, Intent

@registry.register(Intent.LOCK)
def lock(command: Command, context: ActionContext) -> ActionResult:
    return run_checked(["cinnamon-screensaver-command", "--lock"], "Computador bloqueado.")

# Estes handlers só são alcançados após o Assistant validar uma confirmação pendente.
@registry.register(Intent.SHUTDOWN)
def shutdown(command: Command, context: ActionContext) -> ActionResult:
    return run_checked(["systemctl", "poweroff"], "Desligando o computador.")

@registry.register(Intent.REBOOT)
def reboot(command: Command, context: ActionContext) -> ActionResult:
    return run_checked(["systemctl", "reboot"], "Reiniciando o computador.")

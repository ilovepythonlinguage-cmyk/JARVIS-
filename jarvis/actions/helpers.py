from __future__ import annotations
import logging
import shutil
import subprocess
from collections.abc import Sequence
from jarvis.actions.base import ActionResult

LOG = logging.getLogger(__name__)

def run_detached(args: Sequence[str], label: str) -> ActionResult:
    executable = shutil.which(args[0])
    if not executable:
        return ActionResult(False, f"Não encontrei {args[0]} instalado.")
    try:
        subprocess.Popen([executable, *args[1:]], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        LOG.info("Executando %s", label)
        return ActionResult(True, label)
    except OSError as exc:
        LOG.error("Falha ao executar %s: %s", args[0], exc)
        return ActionResult(False, f"Não consegui executar {label}.")

def run_checked(args: Sequence[str], success: str) -> ActionResult:
    executable = shutil.which(args[0])
    if not executable:
        return ActionResult(False, f"O utilitário {args[0]} não está instalado.")
    try:
        result = subprocess.run([executable, *args[1:]], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        LOG.error("Falha em %s: %s", args[0], exc)
        return ActionResult(False, f"Não consegui executar {args[0]}.")
    if result.returncode:
        LOG.warning("%s retornou %s: %s", args[0], result.returncode, result.stderr.strip())
        return ActionResult(False, f"{args[0]} não conseguiu completar a ação.")
    return ActionResult(True, success)

"""Informações do sistema usando apenas interfaces nativas do Linux/Python."""
from datetime import datetime
from pathlib import Path
import shutil
import time
from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.core.models import Command, Intent

@registry.register(Intent.GET_TIME)
def get_time(command: Command, context: ActionContext) -> ActionResult:
    return ActionResult(True, f"Agora são {datetime.now():%H:%M}.")

@registry.register(Intent.GET_DATE)
def get_date(command: Command, context: ActionContext) -> ActionResult:
    return ActionResult(True, f"Hoje é {datetime.now():%d/%m/%Y}.")

def _memory_values() -> tuple[int, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, raw = line.split(":", 1)
        values[key] = int(raw.strip().split()[0])
    return values["MemTotal"], values.get("MemAvailable", values.get("MemFree", 0))

@registry.register(Intent.MEMORY_USAGE)
def memory(command: Command, context: ActionContext) -> ActionResult:
    try:
        total, available = _memory_values()
        percent = (total - available) * 100 / total
    except (OSError, ValueError, KeyError, ZeroDivisionError):
        return ActionResult(False, "Não consegui consultar o uso de memória.")
    return ActionResult(True, f"Uso de memória: {percent:.0f} por cento.")

def _cpu_times() -> tuple[int, int]:
    values = [int(value) for value in Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle

@registry.register(Intent.CPU_USAGE)
def cpu(command: Command, context: ActionContext) -> ActionResult:
    try:
        total1, idle1 = _cpu_times()
        time.sleep(0.2)
        total2, idle2 = _cpu_times()
        delta = total2 - total1
        percent = 100 * (1 - (idle2 - idle1) / delta)
    except (OSError, ValueError, IndexError, ZeroDivisionError):
        return ActionResult(False, "Não consegui consultar o uso do processador.")
    return ActionResult(True, f"Uso do processador: {percent:.0f} por cento.")

@registry.register(Intent.DISK_USAGE)
def disk(command: Command, context: ActionContext) -> ActionResult:
    try:
        value = shutil.disk_usage("/")
    except OSError:
        return ActionResult(False, "Não consegui consultar o disco.")
    return ActionResult(True, f"Há {value.free / 1024**3:.1f} gigabytes livres no disco principal.")

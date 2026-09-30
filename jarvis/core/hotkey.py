from __future__ import annotations
import logging
import os
from collections.abc import Callable

LOG = logging.getLogger(__name__)

class GlobalHotkey:
    def __init__(self, key_name: str, callback: Callable[[], None]):
        self.key_name = key_name
        self.callback = callback
        self.listener = None

    def run(self) -> None:
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session == "wayland":
            raise RuntimeError("Hotkey global via pynput não é compatível com Wayland. Entre em uma sessão Cinnamon/X11.")
        if not os.environ.get("DISPLAY"):
            raise RuntimeError("DISPLAY não definido. Inicie o Jarvis dentro da sessão gráfica do usuário.")
        try:
            from pynput import keyboard
        except ImportError as exc:
            raise RuntimeError("pynput não está instalado. Execute ./install.sh") from exc
        key = getattr(keyboard.Key, self.key_name.lower(), None)
        if key is None:
            raise RuntimeError(f"Hotkey não suportada: {self.key_name}")
        pressed = False
        def on_press(current: object) -> None:
            nonlocal pressed
            if current == key and not pressed:
                pressed = True
                self.callback()
        def on_release(current: object) -> None:
            nonlocal pressed
            if current == key:
                pressed = False
        LOG.info("Aguardando hotkey %s", self.key_name)
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            self.listener = listener
            listener.join()

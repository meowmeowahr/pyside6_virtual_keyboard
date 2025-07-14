from typing import ClassVar

from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeyEvent


class GlobalKeyEventBus(QObject):
    instance: "ClassVar[GlobalKeyEventBus | None]" = None
    key_event = Signal(QKeyEvent)

    def __init__(self):
        super().__init__()
        if not GlobalKeyEventBus.instance:
            GlobalKeyEventBus.instance = self
        else:
            msg = f"Can't create more than one instance of {self.__class__.__name__}"
            raise RuntimeError(msg)

    def add_source(self, source: QMainWindow):
        source.grabKeyboard()
        source.keyPressEvent = (
            lambda *args, **kwargs: self.window_key_event_interceptor(
                source, *args, **kwargs
            )
        )

    def window_key_event_interceptor(
        self, window: QMainWindow, event: QKeyEvent
    ) -> None:
        """
        The global event for the phyical keyboard.
        Almost all keys that are recognized by your OS/X11/Wayland are passed through this function
        """

        # kinda janky, but it seems to work perfectly
        # do this before everything else
        focused = window.focusWidget()
        if hasattr(focused, "keyPressEvent") and not hasattr(focused, "_virtual"):
            focused.keyPressEvent(event)
        event.accept()

        self.key_event.emit(event)

class VirtualKeyEventBus(QObject):
    instance: "ClassVar[VirtualKeyEventBus | None]" = None
    key_event = Signal(str)

    def __init__(self):
        super().__init__()
        if not VirtualKeyEventBus.instance:
            VirtualKeyEventBus.instance = self
        else:
            msg = f"Can't create more than one instance of {self.__class__.__name__}"
            raise RuntimeError(msg)
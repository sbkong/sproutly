"""
전역 단축키 매니저
"""
import keyboard
from PySide6.QtCore import QObject, Signal


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self, key_combo: str = 'ctrl+shift+r'):
        super().__init__()
        self.key_combo = key_combo
        self._hotkey_id = None

    def start(self):
        if self._hotkey_id is not None:
            return
        self._hotkey_id = keyboard.add_hotkey(
            self.key_combo,
            lambda: self.triggered.emit(),
        )

    def stop(self):
        if self._hotkey_id is not None:
            keyboard.remove_hotkey(self._hotkey_id)
            self._hotkey_id = None

    def change_key(self, new_combo: str):
        self.stop()
        self.key_combo = new_combo
        self.start()

"""
전역 단축키 매니저
"""
import keyboard
from PySide6.QtCore import QObject, Signal


class HotkeyManager(QObject):
    triggered = Signal()  # 단축키 눌림 (메인 스레드에서 받음)

    def __init__(self, key_combo: str = 'ctrl+shift+r'):
        super().__init__()
        self.key_combo = key_combo
        self._hotkey_id = None

    def start(self):
        if self._hotkey_id is not None:
            return
        # 콜백은 keyboard 내부 스레드에서 호출됨
        # → 시그널 emit으로 메인 스레드 큐에 들어가게
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

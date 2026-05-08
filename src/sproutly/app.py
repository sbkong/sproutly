import os
import sys

from . import logger as app_logger
from sproutly.resources_util import resource_path

log = app_logger.setup_logging()

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from .ui.main_window import MainWindow
except Exception:
    log.exception("초기 import 실패")
    raise


def resource_path(rel: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'sproutly', 'resources', rel)
    if getattr(sys, 'frozen', False):
        return os.path.join(
            os.path.dirname(sys.executable), '_internal',
            'sproutly', 'resources', rel,
        )
    return os.path.join(os.path.dirname(__file__), 'resources', rel)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    icon_path = resource_path('icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    log.info("메인 윈도우 표시됨")
    sys.exit(app.exec())


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log.exception("main() 종료 시 예외")
        raise

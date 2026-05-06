from PySide6.QtCore import QThread, Signal

from sproutly.ocr_engine import OcrEngine
from sproutly.updater import check_for_update


class OcrWorker(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, engine: OcrEngine, image_path: str):
        super().__init__()
        self.engine = engine
        self.image_path = image_path

    def run(self):
        try:
            record = self.engine.extract(self.image_path)
            self.finished_ok.emit(record)
        except Exception as e:
            self.failed.emit(str(e))


class UpdateCheckWorker(QThread):
    finished_with_info = Signal(object)

    def run(self):
        info = check_for_update()
        self.finished_with_info.emit(info)

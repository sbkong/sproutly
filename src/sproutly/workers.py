from PySide6.QtCore import QThread, Signal

from sproutly.ocr_engine import OcrEngine


class OcrWorker(QThread):
    finished_ok = Signal(dict)  # OCR 성공 → record dict
    failed = Signal(str)  # 실패 → 에러 메시지

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

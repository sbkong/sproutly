"""OCR 테스트 결과 표시 다이얼로그"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPlainTextEdit, QPushButton,
)


class OcrTestResultDialog(QDialog):
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OCR 테스트 결과")
        self.resize(560, 480)

        layout = QVBoxLayout(self)

        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")

        lines = []
        for name, items in result.items():
            if items:
                joined = ' | '.join(items)
                lines.append(f"[{name}]")
                lines.append(f"  {joined}")
            else:
                lines.append(f"[{name}]")
                lines.append(f"  (인식 결과 없음)")
            lines.append("")
        text.setPlainText('\n'.join(lines) if lines else "(결과 없음)")

        layout.addWidget(text)

        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
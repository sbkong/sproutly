"""
이미지 드롭 영역 위젯
- 드래그&드롭
- 클릭으로 파일 선택
- 클립보드 붙여넣기 (Ctrl+V는 메인 윈도우에서 처리)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import QLabel, QFileDialog


class DropArea(QLabel):
    image_selected = Signal(str)  # 이미지 경로

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 360)
        self._set_placeholder()

    def _set_placeholder(self):
        self.setText(
            "이미지를 여기에 드래그하거나 클릭하세요\n"
            "(Ctrl+V로 클립보드 붙여넣기 가능)"
        )
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #aaa;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #4a9eff;
                color: #ddd;
            }
        """)

    def show_image(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #4a9eff;
                border-radius: 8px;
                background-color: #1a1a1a;
            }
        """)

    def reset(self):
        self.clear()
        self._set_placeholder()

    # === 드래그&드롭 ===
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
            self.image_selected.emit(path)

    # === 클릭으로 파일 선택 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "이미지 선택",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
            )
            if path:
                self.image_selected.emit(path)

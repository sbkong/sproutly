import webbrowser

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QCheckBox, QSpacerItem, QSizePolicy,
)

from sproutly.updater import UpdateInfo


class UpdateDialog(QDialog):
    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("업데이트 알림")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)

        title = QLabel(f"새 버전이 있습니다: v{info.latest}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        sub = QLabel(f"현재 버전: v{info.current}")
        sub.setStyleSheet("color: #888;")
        layout.addWidget(sub)

        if info.release_notes:
            notes_label = QLabel("변경사항:")
            notes_label.setStyleSheet("padding-top: 8px;")
            layout.addWidget(notes_label)

            notes = QPlainTextEdit()
            notes.setReadOnly(True)
            notes.setPlainText(info.release_notes)
            notes.setMaximumHeight(220)
            layout.addWidget(notes)

        self.skip_check = QCheckBox(f"v{info.latest} 알림 끄기")
        layout.addWidget(self.skip_check)

        btn_row = QHBoxLayout()
        btn_row.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        later_btn = QPushButton("나중에")
        later_btn.clicked.connect(self.reject)
        btn_row.addWidget(later_btn)

        download_btn = QPushButton("다운로드 페이지 열기")
        download_btn.setDefault(True)
        download_btn.clicked.connect(self._open_release)
        btn_row.addWidget(download_btn)

        layout.addLayout(btn_row)

    def _open_release(self):
        webbrowser.open(self.info.release_url)
        self.accept()

    def should_skip_version(self) -> bool:
        return self.skip_check.isChecked()

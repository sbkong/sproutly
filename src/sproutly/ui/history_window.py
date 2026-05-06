from pathlib import Path

from sproutly import db
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QPushButton, QLabel, QSplitter,
    QMessageBox, QPlainTextEdit,
)

SORT_OPTIONS = [
    ("최신순", 'created_at DESC'),
    ("오래된순", 'created_at ASC'),
    ("점수 높은순", 'score DESC'),
    ("점수 낮은순", 'score ASC'),
    ("곡명 A→Z", 'title ASC'),
    ("곡명 Z→A", 'title DESC'),
]


class HistoryWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("이력 보기")
        self.resize(1200, 700)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 상단 검색/정렬
        top = QHBoxLayout()
        top.addWidget(QLabel("검색:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("곡명 일부 입력")
        self.search_edit.returnPressed.connect(self.refresh)
        top.addWidget(self.search_edit, 1)

        top.addWidget(QLabel("정렬:"))
        self.sort_combo = QComboBox()
        for label, _ in SORT_OPTIONS:
            self.sort_combo.addItem(label)
        self.sort_combo.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.sort_combo)

        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)

        # 좌: 테이블, 우: 상세
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "날짜", "곡명", "Buttons", "Score", "Accuracy"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.table)

        # 우측 상세
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(8, 0, 0, 0)

        self.image_label = QLabel("이미지 없음")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(240)
        self.image_label.setStyleSheet("background-color: #1a1a1a; border: 1px solid #444;")
        detail_layout.addWidget(self.image_label, 1)

        self.detail_text = QPlainTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        detail_layout.addWidget(self.detail_text, 2)

        self.delete_btn = QPushButton("선택 항목 삭제")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_selected)
        detail_layout.addWidget(self.delete_btn)

        splitter.addWidget(detail)
        splitter.setSizes([700, 500])
        layout.addWidget(splitter, 1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; padding: 4px;")
        layout.addWidget(self.status_label)

    def refresh(self):
        title_filter = self.search_edit.text().strip()
        order_by = SORT_OPTIONS[self.sort_combo.currentIndex()][1]
        rows = db.list_records(limit=500, title_filter=title_filter, order_by=order_by)

        self.table.setRowCount(len(rows))
        # 컬럼 폭 일부 명시
        widths = [60, 160, 280, 80, 100, 100]
        for i, w in enumerate(widths):
            self.table.setColumnWidth(i, w)

        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(r, 1, QTableWidgetItem(row['created_at']))
            self.table.setItem(r, 2, QTableWidgetItem(row['title']))
            self.table.setItem(r, 3, QTableWidgetItem(str(row['buttons'])))
            self.table.setItem(r, 4, QTableWidgetItem(f"{row['score']:,}"))
            self.table.setItem(r, 5, QTableWidgetItem(row['accuracy'] or ''))

        self.status_label.setText(f"{len(rows)}개 항목")
        self._clear_detail()

    def _on_select(self):
        items = self.table.selectedItems()
        if not items:
            self._clear_detail()
            return

        row = items[0].row()
        record_id = int(self.table.item(row, 0).text())
        record = db.get_record(record_id)
        if not record:
            return

        # 이미지
        if record['image_path'] and Path(record['image_path']).exists():
            pixmap = QPixmap(record['image_path'])
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("이미지 파일 없음")

        # 상세 텍스트
        d = dict(record)
        lines = [
            f"ID:         {d['id']}",
            f"저장일:      {d['created_at']}",
            f"곡명:       {d['title']}",
            f"Buttons:    {d['buttons']}",
            f"Score:      {d['score']:,}",
            f"Accuracy:   {d['accuracy']}",
            f"Score↑:     {bool(d['is_score_grown'])}",
            f"Acc↑:       {bool(d['is_accuracy_grown'])}",
            "",
            "─ JUDGEMENT ─",
            f"MAX 100:    {d['max_100']}",
            f"MAX 90:     {d['max_90']}",
            f"MAX 80:     {d['max_80']}",
            f"MAX 70:     {d['max_70']}",
            f"MAX 60:     {d['max_60']}",
            f"MAX 50:     {d['max_50']}",
            f"MAX 40:     {d['max_40']}",
            f"MAX 30:     {d['max_30']}",
            f"MAX 20:     {d['max_20']}",
            f"MAX 10:     {d['max_10']}",
            f"MAX 1:      {d['max_1']}",
            f"BREAK:      {d['break_count']}",
            "",
            f"이미지:      {d['image_path']}",
        ]
        self.detail_text.setPlainText('\n'.join(lines))
        self.delete_btn.setEnabled(True)

    def _clear_detail(self):
        self.image_label.clear()
        self.image_label.setText("선택된 항목 없음")
        self.detail_text.clear()
        self.delete_btn.setEnabled(False)

    def _delete_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        record_id = int(self.table.item(row, 0).text())
        title = self.table.item(row, 2).text()

        reply = QMessageBox.question(
            self, "삭제 확인",
            f"id={record_id} ({title}) 항목을 삭제할까요?\n원본 이미지 파일도 함께 삭제됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_record(record_id)
            self.refresh()

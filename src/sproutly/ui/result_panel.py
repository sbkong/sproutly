from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel,
)

FIELDS = [
    ("Title", "title", "str"),
    ("Buttons", "buttons", "int"),
    ("Score", "score", "int"),
    ("Accuracy", "accuracy", "str"),
    ("Score Grown", "is_score_grown", "bool"),
    ("Accuracy Grown", "is_accuracy_grown", "bool"),
    ("MAX 100% (요약)", "max_100_count", "int"),
    ("MAX 1~90% (요약)", "max_1_90_count", "int"),
    ("BREAK (요약)", "break_count", "int"),
    ("─ 판정 디테일 ─", None, "sep"),
    ("MAX 100", "judgement.max_100", "int"),
    ("MAX 90", "judgement.max_90", "int"),
    ("MAX 80", "judgement.max_80", "int"),
    ("MAX 70", "judgement.max_70", "int"),
    ("MAX 60", "judgement.max_60", "int"),
    ("MAX 50", "judgement.max_50", "int"),
    ("MAX 40", "judgement.max_40", "int"),
    ("MAX 30", "judgement.max_30", "int"),
    ("MAX 20", "judgement.max_20", "int"),
    ("MAX 10", "judgement.max_10", "int"),
    ("MAX 1", "judgement.max_1", "int"),
    ("BREAK", "judgement.break", "int"),
]


def _get_nested(d: dict, path: str):
    cur = d
    for part in path.split('.'):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _set_nested(d: dict, path: str, value):
    parts = path.split('.')
    cur = d
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


class ResultPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._record: dict | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("결과 없음")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        layout.addWidget(self.title_label)

        hint = QLabel("값 셀을 더블클릭해서 수정 가능 (OCR 오인식 수정용)")
        hint.setStyleSheet("color: #888; font-size: 11px; padding: 0 4px 4px 4px;")
        layout.addWidget(hint)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["항목", "값"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def show_record(self, record: dict):
        self._record = record
        self.title_label.setText(record.get('title', '-') or '-')

        self.table.setRowCount(len(FIELDS))
        for i, (label, key, kind) in enumerate(FIELDS):
            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, label_item)

            if kind == 'sep':
                val_item = QTableWidgetItem('─' * 20)
                val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, 1, val_item)
                continue

            value = _get_nested(record, key)
            if kind == 'bool':
                display = '🔺' if value else '-'
                val_item = QTableWidgetItem(display)
                val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            elif kind == 'int':
                val_item = QTableWidgetItem(str(int(value) if value is not None else 0))
            else:  # str
                val_item = QTableWidgetItem(str(value) if value is not None else '')

            self.table.setItem(i, 1, val_item)

    def get_edited_record(self) -> dict | None:
        """현재 테이블 값 반영해서 record dict 반환"""
        if self._record is None:
            return None

        import copy
        result = copy.deepcopy(self._record)

        for i, (label, key, kind) in enumerate(FIELDS):
            if kind in ('sep', 'bool') or key is None:
                continue
            cell = self.table.item(i, 1)
            if cell is None:
                continue
            text = cell.text().strip()

            if kind == 'int':
                try:
                    val = int(text.replace(',', '').replace('O', '0'))
                except ValueError:
                    val = 0
                _set_nested(result, key, val)
            else:
                _set_nested(result, key, text)

        return result

    def clear(self):
        self._record = None
        self.title_label.setText("결과 없음")
        self.table.setRowCount(0)

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QComboBox, QCheckBox, QDoubleSpinBox, QKeySequenceEdit, QGroupBox, QDialogButtonBox, QMessageBox,
)

from sproutly import config
from sproutly.screen_capture import list_monitors


def qkey_to_keyboard_str(seq: QKeySequence) -> str:
    s = seq.toString(QKeySequence.SequenceFormat.PortableText)
    return s.lower().replace(' ', '')


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setMinimumWidth(440)

        self.cfg = config.load()
        self._build_ui()
        self._load_to_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        hotkey_group = QGroupBox("전역 단축키")
        hotkey_form = QFormLayout(hotkey_group)

        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setMaximumSequenceLength(1)
        hotkey_form.addRow("캡처 단축키:", self.hotkey_edit)

        hotkey_hint = QLabel("키 조합을 직접 누르세요 (예: Ctrl+Shift+R)")
        hotkey_hint.setStyleSheet("color: #888; font-size: 11px;")
        hotkey_form.addRow("", hotkey_hint)

        root.addWidget(hotkey_group)

        capture_group = QGroupBox("캡처")
        capture_form = QFormLayout(capture_group)

        self.target_combo = QComboBox()
        self.target_combo.addItem("마우스 커서가 있는 모니터", "cursor")
        self.target_combo.addItem("주 모니터 (1번)", "primary")
        for mon in list_monitors():
            self.target_combo.addItem(mon['label'], f"monitor:{mon['index']}")
        capture_form.addRow("캡처 대상:", self.target_combo)

        self.auto_save_check = QCheckBox("OCR 후 자동으로 DB에 저장")
        capture_form.addRow("자동 저장:", self.auto_save_check)

        root.addWidget(capture_group)

        update_group = QGroupBox("업데이트")
        update_form = QFormLayout(update_group)

        self.update_check_check = QCheckBox("앱 시작 시 자동으로 업데이트 확인")
        update_form.addRow("", self.update_check_check)

        root.addWidget(update_group)

        ocr_group = QGroupBox("OCR")
        ocr_form = QFormLayout(ocr_group)

        self.score_thresh_spin = QDoubleSpinBox()
        self.score_thresh_spin.setRange(0.0, 1.0)
        self.score_thresh_spin.setSingleStep(0.05)
        self.score_thresh_spin.setDecimals(2)
        ocr_form.addRow("텍스트 신뢰도 임계값:", self.score_thresh_spin)

        self.red_ratio_spin = QDoubleSpinBox()
        self.red_ratio_spin.setRange(0.0001, 0.1)
        self.red_ratio_spin.setSingleStep(0.001)
        self.red_ratio_spin.setDecimals(4)
        ocr_form.addRow("빨간 화살표 임계 비율:", self.red_ratio_spin)

        ocr_hint = QLabel("점수/정확도 갱신(▲) 판정 민감도. 작을수록 민감.")
        ocr_hint.setStyleSheet("color: #888; font-size: 11px;")
        ocr_form.addRow("", ocr_hint)

        root.addWidget(ocr_group)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )
        root.addWidget(btn_box)

    def _load_to_ui(self):
        self.hotkey_edit.setKeySequence(QKeySequence(self.cfg['hotkey']))

        target = self.cfg.get('capture_target', 'cursor')
        idx = self.target_combo.findData(target)
        self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.auto_save_check.setChecked(bool(self.cfg.get('auto_save', False)))

        self.update_check_check.setChecked(bool(self.cfg.get('update_check', True)))

        self.score_thresh_spin.setValue(float(self.cfg.get('ocr_score_thresh', 0.5)))
        self.red_ratio_spin.setValue(float(self.cfg.get('red_arrow_ratio', 0.005)))

    def _restore_defaults(self):
        self.cfg = config.DEFAULTS.copy()
        self._load_to_ui()

    def _accept(self):
        seq = self.hotkey_edit.keySequence()
        if seq.isEmpty():
            QMessageBox.warning(self, "단축키 오류", "단축키를 입력하세요.")
            return

        new_cfg = dict(self.cfg)
        new_cfg.update({
            'hotkey': qkey_to_keyboard_str(seq),
            'capture_target': self.target_combo.currentData(),
            'auto_save': self.auto_save_check.isChecked(),
            'ocr_score_thresh': self.score_thresh_spin.value(),
            'red_arrow_ratio': self.red_ratio_spin.value(),
            'update_check': self.update_check_check.isChecked(),
        })

        try:
            config.save(new_cfg)
            self.cfg = new_cfg
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))
            return

        self.accept()

    def get_config(self) -> dict:
        return self.cfg

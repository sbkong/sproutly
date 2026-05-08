"""
ROI 편집 다이얼로그
"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QSpinBox, QPushButton, QSplitter,
    QWidget, QGroupBox, QMessageBox, QCheckBox,
)

from sproutly.rois import (
    load_presets, get_active_state, load_active_rois,
    save_custom_rois, set_active_preset, )
from sproutly.ui.ocr_test_dialog import OcrTestResultDialog
from sproutly.ui.roi_canvas import RoiCanvas

log = logging.getLogger('sproutly.roi_editor')


class RoiEditorDialog(QDialog):
    def __init__(self, image_path: str, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ROI 편집")
        self.resize(1200, 720)

        self._image_path = image_path
        self._engine = engine
        self._dirty = False

        self._initial_rois = load_active_rois()
        self._initial_state = get_active_state()

        self._build_ui()
        self._populate_presets()
        self._load_current()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # 프리셋 선택
        top = QHBoxLayout()
        top.addWidget(QLabel("프리셋:"))
        self.preset_combo = QComboBox()
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        top.addWidget(self.preset_combo, 1)
        root.addLayout(top)

        # 캔버스 + 사이드 패널
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.canvas = RoiCanvas()
        self.canvas.selection_changed.connect(self._on_canvas_selection)
        self.canvas.roi_changed.connect(self._on_roi_changed)
        self.canvas.roi_deleted.connect(self._on_roi_deleted)
        splitter.addWidget(self.canvas)

        self.show_labels_check = QCheckBox("ROI 이름 표시")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.toggled.connect(self.canvas.set_show_labels)
        top.addWidget(self.show_labels_check)

        # 우측 패널
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        # ROI 리스트
        right_layout.addWidget(QLabel("ROI 목록"))
        self.roi_list = QListWidget()
        self.roi_list.itemSelectionChanged.connect(self._on_list_changed)
        right_layout.addWidget(self.roi_list, 1)

        # 좌표 입력
        coord_box = QGroupBox("선택된 박스 좌표")
        coord_form = QFormLayout(coord_box)
        self.x1_spin = QSpinBox();
        self.x1_spin.setRange(0, 10000)
        self.y1_spin = QSpinBox();
        self.y1_spin.setRange(0, 10000)
        self.x2_spin = QSpinBox();
        self.x2_spin.setRange(0, 10000)
        self.y2_spin = QSpinBox();
        self.y2_spin.setRange(0, 10000)
        for w in (self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin):
            w.setEnabled(False)
            w.editingFinished.connect(self._on_coord_edited)
        coord_form.addRow("X1:", self.x1_spin)
        coord_form.addRow("Y1:", self.y1_spin)
        coord_form.addRow("X2:", self.x2_spin)
        coord_form.addRow("Y2:", self.y2_spin)
        right_layout.addWidget(coord_box)

        splitter.addWidget(right)
        splitter.setSizes([900, 280])
        root.addWidget(splitter, 1)

        # 하단 버튼
        btn_row = QHBoxLayout()

        self.test_btn = QPushButton("테스트 OCR")
        self.test_btn.clicked.connect(self._on_test_ocr)
        btn_row.addWidget(self.test_btn)

        self.reset_btn = QPushButton("기본값 복원")
        self.reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(self.reset_btn)

        btn_row.addStretch(1)

        self.save_btn = QPushButton("저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        root.addLayout(btn_row)

    def _populate_presets(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for p in load_presets():
            self.preset_combo.addItem(p.name, p.id)
        if self._initial_state['mode'] == 'custom':
            self.preset_combo.addItem("Custom (사용자 편집본)", "custom")
            self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)
        else:
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == self._initial_state['preset_id']:
                    self.preset_combo.setCurrentIndex(i)
                    break
        self.preset_combo.blockSignals(False)

    def _load_current(self):
        self.canvas.set_image(self._image_path)
        self.canvas.set_rois(self._initial_rois)
        self._refresh_roi_list()

    def _refresh_roi_list(self):
        self.roi_list.blockSignals(True)
        self.roi_list.clear()
        for r in self.canvas.get_rois():
            self.roi_list.addItem(QListWidgetItem(r.name))
        self.roi_list.blockSignals(False)

    def _on_preset_changed(self, index: int):
        if index < 0:
            return
        preset_id = self.preset_combo.itemData(index)
        if preset_id == 'custom':
            return

        if self._dirty:
            ans = QMessageBox.question(
                self, "변경사항 폐기",
                "변경한 내용이 있습니다. 폐기하고 프리셋으로 전환할까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                self.preset_combo.blockSignals(True)
                self.preset_combo.blockSignals(False)
                return

        from sproutly.rois import get_preset
        preset = get_preset(preset_id)
        if preset:
            self.canvas.set_rois(preset.rois)
            self._refresh_roi_list()
            self._set_dirty(False)
            self._update_coord_inputs(None)

    def _on_canvas_selection(self, name: str):
        self.roi_list.blockSignals(True)
        if name:
            for i in range(self.roi_list.count()):
                if self.roi_list.item(i).text() == name:
                    self.roi_list.setCurrentRow(i)
                    break
        else:
            self.roi_list.clearSelection()
        self.roi_list.blockSignals(False)

        roi = self._find_roi(name) if name else None
        self._update_coord_inputs(roi)

    def _on_list_changed(self):
        items = self.roi_list.selectedItems()
        if not items:
            self.canvas.select_roi('')
            return
        name = items[0].text()
        self.canvas.select_roi(name)

    def _on_roi_changed(self, name: str):
        roi = self._find_roi(name)
        self._update_coord_inputs(roi)
        self._set_dirty(True)
        self._mark_as_custom()

    def _on_roi_deleted(self, name: str):
        self._refresh_roi_list()
        self._set_dirty(True)
        self._mark_as_custom()
        QMessageBox.information(
            self, "박스 삭제됨",
            f"'{name}' 박스가 너무 작아 삭제되었습니다.\n"
            f"되살리려면 '기본값 복원'을 누르세요.",
        )

    def _on_coord_edited(self):
        if self.x1_spin.isEnabled():
            self.canvas.update_selected_rect(
                self.x1_spin.value(), self.y1_spin.value(),
                self.x2_spin.value(), self.y2_spin.value(),
            )
            self._set_dirty(True)
            self._mark_as_custom()

    def _find_roi(self, name: str):
        for r in self.canvas.get_rois():
            if r.name == name:
                return r
        return None

    def _update_coord_inputs(self, roi):
        enabled = roi is not None
        for w in (self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin):
            w.blockSignals(True)
            w.setEnabled(enabled)
        if roi:
            self.x1_spin.setValue(roi.x1)
            self.y1_spin.setValue(roi.y1)
            self.x2_spin.setValue(roi.x2)
            self.y2_spin.setValue(roi.y2)
        for w in (self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin):
            w.blockSignals(False)

    def _set_dirty(self, dirty: bool):
        self._dirty = dirty
        self.save_btn.setEnabled(dirty)

    def _mark_as_custom(self):
        idx = self.preset_combo.findData('custom')
        if idx < 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.addItem("Custom (사용자 편집본)", "custom")
            idx = self.preset_combo.count() - 1
            self.preset_combo.setCurrentIndex(idx)
            self.preset_combo.blockSignals(False)
        elif self.preset_combo.currentIndex() != idx:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(idx)
            self.preset_combo.blockSignals(False)

    def _on_test_ocr(self):
        rois = self.canvas.get_rois()
        if not rois:
            QMessageBox.warning(self, "테스트 불가", "ROI가 없습니다.")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("OCR 실행 중...")
        try:
            result = self._engine.extract_raw(self._image_path, rois)
        except Exception as e:
            log.exception("OCR 테스트 실패")
            QMessageBox.critical(self, "OCR 실패", str(e))
            return
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("테스트 OCR")

        dlg = OcrTestResultDialog(result, self)
        dlg.exec()

    def _on_reset(self):
        ans = QMessageBox.question(
            self, "기본값 복원",
            "현재 프리셋의 기본 좌표로 되돌립니다. 계속할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        preset_id = self.preset_combo.currentData()
        if preset_id == 'custom':
            preset_id = self.preset_combo.itemData(0)

        from sproutly.rois import get_preset
        preset = get_preset(preset_id)
        if preset:
            self.canvas.set_rois(preset.rois)
            self._refresh_roi_list()
            custom_idx = self.preset_combo.findData('custom')
            self.preset_combo.blockSignals(True)
            if custom_idx >= 0:
                self.preset_combo.removeItem(custom_idx)
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemData(i) == preset_id:
                    self.preset_combo.setCurrentIndex(i)
                    break
            self.preset_combo.blockSignals(False)
            self._set_dirty(True)

    def _on_save(self):
        rois = self.canvas.get_rois()
        if not rois:
            QMessageBox.warning(self, "저장 불가", "최소 1개 이상의 ROI가 필요합니다.")
            return

        preset_id = self.preset_combo.currentData()
        if preset_id == 'custom':
            save_custom_rois(rois, self._initial_state.get('resolution', (1920, 1080)))
        else:
            set_active_preset(preset_id)

        self._set_dirty(False)
        self.accept()

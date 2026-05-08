import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QGuiApplication, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStatusBar, QMessageBox, QSplitter,
    QDialog,
)

from sproutly import config
from sproutly import db
from sproutly.hotkey_manager import HotkeyManager
from sproutly.ocr_engine import OcrEngine
from sproutly.rois import load_active_rois
from sproutly.screen_capture import capture_by_target
from sproutly.ui.drop_area import DropArea
from sproutly.ui.history_window import HistoryWindow
from sproutly.ui.result_panel import ResultPanel
from sproutly.ui.roi_editor_dialog import RoiEditorDialog
from sproutly.ui.settings_dialog import SettingsDialog
from sproutly.ui.stats_window import StatsWindow
from sproutly.ui.update_dialog import UpdateDialog
from sproutly.workers import OcrWorker, UpdateCheckWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sproutly")
        self.resize(1280, 720)

        self.cfg = config.load()

        self.engine = OcrEngine(
            score_thresh=self.cfg['ocr_score_thresh'],
            red_arrow_ratio=self.cfg['red_arrow_ratio'],
        )

        self.current_image_path: str | None = None
        self.worker: OcrWorker | None = None
        self.history_window: HistoryWindow | None = None
        self.stats_window: StatsWindow | None = None

        self.auto_save = self.cfg['auto_save']

        self._build_ui()
        self._build_menu()
        self._setup_shortcuts()

        db.init_db()

        self.hotkey = HotkeyManager(self.cfg['hotkey'])
        self.hotkey.triggered.connect(self.on_hotkey_capture)
        self.hotkey.start()

        self.update_worker: UpdateCheckWorker | None = None
        if self.cfg.get('update_check', True):
            self._start_update_check(silent=True)

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.drop_area = DropArea()
        self.drop_area.image_selected.connect(self.load_image)
        left_layout.addWidget(self.drop_area)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_record)
        self.clear_btn = QPushButton("초기화")
        self.clear_btn.clicked.connect(self.reset)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.clear_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        self.result_panel = ResultPanel()
        splitter.addWidget(self.result_panel)

        splitter.setSizes([720, 560])
        self.setCentralWidget(splitter)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("이미지를 드롭하거나 Ctrl+V로 붙여넣으세요")

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일")
        history_action = QAction("이력 보기...", self)
        history_action.setShortcut("Ctrl+H")
        history_action.triggered.connect(self.show_history)
        file_menu.addAction(history_action)

        roi_action = QAction("ROI 편집...", self)
        roi_action.setShortcut("Ctrl+Shift+E")
        roi_action.triggered.connect(self.open_roi_editor)
        file_menu.addAction(roi_action)

        stats_action = QAction("통계...", self)
        stats_action.setShortcut("Ctrl+T")
        stats_action.triggered.connect(self.show_stats)
        file_menu.addAction(stats_action)

        file_menu.addSeparator()

        quit_action = QAction("종료", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        capture_menu = menubar.addMenu("캡처")

        capture_action = QAction("화면 캡처 (Ctrl+Shift+R)", self)
        capture_action.triggered.connect(self.on_hotkey_capture)
        capture_menu.addAction(capture_action)

        capture_menu.addSeparator()

        self.auto_save_action = QAction("자동 저장 모드", self, checkable=True)
        self.auto_save_action.setChecked(self.auto_save)
        self.auto_save_action.toggled.connect(self._toggle_auto_save)
        capture_menu.addAction(self.auto_save_action)

        file_menu.addSeparator()

        settings_action = QAction("설정...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        help_menu = menubar.addMenu("도움말")

        check_update_action = QAction("업데이트 확인...", self)
        check_update_action.triggered.connect(lambda: self._start_update_check(silent=False))
        help_menu.addAction(check_update_action)

        about_action = QAction("정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_shortcuts(self):
        paste = QShortcut(QKeySequence.StandardKey.Paste, self)
        paste.activated.connect(self.paste_from_clipboard)

    def load_image(self, path: str):
        self.current_image_path = path
        self.drop_area.show_image(path)
        self.result_panel.clear()
        self.save_btn.setEnabled(False)
        self.statusBar().showMessage(f"OCR 실행 중... ({Path(path).name})")

        self.worker = OcrWorker(self.engine, path)
        self.worker.finished_ok.connect(self._on_ocr_done)
        self.worker.failed.connect(self._on_ocr_failed)
        self.worker.start()

    def paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        img = clipboard.image()
        if img.isNull():
            self.statusBar().showMessage("클립보드에 이미지가 없습니다")
            return

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix='clip_')
        tmp.close()
        img.save(tmp.name, 'PNG')
        self.load_image(tmp.name)

    def _on_ocr_done(self, record: dict):
        self.result_panel.show_record(record)
        self.save_btn.setEnabled(True)

        if self.auto_save:
            self.save_record()
            self.statusBar().showMessage("자동 저장 완료. 다음 캡처를 기다리는 중...")
        else:
            self.statusBar().showMessage("OCR 완료. 값 수정 가능. 저장 버튼을 누르세요")

    def _on_ocr_failed(self, msg: str):
        QMessageBox.critical(self, "OCR 실패", msg)
        self.statusBar().showMessage("OCR 실패")

    def save_record(self):
        record = self.result_panel.get_edited_record()
        if not record or not self.current_image_path:
            return

        try:
            img_hash = db.calc_image_hash(self.current_image_path)
            existing = db.find_by_hash(img_hash)
            if existing:
                reply = QMessageBox.question(
                    self,
                    "중복 이미지 감지",
                    f"이 이미지는 이미 저장되어 있습니다.\n\n"
                    f"기존 ID: {existing['id']}\n"
                    f"저장일: {existing['created_at']}\n"
                    f"곡명: {existing['title']}\n\n"
                    f"그래도 새로 저장할까요?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.statusBar().showMessage("저장 취소됨")
                    return
        except Exception as e:
            print(f"hash check failed: {e}")

        try:
            new_id = db.save_record(record, source_image=self.current_image_path)
            self.statusBar().showMessage(f"저장 완료 (id={new_id})")
            self.save_btn.setEnabled(False)
            if self.history_window and self.history_window.isVisible():
                self.history_window.refresh()
            if self.stats_window and self.stats_window.isVisible():
                self.stats_window.refresh()
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))

    def reset(self):
        self.current_image_path = None
        self.drop_area.reset()
        self.result_panel.clear()
        self.save_btn.setEnabled(False)
        self.statusBar().showMessage("초기화됨")

    def show_history(self):
        if self.history_window is None:
            self.history_window = HistoryWindow()
        self.history_window.refresh()
        self.history_window.show()
        self.history_window.raise_()
        self.history_window.activateWindow()

    def _toggle_auto_save(self, checked: bool):
        self.auto_save = checked
        self.cfg['auto_save'] = checked
        config.save(self.cfg)
        msg = "자동 저장 모드 ON (캡처 후 즉시 DB 저장)" if checked else "자동 저장 모드 OFF"
        self.statusBar().showMessage(msg)

    def on_hotkey_capture(self):
        try:
            path = capture_by_target(self.cfg['capture_target'])
        except Exception as e:
            QMessageBox.critical(self, "캡처 실패", str(e))
            return

        self.raise_()
        self.activateWindow()
        self.load_image(path)

    def show_stats(self):
        if self.stats_window is None:
            self.stats_window = StatsWindow()
        self.stats_window.refresh()
        self.stats_window.show()
        self.stats_window.raise_()
        self.stats_window.activateWindow()

    def closeEvent(self, event):
        if hasattr(self, 'hotkey'):
            self.hotkey.stop()
        super().closeEvent(event)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_cfg = dlg.get_config()
            self._apply_config(new_cfg)
            self.statusBar().showMessage("설정이 저장되었습니다")

    def _apply_config(self, new_cfg: dict):
        old_hotkey = self.cfg.get('hotkey')
        self.cfg = new_cfg

        if new_cfg['hotkey'] != old_hotkey:
            try:
                self.hotkey.change_key(new_cfg['hotkey'])
            except Exception as e:
                QMessageBox.warning(self, "단축키 등록 실패",
                                    f"{e}\n다른 키 조합을 시도하세요.")

        self.auto_save = new_cfg['auto_save']
        self.auto_save_action.setChecked(self.auto_save)

        self.engine.update_thresholds(
            new_cfg['ocr_score_thresh'],
            new_cfg['red_arrow_ratio'],
        )

    def _start_update_check(self, silent: bool):
        """
        silent=True: 자동 체크 (시작 시) - 업데이트 있을 때만 알림
        silent=False: 수동 체크 (메뉴) - 결과 무조건 알림
        """
        if self.update_worker and self.update_worker.isRunning():
            return  # 이미 진행 중

        self._update_silent = silent
        self.update_worker = UpdateCheckWorker()
        self.update_worker.finished_with_info.connect(self._on_update_check_done)
        self.update_worker.start()

    def _on_update_check_done(self, info):
        if info is None:
            if not self._update_silent:
                QMessageBox.warning(self, "업데이트 확인 실패",
                                    "업데이트 정보를 가져올 수 없습니다.\n인터넷 연결을 확인하세요.")
            return

        if not info.is_update_available:
            if not self._update_silent:
                QMessageBox.information(self, "최신 버전",
                                        f"현재 최신 버전입니다 (v{info.current}).")
            return

        skipped = self.cfg.get('skipped_update_version', '')
        if self._update_silent and skipped == info.latest:
            return

        dlg = UpdateDialog(info, self)
        dlg.exec()
        if dlg.should_skip_version():
            self.cfg['skipped_update_version'] = info.latest
            config.save(self.cfg)

    def _show_about(self):
        from sproutly import __version__
        QMessageBox.about(self, "Sproutly 정보",
                          f"<h3>Sproutly</h3>"
                          f"<p>버전 v{__version__}</p>"
                          f"<p>성과 기록 도구</p>"
                          f"<p><a href='https://github.com/sbkong/sproutly'>GitHub</a></p>"
                          )

    def open_roi_editor(self):
        if not self.current_image_path:
            QMessageBox.information(
                self, "알림",
                "먼저 이미지를 로드하거나 캡처하세요.\n"
                "(현재 표시된 이미지를 기준으로 ROI를 편집합니다)",
            )
            return

        dlg = RoiEditorDialog(
            image_path=self.current_image_path,
            engine=self.engine,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.engine.reload_rois()
            try:
                self.drop_area.set_rois(load_active_rois())
            except AttributeError:
                pass
            self.statusBar().showMessage("ROI 설정이 저장되었습니다")

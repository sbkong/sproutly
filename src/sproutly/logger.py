"""
앱 전역 로깅 시스템

- logs/YYYY-MM-DD.log 형식으로 일자별 로그
- 미처리 예외 → 별도 crash 로그
- Qt 내부 메시지도 같은 로그로 흘림
- 30일 지난 로그 자동 삭제
"""
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from sproutly.paths import LOG_DIR

LOG_RETENTION_DAYS = 30
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3

_logger: logging.Logger | None = None


def _cleanup_old_logs():
    """LOG_RETENTION_DAYS보다 오래된 로그 삭제"""
    if not LOG_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for f in LOG_DIR.glob('*.log*'):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
        except Exception:
            pass


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """앱 시작 시 한 번 호출"""
    global _logger
    if _logger is not None:
        return _logger

    LOG_DIR.mkdir(exist_ok=True)
    _cleanup_old_logs()

    today = datetime.now().strftime('%Y-%m-%d')
    log_path = LOG_DIR / f'{today}.log'

    logger = logging.getLogger('sproutly')
    logger.setLevel(level)
    logger.propagate = False

    # 중복 핸들러 방지
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # 파일 핸들러 (회전)
    fh = RotatingFileHandler(
        log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8',
    )
    fh.setFormatter(fmt)
    fh.setLevel(level)
    logger.addHandler(fh)

    # 콘솔 출력 (개발 환경 / SPROUTLY_DEBUG=1 시)
    if not getattr(sys, 'frozen', False) or os.environ.get('SPROUTLY_DEBUG') == '1':
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        ch.setLevel(level)
        logger.addHandler(ch)

    # 미처리 예외 훅
    sys.excepthook = _excepthook

    # Qt 메시지 핸들러 연결 (PySide6 import 후 실행)
    _install_qt_handler()

    _logger = logger
    logger.info("=" * 60)
    logger.info(f"앱 시작 (frozen={getattr(sys, 'frozen', False)})")
    logger.info(f"로그 디렉토리: {LOG_DIR}")
    return logger


def get_logger() -> logging.Logger:
    if _logger is None:
        return setup_logging()
    return _logger


def _excepthook(exc_type, exc_value, exc_tb):
    """미처리 예외 → 로그 파일 + 메시지박스"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log = get_logger()
    log.critical(f"미처리 예외:\n{msg}")

    # GUI 메시지박스 (가능하면)
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        if QApplication.instance():
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("오류 발생")
            box.setText("예기치 못한 오류가 발생했습니다.")
            box.setInformativeText(f"로그 파일: {LOG_DIR}")
            box.setDetailedText(msg)
            box.exec()
    except Exception:
        pass


def _install_qt_handler():
    """Qt 내부 경고/에러도 로그로"""
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        return

    log = logging.getLogger('sproutly.qt')

    level_map = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(msg_type, context, message):
        level = level_map.get(msg_type, logging.INFO)
        log.log(level, message)

    qInstallMessageHandler(handler)

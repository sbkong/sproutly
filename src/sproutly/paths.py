"""런타임 데이터 경로 관리"""
import sys
from pathlib import Path


def app_root() -> Path:
    """
    런타임 데이터를 저장할 루트 디렉토리.
    - 개발 환경: 프로젝트 루트의 data/
    - exe 환경: exe 옆의 data/
    """
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        # src/sproutly/paths.py → 프로젝트 루트는 두 단계 위
        base = Path(__file__).resolve().parents[2]

    data_dir = base / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir


# 자주 쓰는 경로들
DATA_DIR = app_root()
DB_PATH = DATA_DIR / 'records.db'
IMAGE_DIR = DATA_DIR / 'images'
CROPS_DIR = DATA_DIR / 'crops'
LOG_DIR = DATA_DIR / 'logs'
CONFIG_PATH = DATA_DIR / 'config.json'

for d in (IMAGE_DIR, CROPS_DIR, LOG_DIR):
    d.mkdir(exist_ok=True)

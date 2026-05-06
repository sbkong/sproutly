import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parents[2]

    data_dir = base / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir


DATA_DIR = app_root()
DB_PATH = DATA_DIR / 'records.db'
IMAGE_DIR = DATA_DIR / 'images'
CROPS_DIR = DATA_DIR / 'crops'
LOG_DIR = DATA_DIR / 'logs'
CONFIG_PATH = DATA_DIR / 'config.json'

for d in (IMAGE_DIR, CROPS_DIR, LOG_DIR):
    d.mkdir(exist_ok=True)

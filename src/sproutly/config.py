import json
from copy import deepcopy

from sproutly.paths import CONFIG_PATH

DEFAULTS = {
    'hotkey': 'ctrl+shift+r',
    'capture_target': 'cursor',  # 'cursor' | 'primary' | 'monitor:N'
    'auto_save': False,
    'ocr_score_thresh': 0.5,
    'red_arrow_ratio': 0.005,
    'update_check': True,
    'skipped_update_version': '',
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        return deepcopy(DEFAULTS)
    try:
        with CONFIG_PATH.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return deepcopy(DEFAULTS)

    merged = deepcopy(DEFAULTS)
    merged.update(data)
    return merged


def save(cfg: dict):
    with CONFIG_PATH.open('w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

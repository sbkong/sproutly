import os

os.environ['FLAGS_use_mkldnn'] = '0'

import re
from PIL import Image
import numpy as np
from paddleocr import PaddleOCR

from sproutly.paths import CROPS_DIR
from sproutly.rois import load_active_rois


def to_int(s: str) -> int:
    s = s.replace('O', '0').replace('o', '0').replace(' ', '')
    return int(s) if s.isdigit() else 0


def has_red_arrow(img: Image.Image, threshold_ratio: float = 0.005) -> bool:
    arr = np.array(img.convert('RGB'))
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    red_mask = (r > 180) & (g < 100) & (b < 100)
    ratio = red_mask.sum() / red_mask.size
    return bool(ratio >= threshold_ratio)


def parse_judgement(texts: list[str]) -> dict:
    result = {}
    label_pattern = re.compile(r'MAX\s*(\d+)%', re.IGNORECASE)

    current_key = None
    for tok in texts:
        tok_stripped = tok.strip()

        m = label_pattern.match(tok_stripped)
        if m:
            current_key = f"max_{m.group(1)}"
            continue
        if tok_stripped.upper() == 'BREAK':
            current_key = 'break'
            continue
        if tok_stripped.upper() == 'JUDGEMENT DETAILS':
            continue

        if current_key is not None:
            result[current_key] = to_int(tok_stripped)
            current_key = None

    expected_keys = [f"max_{p}" for p in (100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 1)] + ['break']
    for key in expected_keys:
        result.setdefault(key, 0)

    return result


class OcrEngine:
    def __init__(self, score_thresh: float = 0.5, red_arrow_ratio: float = 0.005):
        self._ocr = None
        self.score_thresh = score_thresh
        self.red_arrow_ratio = red_arrow_ratio
        self._rois = load_active_rois()

    def _ensure_loaded(self):
        if self._ocr is None:
            self._ocr = PaddleOCR(
                lang='en',
                enable_mkldnn=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

    def reload_rois(self):
        self._rois = load_active_rois()

    def extract(self, image_path: str, override_rois=None) -> dict:
        self._ensure_loaded()

        rois = override_rois if override_rois is not None else self._rois

        img = Image.open(image_path)
        raw = {}
        crops = {}
        CROPS_DIR.mkdir(exist_ok=True)

        for roi in rois:
            crop = img.crop((roi.x1, roi.y1, roi.x2, roi.y2))
            crop_path = str(CROPS_DIR / f'{roi.name}.png')
            crop.save(crop_path)
            crops[roi.name] = crop

            result = self._ocr.predict(crop_path)
            texts = result[0]['rec_texts']
            scores = result[0]['rec_scores']
            filtered = [t for t, s in zip(texts, scores) if s >= self.score_thresh]
            raw[roi.name] = filtered

        record = {
            'title': raw.get('title', [''])[0] if raw.get('title') else '',
            'buttons': to_int(raw.get('buttons', ['0'])[0]) if raw.get('buttons') else 0,
            'score': to_int(raw.get('score', ['0'])[0]) if raw.get('score') else 0,
            'accuracy': raw.get('judgement_total', [''])[0] if raw.get('judgement_total') else '',
            'max_100_count': to_int(raw.get('max_100', ['0'])[0]) if raw.get('max_100') else 0,
            'max_1_90_count': to_int(raw.get('max_1_90', ['0'])[0]) if raw.get('max_1_90') else 0,
            'break_count': to_int(raw.get('break_top', ['0'])[0]) if raw.get('break_top') else 0,
            'judgement': parse_judgement(raw.get('judgement', [])),
            'is_score_grown': has_red_arrow(crops['score_grown'],
                                            self.red_arrow_ratio) if 'score_grown' in crops else False,
            'is_accuracy_grown': has_red_arrow(crops['judgement_total_grown'],
                                               self.red_arrow_ratio) if 'judgement_total_grown' in crops else False,
        }
        return record

    def extract_raw(self, image_path: str, rois) -> dict:
        self._ensure_loaded()

        img = Image.open(image_path)
        raw = {}
        CROPS_DIR.mkdir(exist_ok=True)

        for roi in rois:
            crop = img.crop((roi.x1, roi.y1, roi.x2, roi.y2))
            crop_path = str(CROPS_DIR / f'_test_{roi.name}.png')
            crop.save(crop_path)
            result = self._ocr.predict(crop_path)
            texts = result[0]['rec_texts']
            scores = result[0]['rec_scores']
            filtered = [t for t, s in zip(texts, scores) if s >= self.score_thresh]
            raw[roi.name] = filtered

        return raw

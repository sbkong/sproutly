import os

os.environ['FLAGS_use_mkldnn'] = '0'

import re
from PIL import Image
import numpy as np
from paddleocr import PaddleOCR

from sproutly.paths import CROPS_DIR

ROIS = [
    ("buttons", 40, 0, 270, 110),
    ("title", 770, 0, 1400, 50),
    ("break_top", 1080, 165, 1165, 235),
    ("judgement", 90, 230, 435, 640),
    ("max_100", 610, 350, 720, 415),
    ("max_1_90", 1180, 340, 1310, 415),
    ("score", 720, 710, 1150, 800),
    ("score_grown", 830, 800, 1050, 840),
    ("judgement_total", 880, 600, 1040, 640),
    ("judgement_total_grown", 880, 640, 1040, 670),
]


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

    def update_thresholds(self, score_thresh: float, red_arrow_ratio: float):
        self.score_thresh = score_thresh
        self.red_arrow_ratio = red_arrow_ratio

    def _ensure_loaded(self):
        if self._ocr is None:
            self._ocr = PaddleOCR(
                lang='en',
                enable_mkldnn=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

    def extract(self, image_path: str) -> dict:
        self._ensure_loaded()

        img = Image.open(image_path)
        raw = {}
        crops = {}

        # 임시 crop 저장 폴더
        tmp_dir = CROPS_DIR
        tmp_dir.mkdir(exist_ok=True)

        for name, x1, y1, x2, y2 in ROIS:
            crop = img.crop((x1, y1, x2, y2))
            crop_path = str(tmp_dir / f'{name}.png')
            crop.save(crop_path)
            crops[name] = crop

            result = self._ocr.predict(crop_path)
            texts = result[0]['rec_texts']
            scores = result[0]['rec_scores']
            filtered = [t for t, s in zip(texts, scores) if s >= self.score_thresh]
            raw[name] = filtered

        record = {
            'title': raw['title'][0] if raw['title'] else '',
            'buttons': to_int(raw['buttons'][0]) if raw['buttons'] else 0,
            'score': to_int(raw['score'][0]) if raw['score'] else 0,
            'accuracy': raw['judgement_total'][0] if raw['judgement_total'] else '',
            'max_100_count': to_int(raw['max_100'][0]) if raw['max_100'] else 0,
            'max_1_90_count': to_int(raw['max_1_90'][0]) if raw['max_1_90'] else 0,
            'break_count': to_int(raw['break_top'][0]) if raw['break_top'] else 0,
            'judgement': parse_judgement(raw['judgement']),
            'is_score_grown': has_red_arrow(crops['score_grown'], self.red_arrow_ratio),
            'is_accuracy_grown': has_red_arrow(crops['judgement_total_grown'], self.red_arrow_ratio),
        }

        return record

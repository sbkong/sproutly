"""
ROI 정의 로딩/저장
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from sproutly.paths import DATA_DIR
from sproutly.resources_util import resource_path

log = logging.getLogger('sproutly.rois')

USER_ROIS_PATH = DATA_DIR / 'rois.json'


@dataclass
class Roi:
    name: str
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def as_tuple(self) -> tuple:
        return (self.name, self.x1, self.y1, self.x2, self.y2)


@dataclass
class Preset:
    id: str
    name: str
    resolution: tuple[int, int]   # (width, height)
    rois: list[Roi]


def _load_presets_file() -> dict:
    path = resource_path('presets.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_presets() -> list[Preset]:
    data = _load_presets_file()
    presets = []
    for p in data.get('presets', []):
        rois = [Roi(**r) for r in p['rois']]
        presets.append(Preset(
            id=p['id'],
            name=p['name'],
            resolution=tuple(p['resolution']),
            rois=rois,
        ))
    return presets


def get_preset(preset_id: str) -> Optional[Preset]:
    for p in load_presets():
        if p.id == preset_id:
            return p
    return None


def get_default_preset() -> Preset:
    presets = load_presets()
    if not presets:
        raise RuntimeError("No presets defined")
    return presets[0]


def _load_user_rois() -> Optional[dict]:
    if not USER_ROIS_PATH.exists():
        return None
    try:
        with open(USER_ROIS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"사용자 ROI 파일 로드 실패: {e}")
        return None


def load_active_rois() -> list[Roi]:
    user = _load_user_rois()

    if user is None:
        # 첫 사용 → 기본 프리셋
        return get_default_preset().rois

    active = user.get('active_preset', '')
    if active == 'custom':
        rois_data = user.get('custom_rois', [])
        if rois_data:
            return [Roi(**r) for r in rois_data]
        # custom인데 데이터 없으면 fallback
        return get_default_preset().rois

    # 프리셋 id 지정됨
    preset = get_preset(active)
    if preset is None:
        log.warning(f"알 수 없는 프리셋: {active}, 기본값 사용")
        return get_default_preset().rois
    return preset.rois


def get_active_state() -> dict:
    user = _load_user_rois()
    if user is None:
        p = get_default_preset()
        return {'mode': 'preset', 'preset_id': p.id, 'resolution': p.resolution}

    active = user.get('active_preset', '')
    if active == 'custom':
        return {
            'mode': 'custom',
            'preset_id': None,
            'resolution': tuple(user.get('custom_resolution', [1920, 1080])),
        }
    p = get_preset(active) or get_default_preset()
    return {'mode': 'preset', 'preset_id': p.id, 'resolution': p.resolution}


def save_custom_rois(rois: list[Roi], resolution: tuple[int, int]):
    USER_ROIS_PATH.parent.mkdir(exist_ok=True)
    data = {
        'version': 1,
        'active_preset': 'custom',
        'custom_rois': [
            {'name': r.name, 'x1': r.x1, 'y1': r.y1, 'x2': r.x2, 'y2': r.y2}
            for r in rois
        ],
        'custom_resolution': list(resolution),
    }
    with open(USER_ROIS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"사용자 ROI 저장됨: {len(rois)}개")


def set_active_preset(preset_id: str):
    USER_ROIS_PATH.parent.mkdir(exist_ok=True)
    user = _load_user_rois() or {'version': 1}
    user['active_preset'] = preset_id
    with open(USER_ROIS_PATH, 'w', encoding='utf-8') as f:
        json.dump(user, f, indent=2, ensure_ascii=False)


def reset_to_default():
    if USER_ROIS_PATH.exists():
        USER_ROIS_PATH.unlink()
        log.info("ROI 사용자 설정 삭제됨")
import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from typing import Optional

from . import __version__

log = logging.getLogger('sproutly.updater')

GITHUB_OWNER = "sbkong"
GITHUB_REPO = "sproutly"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
TIMEOUT_SEC = 5


@dataclass
class UpdateInfo:
    current: str
    latest: str
    is_update_available: bool
    release_url: str
    release_notes: str
    download_url: Optional[str] = None


def _parse_version(tag: str) -> tuple[int, ...]:
    s = tag.lstrip('v').strip()
    nums = re.findall(r'\d+', s)
    return tuple(int(n) for n in nums[:3]) if nums else (0,)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def check_for_update(timeout: float = TIMEOUT_SEC) -> Optional[UpdateInfo]:
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={
                'Accept': 'application/vnd.github+json',
                'User-Agent': f'Sproutly/{__version__}',
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log.warning(f"업데이트 체크 실패: {e}")
        return None

    tag = data.get('tag_name', '')
    if not tag:
        return None

    download_url = None
    for asset in data.get('assets', []):
        name = asset.get('name', '').lower()
        if name.endswith('.zip') or name.endswith('.exe'):
            download_url = asset.get('browser_download_url')
            break

    info = UpdateInfo(
        current=__version__,
        latest=tag.lstrip('v'),
        is_update_available=_is_newer(tag, __version__),
        release_url=data.get('html_url', RELEASES_URL),
        release_notes=data.get('body', '') or '',
        download_url=download_url,
    )
    log.info(f"업데이트 체크: 현재={info.current}, 최신={info.latest}, 업데이트={info.is_update_available}")
    return info

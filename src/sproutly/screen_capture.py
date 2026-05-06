"""
화면 캡처 - 마우스 커서가 있는 모니터를 PNG로 임시저장
"""
import tempfile

import mss
from PIL import Image


def get_cursor_pos() -> tuple[int, int]:
    """현재 마우스 좌표 (Windows)"""
    import ctypes
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def capture_active_monitor() -> str:
    """
    마우스 커서가 있는 모니터 전체를 캡처해서 임시 PNG 경로 반환
    """
    cx, cy = get_cursor_pos()

    with mss.mss() as sct:
        # monitors[0]은 전체 가상 화면, [1]부터 개별 모니터
        target = None
        for mon in sct.monitors[1:]:
            if (mon['left'] <= cx < mon['left'] + mon['width']
                    and mon['top'] <= cy < mon['top'] + mon['height']):
                target = mon
                break
        if target is None:
            target = sct.monitors[1]  # fallback: 1번 모니터

        shot = sct.grab(target)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix='capture_')
    tmp.close()
    img.save(tmp.name, 'PNG')
    return tmp.name


def capture_primary_monitor() -> str:
    """1번(주) 모니터 캡처 - 멀티모니터에서 항상 게임 화면이 1번이면 이게 단순함"""
    with mss.mss() as sct:
        target = sct.monitors[1]
        shot = sct.grab(target)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix='capture_')
    tmp.close()
    img.save(tmp.name, 'PNG')
    return tmp.name


def list_monitors() -> list[dict]:
    """모니터 정보 리스트 - UI에서 선택지 만들 때 씀"""
    with mss.mss() as sct:
        # monitors[0]은 가상 전체화면, [1]부터 개별
        result = []
        for i, mon in enumerate(sct.monitors[1:], start=1):
            result.append({
                'index': i,
                'left': mon['left'],
                'top': mon['top'],
                'width': mon['width'],
                'height': mon['height'],
                'label': f"모니터 {i} ({mon['width']}x{mon['height']})",
            })
        return result


def capture_monitor_by_index(idx: int) -> str:
    """1-based 인덱스로 모니터 캡처"""
    with mss.mss() as sct:
        mons = sct.monitors
        if idx < 1 or idx >= len(mons):
            raise ValueError(f"모니터 {idx} 없음 (사용가능: 1~{len(mons) - 1})")
        target = mons[idx]
        shot = sct.grab(target)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix='capture_')
    tmp.close()
    img.save(tmp.name, 'PNG')
    return tmp.name


def capture_by_target(target: str) -> str:
    """
    target: 'cursor' | 'primary' | 'monitor:N'
    """
    if target == 'cursor':
        return capture_active_monitor()
    if target == 'primary':
        return capture_primary_monitor()
    if target.startswith('monitor:'):
        idx = int(target.split(':', 1)[1])
        return capture_monitor_by_index(idx)
    # fallback
    return capture_active_monitor()

import tempfile

import mss
from PIL import Image


def get_cursor_pos() -> tuple[int, int]:
    import ctypes
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def capture_active_monitor() -> str:
    cx, cy = get_cursor_pos()

    with mss.mss() as sct:
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
    with mss.mss() as sct:
        target = sct.monitors[1]
        shot = sct.grab(target)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix='capture_')
    tmp.close()
    img.save(tmp.name, 'PNG')
    return tmp.name


def list_monitors() -> list[dict]:
    with mss.mss() as sct:
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
    return capture_active_monitor()

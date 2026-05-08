import os
import sys
from pathlib import Path


def resource_path(rel: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'sproutly', 'resources', rel)
    if getattr(sys, 'frozen', False):
        return os.path.join(
            os.path.dirname(sys.executable), '_internal',
            'sproutly', 'resources', rel,
        )
    return str(Path(__file__).parent / 'resources' / rel)
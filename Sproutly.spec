# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

# === paddle / paddleocr ===
paddle_datas, paddle_binaries, paddle_hidden = collect_all('paddle')
paddleocr_datas, paddleocr_binaries, paddleocr_hidden = collect_all('paddleocr')
paddlex_datas, paddlex_binaries, paddlex_hidden = collect_all('paddlex')

# 우리 패키지
sproutly_datas, sproutly_binaries, sproutly_hidden = collect_all('sproutly')

metadata_pkgs = [
    'paddlepaddle', 'paddleocr', 'paddlex',
    'shapely', 'pyclipper', 'opencv-contrib-python',
    'pypdfium2', 'imagesize', 'python-bidi',
    'pyyaml', 'requests', 'numpy', 'pillow', 'pandas',
    'pydantic', 'tqdm', 'einops', 'safetensors',
    'huggingface-hub', 'modelscope', 'aistudio-sdk',
    'colorlog', 'chardet', 'prettytable', 'ruamel.yaml',
    'ujson', 'filelock', 'click', 'typer', 'rich',
    'bce-python-sdk', 'pycryptodome',
    'PySide6', 'shiboken6',
]

extra_metadata = []
for pkg in metadata_pkgs:
    try:
        extra_metadata += copy_metadata(pkg)
    except Exception as e:
        print(f"[spec] skip metadata for '{pkg}': {e}")

extra_hidden = [
    'paddleocr', 'paddleocr._pipelines.ocr',
    'paddlex', 'paddlex.inference',
    'paddlex.inference.pipelines', 'paddlex.inference.pipelines.ocr',
    'shapely', 'shapely.geometry', 'pyclipper',
    'sproutly', 'sproutly.ui',
]

import os
sproutly_resources = []
src_resources = os.path.join('src', 'sproutly', 'resources')
if os.path.isdir(src_resources):
    for f in os.listdir(src_resources):
        full = os.path.join(src_resources, f)
        if os.path.isfile(full):
            sproutly_resources.append((full, 'sproutly/resources'))

a = Analysis(
    ['run_sproutly.py'],
    pathex=['src'],
    binaries=paddle_binaries + paddleocr_binaries + paddlex_binaries + sproutly_binaries,
    datas=(
        paddle_datas + paddleocr_datas + paddlex_datas
        + sproutly_datas + extra_metadata
        + sproutly_resources
    ),
    hiddenimports=(
        paddle_hidden + paddleocr_hidden + paddlex_hidden
        + sproutly_hidden + extra_hidden
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'tkinter',
        'PyQt5', 'PyQt6', 'PySide2',
        'IPython', 'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Sproutly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/sproutly/resources/icon.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name='Sproutly',
)
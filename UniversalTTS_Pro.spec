# -*- mode: python ; coding: utf-8 -*-
# ════════════════════════════════════════════════════════════════════
#  UniversalTTS_Pro.spec  — PyInstaller build konfiguráció
#  Parancs: pyinstaller UniversalTTS_Pro.spec
#
#  FONTOS: a models/ mappa NEM kerül az _internal-ba!
#  Build után a .bat script átmásolja: dist/UniversalTTS_Pro/models/
# ════════════════════════════════════════════════════════════════════

import shutil, os

block_cipher = None

a = Analysis(
    ['UniversalTTS_Pro.py'],
    pathex=[],
    binaries=[
        ('opusenc.exe',  '.'),
    ],
    datas=[
        # Javítási szótárak → az exe mellé kerülnek (nem _internal!)
        ('javitasok_HU.txt', '.'),
        ('javitasok_EN.txt', '.'),
        ('javitasok_RO.txt', '.'),
        # models/ szándékosan NINCS itt — a .bat másolja át build után
    ],
    hiddenimports=[
        'sherpa_onnx',
        'sounddevice',
        'numpy',
        'supertonic',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UniversalTTS_Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UniversalTTS_Pro',
)

# ── Post-build: models/ másolása az exe mellé (nem _internal-ba) ──
dist_dir = os.path.join('dist', 'UniversalTTS_Pro')
src_models = 'models'
dst_models = os.path.join(dist_dir, 'models')

if os.path.isdir(src_models) and os.path.isdir(dist_dir):
    if os.path.exists(dst_models):
        shutil.rmtree(dst_models)
    shutil.copytree(src_models, dst_models)
    print(f"\n[OK] models/ átmásolva: {dst_models}\n")

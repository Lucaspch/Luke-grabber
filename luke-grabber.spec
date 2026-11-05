# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [
    ('frontend', 'frontend'),
    ('bin', 'bin'),
    ('frontend/app-icon.ico', '.'),
    ('frontend/app-icon.png', '.'),
]
datas += collect_data_files('yt_dlp')

hiddenimports = [
    'bottle',
    'yt_dlp',
    'webview',
    'pythonnet',
    'clr_loader',
    'tkinter',
    'tkinter.filedialog',
]
# Inclui extractors do yt-dlp para garantir suporte a todas as plataformas
hiddenimports += collect_submodules('yt_dlp.extractor')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Luke-Grabber',
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
    icon='frontend/app-icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Luke-Grabber',
)

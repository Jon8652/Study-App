# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build configuration for Study Tracker Desktop (Part M).
#
# One-folder, windowed (no console) build — per the plan's v1 guidance.
# Assets are bundled into an "assets" folder next to the executable;
# app/utils/paths.get_resource_dir() resolves them in frozen mode.
#
# Build on Windows:  pyinstaller --noconfirm study_tracker.spec
#              or:   .\run_build.ps1

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['customtkinter', 'PIL.ImageTk', 'platformdirs'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'setuptools'],
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
    name='StudyTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # GUI app: no console window (Part M rule)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='StudyTracker',
)

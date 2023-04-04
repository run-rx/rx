# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Check rsync.
rsync_path = os.getenv('RSYNC_PATH')
if not rsync_path:
  raise RuntimeError('RSYNC_PATH must be specified')
if not os.path.exists(rsync_path):
  raise RuntimeError(f'{rsync_path} does not exist')

a = Analysis(
    ['rx/client/commands/exec.py'],
    pathex=['.'],
    binaries=[(rsync_path, 'bin')],
    datas=[('install', 'install')],
    hiddenimports=[],
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
    name='rx',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='rx',
)

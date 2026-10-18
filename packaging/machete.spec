# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

block_cipher = None

a = Analysis(
    ['src/machete/cli.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/machete/assets/*', 'machete/assets'),
    ],
    hiddenimports=[
        'pyaaf2',
        'pydantic',
        'pydantic_core',
        'tkinter',
        'fractions',
        'uuid',
        'xml.etree.ElementTree',
        'gzip',
        'machete.ir',
        'machete.parsers',
        'machete.exporters',
        'machete.verify',
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

exe_name = 'KrovakovaSekera.exe' if sys.platform.startswith('win') else 'Křovákova Sekera'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/machete/assets/dwarf_seal.icns' if sys.platform == 'darwin' else 'src/machete/assets/dwarf_seal.png',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Křovákova Sekera.app',
        icon='src/machete/assets/dwarf_seal.icns',
        bundle_identifier='cz.krovak.machete',
        info_plist={
            'NSHighResolutionCapable': 'True',
        },
    )

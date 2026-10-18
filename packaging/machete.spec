# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

# SPECPATH is provided by PyInstaller and points to packaging/
spec_dir = Path(SPECPATH).resolve() if "SPECPATH" in globals() else Path(__file__).resolve().parent
root_dir = spec_dir.parent
src_dir = root_dir / "src"
cli_path = str(src_dir / "machete" / "cli.py")
assets_dir = src_dir / "machete" / "assets"
icns_icon = str(assets_dir / "dwarf_seal.icns")
ico_icon = str(assets_dir / "dwarf_seal.ico")

block_cipher = None

a = Analysis(
    [cli_path],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[
        (str(assets_dir), "machete/assets"),
    ],
    hiddenimports=[
        "aaf2",
        "pyaaf2",
        "pydantic",
        "pydantic_core",
        "tkinter",
        "fractions",
        "uuid",
        "xml.etree.ElementTree",
        "gzip",
        "machete.ir",
        "machete.parsers",
        "machete.exporters",
        "machete.verify",
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

exe_name = "KrovakovaSekera.exe" if sys.platform.startswith("win") else "Křovákova Sekera"
exe_icon = icns_icon if sys.platform == "darwin" else (ico_icon if Path(ico_icon).exists() else None)

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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Křovákova Sekera.app",
        icon=icns_icon,
        bundle_identifier="cz.krovak.machete",
        info_plist={
            "NSHighResolutionCapable": "True",
        },
    )

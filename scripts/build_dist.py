#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def create_dmg(app_path: Path, output_dmg: Path, volname: str = "Křovákova Sekera") -> Path:
    """Create a macOS DMG installer containing the app bundle and an /Applications symlink."""
    app_path = Path(app_path).resolve()
    output_dmg = Path(output_dmg).resolve()

    if not app_path.exists():
        raise FileNotFoundError(f"App bundle not found at: {app_path}")

    output_dmg.parent.mkdir(parents=True, exist_ok=True)
    if output_dmg.exists():
        output_dmg.unlink()

    with tempfile.TemporaryDirectory() as tmp_dir:
        staging_dir = Path(tmp_dir) / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)

        target_app = staging_dir / app_path.name
        if app_path.is_dir():
            shutil.copytree(app_path, target_app, symlinks=True)
        else:
            shutil.copy2(app_path, target_app)

        apps_symlink = staging_dir / "Applications"
        if not apps_symlink.exists():
            try:
                os.symlink("/Applications", apps_symlink)
            except OSError:
                pass

        if sys.platform == "darwin":
            subprocess.run(["xattr", "-cr", str(staging_dir)], check=False)

        cmd = [
            "hdiutil",
            "create",
            "-volname",
            volname,
            "-srcfolder",
            str(staging_dir),
            "-ov",
            "-format",
            "UDZO",
            str(output_dmg),
        ]
        subprocess.run(cmd, check=True)

    return output_dmg


def build_distribution(dmg: bool = False, clean: bool = False, dry_run: bool = False) -> int:
    """Run PyInstaller build and optional DMG packaging."""
    root_dir = Path(__file__).resolve().parent.parent
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"
    spec_path = root_dir / "packaging" / "machete.spec"

    if clean:
        print("Cleaning build and dist directories...")
        if not dry_run:
            if build_dir.exists():
                shutil.rmtree(build_dir)
            if dist_dir.exists():
                shutil.rmtree(dist_dir)
        else:
            print(f"[dry-run] Would remove {build_dir} and {dist_dir}")

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(spec_path),
    ]

    print(f"Running PyInstaller: {' '.join(pyinstaller_cmd)}")
    if not dry_run:
        subprocess.run(pyinstaller_cmd, cwd=str(root_dir), check=True)
    else:
        print(f"[dry-run] Would execute: {' '.join(pyinstaller_cmd)} in {root_dir}")

    if dmg:
        if sys.platform != "darwin" and not dry_run:
            print("Warning: DMG creation is only supported on macOS.")
            return 0

        app_name = "Křovákova Sekera.app"
        app_path = dist_dir / app_name
        dmg_path = dist_dir / "KrovakovaSekera.dmg"

        print(f"Creating DMG package: {dmg_path}")
        if not dry_run:
            create_dmg(app_path, dmg_path)
            print(f"DMG successfully created at: {dmg_path}")
        else:
            print(f"[dry-run] Would create DMG from {app_path} to {dmg_path} using hdiutil create")

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for build_dist."""
    parser = argparse.ArgumentParser(
        prog="build_dist",
        description="Build distribution packages for Křovákova Sekera / Mačeta",
    )
    parser.add_argument(
        "--dmg",
        action="store_true",
        help="Build macOS DMG image with Applications shortcut",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build and dist directories prior to building",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display build commands without executing them",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    args = parse_args(argv)
    return build_distribution(dmg=args.dmg, clean=args.clean, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

from pathlib import Path
import sys


def get_asset_path(filename: str) -> Path:
    """Resolve path to an asset in both development and PyInstaller frozen environments."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
        primary = base / "machete" / "assets" / filename
        if primary.exists():
            return primary
        fallback = base / filename
        if fallback.exists():
            return fallback
        path = primary
    else:
        path = Path(__file__).resolve().parent / filename

    if path.exists():
        return path

    raise FileNotFoundError(f"Asset '{filename}' not found at {path}")

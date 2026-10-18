from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from machete.assets.resolver import get_asset_path
from scripts.build_dist import create_dmg, parse_args


def test_get_asset_path_live_mode() -> None:
    """Test get_asset_path successfully locates existing assets in development/live mode."""
    seal_png = get_asset_path("dwarf_seal.png")
    assert seal_png.exists()
    assert seal_png.name == "dwarf_seal.png"

    scene_png = get_asset_path("dwarf_scene.png")
    assert scene_png.exists()
    assert scene_png.name == "dwarf_scene.png"

    seal_icns = get_asset_path("dwarf_seal.icns")
    assert seal_icns.exists()
    assert seal_icns.name == "dwarf_seal.icns"


def test_get_asset_path_frozen_primary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_asset_path resolves sys._MEIPASS/machete/assets/filename in frozen mode."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    primary_dir = tmp_path / "machete" / "assets"
    primary_dir.mkdir(parents=True, exist_ok=True)
    fake_asset = primary_dir / "dwarf_seal.png"
    fake_asset.write_bytes(b"PNG_DATA")

    resolved = get_asset_path("dwarf_seal.png")
    assert resolved == fake_asset
    assert resolved.exists()


def test_get_asset_path_frozen_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_asset_path falls back to sys._MEIPASS/filename in frozen mode."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    fallback_asset = tmp_path / "dwarf_seal.png"
    fallback_asset.write_bytes(b"PNG_FALLBACK")

    resolved = get_asset_path("dwarf_seal.png")
    assert resolved == fallback_asset
    assert resolved.exists()


def test_get_asset_path_nonexistent() -> None:
    """Test get_asset_path raises FileNotFoundError for missing assets."""
    with pytest.raises(FileNotFoundError, match="nonexistent_asset.png"):
        get_asset_path("nonexistent_asset.png")


def test_get_asset_path_frozen_nonexistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_asset_path raises FileNotFoundError in frozen mode when asset does not exist."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    with pytest.raises(FileNotFoundError, match="missing.png"):
        get_asset_path("missing.png")


def test_packaging_spec_valid_and_has_data_tuples() -> None:
    """Test packaging/machete.spec is valid Python syntax and contains required configurations."""
    spec_path = Path(__file__).resolve().parent.parent / "packaging" / "machete.spec"
    assert spec_path.exists(), f"Spec file not found at {spec_path}"

    content = spec_path.read_text(encoding="utf-8")

    # Verify Python syntax validity
    parsed_ast = ast.parse(content, filename=str(spec_path))
    assert isinstance(parsed_ast, ast.Module)

    # Verify asset data tuple
    assert "('src/machete/assets/*', 'machete/assets')" in content or \
           '("src/machete/assets/*", "machete/assets")' in content

    # Verify hidden imports
    expected_hidden = [
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
    ]
    for imp in expected_hidden:
        assert f"'{imp}'" in content or f'"{imp}"' in content, f"Missing hidden import: {imp}"

    # Verify macOS Bundle configuration
    assert "Křovákova Sekera.app" in content
    assert "cz.krovak.machete" in content
    assert "dwarf_seal.icns" in content
    assert "NSHighResolutionCapable" in content

    # Verify Windows executable configuration
    assert "KrovakovaSekera.exe" in content


def test_build_dist_cli_help() -> None:
    """Test scripts/build_dist.py --help via CLI subprocess."""
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "build_dist.py"
    proc = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0
    assert "--dmg" in proc.stdout
    assert "--clean" in proc.stdout
    assert "--dry-run" in proc.stdout


def test_build_dist_argparse() -> None:
    """Test argument parsing in build_dist."""
    args = parse_args(["--dmg", "--clean", "--dry-run"])
    assert args.dmg is True
    assert args.clean is True
    assert args.dry_run is True


def test_create_dmg_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test create_dmg constructs staging area and invokes hdiutil create."""
    fake_app = tmp_path / "Křovákova Sekera.app"
    fake_app.mkdir()
    (fake_app / "dummy_bin").write_text("binary", encoding="utf-8")

    out_dmg = tmp_path / "out" / "test.dmg"

    mock_run = MagicMock()
    monkeypatch.setattr(subprocess, "run", mock_run)

    result = create_dmg(fake_app, out_dmg)
    assert result == out_dmg
    assert mock_run.called

    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "hdiutil"
    assert call_args[1] == "create"
    assert "-volname" in call_args
    assert "-srcfolder" in call_args
    assert str(out_dmg) == call_args[-1]


def test_github_actions_workflow() -> None:
    """Test that release.yml workflow exists, triggers on v* tags, and defines required jobs."""
    workflow_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"
    assert workflow_path.exists()
    content = workflow_path.read_text(encoding="utf-8")

    assert "tags:" in content
    assert "v*" in content
    assert "build-macos" in content
    assert "build-windows" in content
    assert "create-release" in content
    assert "softprops/action-gh-release" in content
    assert ".dmg" in content
    assert ".exe" in content

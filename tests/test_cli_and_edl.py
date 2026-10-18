from __future__ import annotations

from pathlib import Path
import tkinter as tk

import pytest

from machete.cli import main, run_conversion_pipeline
from machete.exporters.edl_cmx3600 import export_sequence_to_edl
from machete.gui import DwarfProgressMonitor, KrovakSekeraGUI, launch_gui
from machete.parsers.prproj_extract import parse_prproj
from tests.fixture_factory import generate_all_fixtures


def test_export_sequence_to_edl(tmp_path: Path) -> None:
    """Test CMX 3600 EDL exporter on simple_cut.prproj:

    - Assert file is written, non-empty.
    - Contains TITLE: Main_Edit_25fps.
    - Contains 001 event line with valid SMPTE timecodes.
    - Contains FCM: NON-DROP FRAME and marker locators.
    """
    fixtures = generate_all_fixtures(tmp_path)
    prproj_path = fixtures["simple_cut.prproj"]

    project_ir = parse_prproj(prproj_path)
    edl_out = tmp_path / "simple_cut.edl"
    result_path = export_sequence_to_edl(
        project_ir.sequences[0], project_ir.media_sources, edl_out
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 0

    content = result_path.read_text(encoding="utf-8")
    assert "TITLE: Main_Edit_25fps" in content
    assert "FCM: NON-DROP FRAME" in content
    assert "001" in content
    assert "00:00:00:00" in content
    assert "00:00:02:00" in content
    assert "Shot_01.mov" in content
    assert "002" in content
    assert "* LOC:" in content
    assert "VFX_Check" in content


def test_cli_convert_prproj(tmp_path: Path) -> None:
    """Test CLI main() convert subcommand with --also-edl and --report:

    - Returns exit code 0.
    - Assert .aaf, .edl, and .md report files are created on disk and non-empty.
    - Assert .edl contains TITLE: Main_Edit_25fps and 001 event line.
    - Assert report markdown contains VALIDNÍ.
    """
    fixtures = generate_all_fixtures(tmp_path)
    prproj_path = fixtures["simple_cut.prproj"]
    aaf_path = tmp_path / "simple_cut.aaf"
    edl_path = aaf_path.with_suffix(".edl")
    report_path = tmp_path / "report.md"

    ret = main(
        [
            "convert",
            str(prproj_path),
            "-o",
            str(aaf_path),
            "--also-edl",
            "--report",
            str(report_path),
        ]
    )

    assert ret == 0
    assert aaf_path.exists() and aaf_path.stat().st_size > 0
    assert edl_path.exists() and edl_path.stat().st_size > 0
    assert report_path.exists() and report_path.stat().st_size > 0

    edl_content = edl_path.read_text(encoding="utf-8")
    assert "TITLE: Main_Edit_25fps" in edl_content
    assert "001" in edl_content
    assert "00:00:00:00" in edl_content

    report_content = report_path.read_text(encoding="utf-8")
    assert "VALIDNÍ" in report_content
    assert "Main_Edit_25fps" in report_content


def test_cli_convert_sesx(tmp_path: Path) -> None:
    """Test CLI main() on .sesx file:

    - Returns exit code 0.
    - Creates valid non-empty .aaf file.
    """
    fixtures = generate_all_fixtures(tmp_path)
    sesx_path = fixtures["sample_audition.sesx"]
    aaf_path = tmp_path / "audition.aaf"

    ret = main(["convert", str(sesx_path), "-o", str(aaf_path), "--embed-audio"])

    assert ret == 0
    assert aaf_path.exists()
    assert aaf_path.stat().st_size > 0


def test_run_conversion_pipeline_progress_callback(tmp_path: Path) -> None:
    """Test run_conversion_pipeline invokes progress_callback:

    - Strictly non-decreasing percentage order (15 -> 40 -> 70 -> 85 -> 100).
    - With Czech stonemason stage messages.
    """
    fixtures = generate_all_fixtures(tmp_path)
    prproj_path = fixtures["simple_cut.prproj"]
    aaf_path = tmp_path / "pipeline_test.aaf"

    progress_events: list[tuple[int, str]] = []

    def on_progress(pct: int, msg: str) -> None:
        progress_events.append((pct, msg))

    report = run_conversion_pipeline(
        input_path=prproj_path,
        output_path=aaf_path,
        progress_callback=on_progress,
    )

    assert report.is_valid is True

    percentages = [event[0] for event in progress_events]
    assert percentages == [15, 40, 70, 85, 100]

    # Verify non-decreasing order
    for i in range(len(percentages) - 1):
        assert percentages[i] <= percentages[i + 1]

    # Verify Czech stonemason stage messages
    expected_messages = [
        "Průzkum slojí a indexace Adobe XML...",
        "Osekávání vnořených sekvencí na čisté kvádry...",
        "Kladení základů Avid AAF stromu...",
        "Třídění a zalévání audio esencí (PCM WAV)...",
        "Kamenická inspekce integrity zdiva (Roundtrip Verifier)...",
    ]
    actual_messages = [event[1] for event in progress_events]
    assert actual_messages == expected_messages


def test_gui_instantiation() -> None:
    """Test that tkinter GUI components instantiate gracefully."""
    try:
        root = tk.Tk()
        root.withdraw()
    except (tk.TclError, Exception):
        pytest.skip("No graphical display available for Tkinter GUI test")

    try:
        app = KrovakSekeraGUI(root)
        assert app.root.title() == "Křovákova Sekera — Adobe -> Avid Překladač"
        assert isinstance(app.monitor, DwarfProgressMonitor)

        # Test state transitions on monitor
        app.monitor.set_state("WORKING", 50, "Opracovávám kvádr...")
        assert app.monitor.percentage == 50
        assert app.monitor.state == "WORKING"

        app.monitor.set_state("SUCCESS", 100)
        assert app.monitor.percentage == 100
        assert app.monitor.state == "SUCCESS"

        app.monitor.set_state("ERROR", 0, "Chyba")
        assert app.monitor.state == "ERROR"
    finally:
        root.destroy()

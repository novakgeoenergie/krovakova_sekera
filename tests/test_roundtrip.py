from __future__ import annotations

from pathlib import Path

from machete.exporters import export_project_to_aaf
from machete.parsers import parse_prproj, parse_sesx
from machete.verify import verify_aaf_against_ir
from tests.fixture_factory import (
    generate_all_fixtures,
    generate_nested_seq_prproj,
    generate_simple_cut_prproj,
)


def test_roundtrip_simple_cut(tmp_path: Path) -> None:
    """End-to-End Test 1:

    simple_cut.prproj -> parse_prproj -> export_project_to_aaf -> verify_aaf_against_ir.
    - Assert report.is_valid is True.
    - Assert "Warp Stabilizer" appears in report.warnings or in report.to_markdown().
    """
    fixtures = generate_all_fixtures(tmp_path)
    prproj_path = fixtures["simple_cut.prproj"]

    project_ir = parse_prproj(prproj_path)
    aaf_path = export_project_to_aaf(project_ir, tmp_path / "simple_cut.aaf")

    report = verify_aaf_against_ir(aaf_path, project_ir)

    assert report.is_valid is True
    assert "Warp Stabilizer" in report.warnings or "Warp Stabilizer" in report.to_markdown()

    md = report.to_markdown()
    assert "VALIDNÍ" in md
    assert "Main_Edit_25fps" in md
    assert report.total_tracks == 2
    assert report.total_clips == 4
    assert report.total_fillers == 2
    assert len(report.errors) == 0


def test_roundtrip_nested_seq(tmp_path: Path) -> None:
    """End-to-End Test 2:

    nested_seq.prproj -> parse_prproj(path, flatten_nested=True) -> export_project_to_aaf -> verify_aaf_against_ir.
    - Assert report.is_valid is True.
    """
    nested_path = generate_nested_seq_prproj(tmp_path / "nested_seq.prproj")

    project_ir = parse_prproj(nested_path, flatten_nested=True)
    aaf_path = export_project_to_aaf(project_ir, tmp_path / "nested_seq.aaf")

    report = verify_aaf_against_ir(aaf_path, project_ir)

    assert report.is_valid is True

    md = report.to_markdown()
    assert "VALIDNÍ" in md
    assert report.total_tracks >= 2
    assert report.total_clips >= 4
    assert len(report.errors) == 0


def test_roundtrip_sample_audition(tmp_path: Path) -> None:
    """End-to-End Test 3:

    sample_audition.sesx -> parse_sesx -> export_project_to_aaf(embed_audio=True) -> verify_aaf_against_ir.
    - Assert report.is_valid is True.
    """
    fixtures = generate_all_fixtures(tmp_path)
    sesx_path = fixtures["sample_audition.sesx"]

    project_ir = parse_sesx(sesx_path)
    aaf_path = export_project_to_aaf(project_ir, tmp_path / "audition.aaf", embed_audio=True)

    report = verify_aaf_against_ir(aaf_path, project_ir)

    assert report.is_valid is True

    md = report.to_markdown()
    assert "VALIDNÍ" in md
    assert report.total_tracks >= 1
    assert report.total_clips >= 2
    assert len(report.errors) == 0


def test_verify_aaf_detects_mismatch(tmp_path: Path) -> None:
    """Verify that verify_aaf_against_ir catches mismatches and reports NEVALIDNÍ."""
    fixtures = generate_all_fixtures(tmp_path)
    prproj_path = fixtures["simple_cut.prproj"]

    project_ir = parse_prproj(prproj_path)
    aaf_path = export_project_to_aaf(project_ir, tmp_path / "simple_cut.aaf")

    # Tamper with expected_ir by altering sequence duration
    mutated_seq = project_ir.sequences[0].model_copy(
        update={"duration_frames": project_ir.sequences[0].duration_frames + 10}
    )
    mutated_ir = project_ir.model_copy(update={"sequences": [mutated_seq]})

    report = verify_aaf_against_ir(aaf_path, mutated_ir)

    assert report.is_valid is False
    assert len(report.errors) > 0
    md = report.to_markdown()
    assert "NEVALIDNÍ" in md
    assert "Chyby" in md

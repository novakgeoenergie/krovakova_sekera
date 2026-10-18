from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import pytest

from machete.ir.schema import ProjectIR
from machete.parsers import parse_prproj
from tests.fixture_factory import generate_nested_seq_prproj, generate_simple_cut_prproj


def test_simple_cut_extract(tmp_path: Path) -> None:
    prproj_path = generate_simple_cut_prproj(tmp_path / "simple_cut.prproj")
    project = parse_prproj(prproj_path)

    assert project.source_format == "prproj"
    assert len(project.sequences) >= 1

    seq = next(s for s in project.sequences if s.name == "Main_Edit_25fps")
    assert seq.edit_rate == Fraction(25, 1)

    # Track V1 verification
    v1 = next(t for t in seq.tracks if t.name == "V1")
    assert len(v1.clips) == 2
    assert v1.clips[0].timeline_in_frames == 0
    assert v1.clips[0].timeline_out_frames == 50
    assert v1.clips[1].timeline_in_frames == 75
    assert v1.clips[1].timeline_out_frames == 125
    # 25 frame gap between 50 and 75
    assert v1.clips[1].timeline_in_frames - v1.clips[0].timeline_out_frames == 25

    # Track A1 verification (J-cut and volume keyframes)
    a1 = next(t for t in seq.tracks if t.name == "A1")
    assert len(a1.clips) == 2
    assert a1.clips[0].timeline_in_frames == 0
    assert a1.clips[0].timeline_out_frames == 50
    assert a1.clips[1].timeline_in_frames in (62, 63)
    assert a1.clips[1].timeline_out_frames == 125

    # Volume keyframes
    vk = a1.clips[1].volume_keyframes
    assert len(vk) == 2
    assert vk[0].offset_frames == 0
    assert vk[0].value == Fraction(1, 1)
    assert vk[1].offset_frames == 25
    assert vk[1].value == Fraction(1, 2)

    # Warp Stabilizer effect notice and red marker
    shot_01 = v1.clips[0]
    unsupported = [e for e in shot_01.unsupported_effects if e.effect_name == "Warp Stabilizer"]
    assert len(unsupported) == 1

    warp_markers = [m for m in shot_01.markers if "Warp Stabilizer" in m.name and m.color == "red"]
    assert len(warp_markers) >= 1
    assert warp_markers[0].frame_offset == shot_01.timeline_in_frames

    # Sequence marker VFX_Check and Adobe FX marker
    vfx_marker = next(m for m in seq.markers if m.name == "VFX_Check")
    assert vfx_marker.frame_offset == 25
    assert vfx_marker.color == "red"


def test_nested_sequence_flattening(tmp_path: Path) -> None:
    prproj_path = generate_nested_seq_prproj(tmp_path / "nested_seq.prproj")

    # With flatten_nested=True
    project_flattened = parse_prproj(prproj_path, flatten_nested=True)
    master = next(s for s in project_flattened.sequences if s.name == "Master_Seq")
    v1 = next(t for t in master.tracks if t.name == "V1")

    assert len(v1.clips) == 2
    assert v1.clips[0].name == "Shot_A.mov"
    assert v1.clips[0].timeline_in_frames == 25
    assert v1.clips[0].timeline_out_frames == 50

    assert v1.clips[1].name == "Shot_B.mov"
    assert v1.clips[1].timeline_in_frames == 50
    assert v1.clips[1].timeline_out_frames == 75

    # With flatten_nested=False
    project_unflattened = parse_prproj(prproj_path, flatten_nested=False)
    master_unflat = next(s for s in project_unflattened.sequences if s.name == "Master_Seq")
    v1_unflat = next(t for t in master_unflat.tracks if t.name == "V1")

    assert len(v1_unflat.clips) == 1
    assert v1_unflat.clips[0].name == "Child_Seq"
    assert v1_unflat.clips[0].timeline_in_frames == 25
    assert v1_unflat.clips[0].timeline_out_frames == 75


def test_json_roundtrip(tmp_path: Path) -> None:
    simple_cut_path = generate_simple_cut_prproj(tmp_path / "simple_cut.prproj")
    project1 = parse_prproj(simple_cut_path)
    json_str1 = project1.model_dump_json()
    restored1 = ProjectIR.model_validate_json(json_str1)
    assert restored1 == project1

    nested_seq_path = generate_nested_seq_prproj(tmp_path / "nested_seq.prproj")
    project2 = parse_prproj(nested_seq_path, flatten_nested=True)
    json_str2 = project2.model_dump_json()
    restored2 = ProjectIR.model_validate_json(json_str2)
    assert restored2 == project2

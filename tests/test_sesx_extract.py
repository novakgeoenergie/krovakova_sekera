from fractions import Fraction
from pathlib import Path
import pytest

from machete.ir.schema import ProjectIR
from machete.parsers import parse_sesx
from tests.fixture_factory import generate_all_fixtures


def test_parse_sesx_sample_audition(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    sesx_path = fixtures["sample_audition.sesx"]

    target_rate = Fraction(25, 1)
    project = parse_sesx(sesx_path, target_edit_rate=target_rate)

    assert project.source_format == "sesx"
    assert project.project_name == "Audition_Mix"
    assert len(project.sequences) == 1

    seq = project.sequences[0]
    assert seq.edit_rate == target_rate
    assert seq.sample_rate == 48000
    assert len(seq.tracks) == 1

    track = seq.tracks[0]
    assert track.kind == "sound"
    assert track.track_index == 0
    assert track.name == "Dialogue_1"
    assert len(track.clips) == 2

    # Clip 1 (0..96000 samples)
    clip1 = track.clips[0]
    assert clip1.timeline_in_frames == 0
    assert clip1.timeline_out_frames == 50
    assert clip1.source_in_frames == 0

    # Clip 2 (144000..240000 samples, sourceInPoint="24000")
    clip2 = track.clips[1]
    assert clip2.timeline_in_frames == 75
    assert clip2.timeline_out_frames == 125
    assert clip2.source_in_frames in (12, 13)

    # Volume keyframes
    assert len(clip2.volume_keyframes) == 2
    assert clip2.volume_keyframes[0].offset_frames == 0
    assert clip2.volume_keyframes[0].value == Fraction(1, 1)
    assert clip2.volume_keyframes[1].offset_frames == 25
    assert clip2.volume_keyframes[1].value == Fraction(1, 2)


def test_parse_sesx_different_edit_rate(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    sesx_path = fixtures["sample_audition.sesx"]

    target_rate = Fraction(24, 1)
    project = parse_sesx(sesx_path, target_edit_rate=target_rate)
    track = project.sequences[0].tracks[0]
    clip2 = track.clips[1]

    # At 24fps, 24000 samples at 48000 Hz = 0.5 sec * 24 fps = 12 frames
    assert clip2.source_in_frames == 12


def test_project_ir_json_round_trip(tmp_path: Path) -> None:
    fixtures = generate_all_fixtures(tmp_path)
    sesx_path = fixtures["sample_audition.sesx"]

    project = parse_sesx(sesx_path, target_edit_rate=Fraction(25, 1))
    json_str = project.model_dump_json()

    restored = ProjectIR.model_validate_json(json_str)
    assert restored.project_name == project.project_name
    assert restored.source_format == "sesx"
    assert len(restored.sequences) == len(project.sequences)
    assert restored.sequences[0].duration_frames == project.sequences[0].duration_frames
    assert len(restored.sequences[0].tracks[0].clips) == 2
    assert restored.sequences[0].tracks[0].clips[1].volume_keyframes[1].value == Fraction(1, 2)


def test_parse_sesx_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_sesx(tmp_path / "non_existent.sesx")
